"""
Gemini AI client for generating SEO metadata using google-genai SDK.
"""

import json
import base64
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from google import genai
from google.genai import types


@dataclass
class GeminiConfig:
    """Configuration for Gemini client."""
    api_key: str
    model: str = "gemini-2.5-flash"  # Updated to latest stable model
    temperature: float = 0.7
    max_output_tokens: int = 2048  # Increased for richer content


class GeminiClient:
    """
    Client for generating SEO metadata using Gemini API.
    """
    
    def __init__(self, config: GeminiConfig):
        """
        Initialize the Gemini client.
        
        Args:
            config: GeminiConfig with API key and model settings
        """
        self.config = config
        self.client = genai.Client(api_key=config.api_key)
        self.categories_data: Dict[str, Any] = {}
        self._load_categories_data()
    
    def _load_categories_data(self):
        """Load categories.json data to access imperial values."""
        try:
            categories_path = Path(__file__).parent.parent / "data" / "categories.json"
            if categories_path.exists():
                with open(categories_path, 'r', encoding='utf-8') as f:
                    self.categories_data = json.load(f)
        except Exception:
            # If loading fails, continue without categories data
            self.categories_data = {}
    
    def _get_imperial_value(self, thickness: str) -> str:
        """Get imperial equivalent for a thickness value from categories.json."""
        if not thickness or not self.categories_data:
            return ""
        
        # Search in thickness_lumber options
        thickness_lumber = self.categories_data.get("lists", {}).get("thickness_lumber", {})
        for option in thickness_lumber.get("options", []):
            # Check by localized name (ua, en, ru) or by slug
            if (option.get("ua") == thickness or 
                option.get("en") == thickness or 
                option.get("ru") == thickness or
                option.get("slug") == thickness):
                return option.get("imperial", "")
        
        return ""
    
    def _get_translation(self, key: str, lang: str) -> str:
        """
        Get translated name for a key from categories.json data.
        
        Args:
            key: The Ukrainian name to translate
            lang: Target language ('ua', 'en', or 'ru')
            
        Returns:
            Translated string, or original key if not found
        """
        if not key or not self.categories_data:
            return key
        
        # Try to find in categories
        for cat_key, cat_data in self.categories_data.get("categories", {}).items():
            if cat_data.get("name_ua") == key:
                if lang == "en":
                    return cat_data.get("name_en", key)
                elif lang == "ru":
                    return cat_data.get("name_ru", key)
                return key  # UA
            
            # Check types within category
            for type_key, type_data in cat_data.get("types", {}).items():
                if type_data.get("name_ua") == key:
                    if lang == "en":
                        return type_data.get("name_en", key)
                    elif lang == "ru":
                        return type_data.get("name_ru", key)
                    return key  # UA
        
        # Try to find in lists (species, grades, etc.)
        for list_name, list_data in self.categories_data.get("lists", {}).items():
            for option in list_data.get("options", []):
                if option.get("ua") == key:
                    if lang == "en":
                        return option.get("en", key)
                    elif lang == "ru":
                        return option.get("ru", key)
                    return key  # UA
        
        # Return original if not found
        return key
    
    def _build_translation_map(self, lang: str) -> Dict[str, str]:
        """
        Build a dictionary mapping Ukrainian terms to their translations.
        
        Args:
            lang: Target language ('en' or 'ru')
            
        Returns:
            Dictionary mapping Ukrainian terms to translated terms
        """
        translation_map = {}
        
        if not self.categories_data:
            return translation_map
        
        # Add categories
        for cat_key, cat_data in self.categories_data.get("categories", {}).items():
            ua_name = cat_data.get("name_ua", "")
            if ua_name:
                if lang == "en":
                    translation_map[ua_name] = cat_data.get("name_en", ua_name)
                elif lang == "ru":
                    translation_map[ua_name] = cat_data.get("name_ru", ua_name)
            
            # Add types within category
            for type_key, type_data in cat_data.get("types", {}).items():
                ua_name = type_data.get("name_ua", "")
                if ua_name:
                    if lang == "en":
                        translation_map[ua_name] = type_data.get("name_en", ua_name)
                    elif lang == "ru":
                        translation_map[ua_name] = type_data.get("name_ru", ua_name)
        
        # Add all list options
        for list_name, list_data in self.categories_data.get("lists", {}).items():
            for option in list_data.get("options", []):
                ua_name = option.get("ua", "")
                if ua_name:
                    if lang == "en":
                        translation_map[ua_name] = option.get("en", ua_name)
                    elif lang == "ru":
                        translation_map[ua_name] = option.get("ru", ua_name)
        
        return translation_map
    
    def _post_process_translations(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process AI result to ensure all Ukrainian terms in EN/RU sections
        are properly translated using categories.json translations.
        
        Args:
            result: The AI-generated result dictionary
            
        Returns:
            Result with Ukrainian terms replaced by proper translations
        """
        if not self.categories_data:
            return result
        
        # Build translation maps for EN and RU
        en_translations = self._build_translation_map("en")
        ru_translations = self._build_translation_map("ru")
        
        def translate_text(text: str, translation_map: Dict[str, str]) -> str:
            """Replace Ukrainian terms in text with translations."""
            if not text or not isinstance(text, str):
                return text
            
            result_text = text
            # Sort by length (longest first) to avoid partial replacements
            sorted_terms = sorted(translation_map.keys(), key=len, reverse=True)
            for ua_term in sorted_terms:
                translated = translation_map[ua_term]
                if ua_term != translated and ua_term in result_text:
                    result_text = result_text.replace(ua_term, translated)
            
            return result_text
        
        # Process EN section
        if "en" in result and isinstance(result["en"], dict):
            en_data = result["en"]
            for field in ["alt_text", "title", "description", "tags"]:
                if field in en_data and isinstance(en_data[field], str):
                    en_data[field] = translate_text(en_data[field], en_translations)
        
        # Process RU section
        if "ru" in result and isinstance(result["ru"], dict):
            ru_data = result["ru"]
            for field in ["alt_text", "title", "description", "tags"]:
                if field in ru_data and isinstance(ru_data[field], str):
                    ru_data[field] = translate_text(ru_data[field], ru_translations)
        
        return result
    
    def _post_process_video_translations(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process video AI result to ensure all Ukrainian terms in EN/RU sections
        are properly translated using categories.json translations.
        
        Args:
            result: The AI-generated video result dictionary
            
        Returns:
            Result with Ukrainian terms replaced by proper translations
        """
        if not self.categories_data:
            return result
        
        # Build translation maps for EN and RU
        en_translations = self._build_translation_map("en")
        ru_translations = self._build_translation_map("ru")
        
        def translate_text(text: str, translation_map: Dict[str, str]) -> str:
            """Replace Ukrainian terms in text with translations."""
            if not text or not isinstance(text, str):
                return text
            
            result_text = text
            # Sort by length (longest first) to avoid partial replacements
            sorted_terms = sorted(translation_map.keys(), key=len, reverse=True)
            for ua_term in sorted_terms:
                translated = translation_map[ua_term]
                if ua_term != translated and ua_term in result_text:
                    result_text = result_text.replace(ua_term, translated)
            
            return result_text
        
        # Process EN section
        if "en" in result and isinstance(result["en"], dict):
            en_data = result["en"]
            for field in ["video_title", "video_description", "thumbnail_alt_text", "video_tags"]:
                if field in en_data:
                    if isinstance(en_data[field], str):
                        en_data[field] = translate_text(en_data[field], en_translations)
                    elif isinstance(en_data[field], list):
                        # Handle list of tags
                        en_data[field] = [translate_text(tag, en_translations) for tag in en_data[field]]
        
        # Process RU section
        if "ru" in result and isinstance(result["ru"], dict):
            ru_data = result["ru"]
            for field in ["video_title", "video_description", "thumbnail_alt_text", "video_tags"]:
                if field in ru_data:
                    if isinstance(ru_data[field], str):
                        ru_data[field] = translate_text(ru_data[field], ru_translations)
                    elif isinstance(ru_data[field], list):
                        # Handle list of tags
                        ru_data[field] = [translate_text(tag, ru_translations) for tag in ru_data[field]]
        
        return result
    
    def _build_translation_context(
        self,
        category: str = "",
        product_type: str = "",
        species: str = "",
        grade: str = "",
    ) -> str:
        """
        Build context string with translation hints for AI.
        
        Args:
            category: Product category (Ukrainian)
            product_type: Product type (Ukrainian)
            species: Wood species (Ukrainian)
            grade: Quality grade
            
        Returns:
            Context string with translations for AI prompt
        """
        lines = []
        
        if category:
            cat_en = self._get_translation(category, "en")
            cat_ru = self._get_translation(category, "ru")
            lines.append(f"Category: {category} (EN: {cat_en}, RU: {cat_ru})")
        
        if product_type:
            type_en = self._get_translation(product_type, "en")
            type_ru = self._get_translation(product_type, "ru")
            lines.append(f"Product Type: {product_type} (EN: {type_en}, RU: {type_ru})")
        
        if species:
            species_en = self._get_translation(species, "en")
            species_ru = self._get_translation(species, "ru")
            lines.append(f"Wood Species: {species} (EN: {species_en}, RU: {species_ru})")
        
        if grade:
            grade_en = self._get_translation(grade, "en")
            grade_ru = self._get_translation(grade, "ru")
            lines.append(f"Grade: {grade} (EN: {grade_en}, RU: {grade_ru})")
        
        return "\n".join(lines)
    
    def generate_seo_metadata(
        self,
        image_path: Optional[Path] = None,
        image_bytes: Optional[bytes] = None,
        category: str = "",
        product_type: str = "",
        species: str = "",
        finish: str = "",
        thickness: str = "",
        size: str = "",
        grade: str = "",
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Generate SEO metadata for an image using Gemini.
        
        Args:
            image_path: Path to the image file
            image_bytes: Image data as bytes (alternative to path)
            category: Product category
            product_type: Specific product type
            species: Wood species
            finish: Surface finish
            thickness: Material thickness
            size: Dimensions
            grade: Quality grade
            
        Returns:
            Dictionary with filename and multi-language metadata
        """
        # Build context string with translation hints for AI guidance
        context_parts = []
        
        if category:
            cat_en = self._get_translation(category, "en")
            cat_ru = self._get_translation(category, "ru")
            context_parts.append(f"Category: {category} (EN: {cat_en}, RU: {cat_ru})")
        if product_type:
            type_en = self._get_translation(product_type, "en")
            type_ru = self._get_translation(product_type, "ru")
            context_parts.append(f"Type: {product_type} (EN: {type_en}, RU: {type_ru})")
        if species:
            species_en = self._get_translation(species, "en")
            species_ru = self._get_translation(species, "ru")
            context_parts.append(f"Wood Species: {species} (EN: {species_en}, RU: {species_ru})")
        if finish:
            finish_en = self._get_translation(finish, "en")
            finish_ru = self._get_translation(finish, "ru")
            context_parts.append(f"Finish: {finish} (EN: {finish_en}, RU: {finish_ru})")
        if thickness:
            # Get imperial equivalent if available
            imperial_value = self._get_imperial_value(thickness)
            if imperial_value:
                context_parts.append(f"Thickness: {thickness} ({imperial_value})")
            else:
                context_parts.append(f"Thickness: {thickness}")
        if size:
            context_parts.append(f"Size: {size}")
        if grade:
            grade_en = self._get_translation(grade, "en")
            grade_ru = self._get_translation(grade, "ru")
            context_parts.append(f"Grade: {grade} (EN: {grade_en}, RU: {grade_ru})")
        
        context = "\n".join(context_parts) if context_parts else "General wood product"
        
        prompt = f"""You are a senior SEO specialist for WoodWay Expert, a premium Ukrainian wood products company specializing in high-quality lumber, veneer, and wood materials for professional woodworkers and furniture manufacturers.

PRODUCT CONTEXT:
{context}

YOUR TASK: Analyze this product image and generate comprehensive, SEO-optimized metadata in THREE languages (Ukrainian, English, Russian).

**CRITICAL LANGUAGE REQUIREMENTS:**
- "ua" section: ONLY Ukrainian language
- "en" section: ONLY English language - translate ALL terms
- "ru" section: ONLY Russian language - translate ALL terms
- Use the translations provided in parentheses above
- NEVER mix languages within a section

=== IMAGE ANALYSIS INSTRUCTIONS ===
Look at the actual image and describe:
- The wood grain pattern (straight, wavy, interlocked, cathedral)
- Color tones (golden, honey, chocolate, reddish, pale, deep brown)
- Surface texture (smooth, rough-sawn, brushed)
- Visible features (knots, figure, sapwood/heartwood)
- Lighting and presentation style

=== 2025-2026 SEO BEST PRACTICES ===

**1. ALT_TEXT (80-125 characters):**
Write a descriptive, accessible alt text that:
- Describes WHAT is visually shown in the image
- Includes the product category, type, species naturally
- Mentions visible characteristics (grain, color, texture)
- Is conversational for voice search
- Does NOT start with "image of" or "picture of"

GOOD EXAMPLES:
- "Premium edged American Walnut lumber board showing rich chocolate brown grain with natural figure, 52mm thick"
- "Close-up of oak veneer sheet with cathedral grain pattern and golden honey tones, furniture-grade quality"
- "Stack of kiln-dried maple lumber boards with pale cream color and straight grain, Extra grade"

**2. TITLE (50-60 characters):**
Create an engaging, keyword-rich title:
- Start with Category + Type + Species
- Include thickness or key specification
- End with "| WoodWay Expert"
- Make it compelling for search results

GOOD EXAMPLES:
- "Lumber Edged American Walnut 52mm Extra | WoodWay Expert"
- "Oak Veneer Sliced A-Grade Premium | WoodWay Expert"
- "Birch Plywood 18mm BB/BB | WoodWay Expert"

**3. DESCRIPTION (140-160 characters):**
Write a compelling meta description that:
- Answers "What is this?" and "Why should I buy it?"
- Includes product specs (thickness, grade)
- Mentions quality/expertise signals
- Ends with a soft call-to-action
- Is scannable on mobile

GOOD EXAMPLES:
- "Buy premium Edged American Walnut lumber, 52mm (2 inch), Extra grade. Perfect for high-end furniture. Expert selection, fast delivery across Ukraine. Order now!"
- "High-quality sliced Oak veneer, A-grade with stunning cathedral grain. Ideal for professional veneering projects. Ukrainian craftsmanship. Get a quote today."

**4. TAGS (5-7 relevant tags):**
Create a comma-separated list including:
- Category (Lumber, Veneer, Plywood, etc.)
- Product type (Edged, Sliced, etc.)
- Wood species
- Grade/quality
- Thickness with imperial equivalent
- Brand: "WoodWay Expert"
- Relevant use cases (furniture, interior, professional)

GOOD EXAMPLE: "Lumber, Edged, American Walnut, Extra Grade, 52mm 2 inch, WoodWay Expert, furniture wood"

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "ua": {{
    "alt_text": "[80-125 chars describing the image in Ukrainian]",
    "title": "[50-60 chars product title | WoodWay Expert]",
    "description": "[140-160 chars compelling description with CTA]",
    "tags": "[5-7 relevant tags in Ukrainian]"
  }},
  "en": {{
    "alt_text": "[80-125 chars describing the image in English]",
    "title": "[50-60 chars product title | WoodWay Expert]",
    "description": "[140-160 chars compelling description with CTA]",
    "tags": "[5-7 relevant tags in English]"
  }},
  "ru": {{
    "alt_text": "[80-125 chars describing the image in Russian]",
    "title": "[50-60 chars product title | WoodWay Expert]",
    "description": "[140-160 chars compelling description with CTA]",
    "tags": "[5-7 relevant tags in Russian]"
  }}
}}"""

        # Prepare content parts
        contents = []
        
        # Add image if provided
        if image_path:
            image_path = Path(image_path)
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Determine MIME type
            suffix = image_path.suffix.lower()
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.gif': 'image/gif',
            }
            mime_type = mime_types.get(suffix, 'image/jpeg')
            
            contents.append(types.Part.from_bytes(data=image_data, mime_type=mime_type))
        elif image_bytes:
            # Assume JPEG if bytes provided without path
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'))
        
        contents.append(prompt)
        
        # Retry logic with validation
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.config.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=self.config.temperature,
                        max_output_tokens=self.config.max_output_tokens,
                    )
                )
                
                # Parse response
                response_text = response.text.strip()
                
                # Try to extract JSON from response (handle markdown code blocks)
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
                if json_match:
                    response_text = json_match.group(1)
                
                # Parse JSON
                result = json.loads(response_text)
                
                # Validate structure
                if not all(key in result for key in ['ua', 'en', 'ru']):
                    raise ValueError("Invalid response structure: missing language keys")
                
                # Validate each language has required fields
                required_fields = ['alt_text', 'title', 'description', 'tags']
                for lang in ['ua', 'en', 'ru']:
                    if lang not in result:
                        raise ValueError(f"Missing language section: {lang}")
                    lang_data = result[lang]
                    if not isinstance(lang_data, dict):
                        raise ValueError(f"Invalid structure for {lang}")
                    
                    # Check for missing fields and add empty defaults
                    for field in required_fields:
                        if field not in lang_data:
                            lang_data[field] = ""
                
                # Validate tags are present and not empty
                tags_missing = False
                for lang in ['ua', 'en', 'ru']:
                    if not result[lang].get('tags', '').strip():
                        tags_missing = True
                        break
                
                if tags_missing and attempt < max_retries:
                    # Retry if tags are missing
                    continue
                
                # Post-process to ensure proper translations in EN/RU sections
                result = self._post_process_translations(result)
                
                return result
                
            except json.JSONDecodeError as e:
                last_error = e
                if attempt < max_retries:
                    continue
            except ValueError as e:
                last_error = e
                if attempt < max_retries:
                    continue
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    continue
        
        # Return fallback structure after all retries failed
        return self._generate_fallback(category, product_type, species, grade, thickness)
    
    def _generate_fallback(
        self,
        category: str = "",
        product_type: str = "",
        species: str = "",
        grade: str = "",
        thickness: str = "",
    ) -> Dict[str, Any]:
        """Generate comprehensive fallback metadata when AI fails."""
        # Get translations for each language
        cat_ua = category or ""
        cat_en = self._get_translation(category, "en") if category else ""
        cat_ru = self._get_translation(category, "ru") if category else ""
        
        type_ua = product_type or ""
        type_en = self._get_translation(product_type, "en") if product_type else ""
        type_ru = self._get_translation(product_type, "ru") if product_type else ""
        
        species_ua = species or ""
        species_en = self._get_translation(species, "en") if species else ""
        species_ru = self._get_translation(species, "ru") if species else ""
        
        grade_ua = grade or ""
        grade_en = self._get_translation(grade, "en") if grade else ""
        grade_ru = self._get_translation(grade, "ru") if grade else ""
        
        # Get imperial thickness
        imperial = self._get_imperial_value(thickness) if thickness else ""
        thickness_display = f"{thickness} ({imperial})" if imperial else thickness
        
        # Build product names
        parts_ua = [p for p in [cat_ua, type_ua, species_ua] if p]
        product_name_ua = " ".join(parts_ua) if parts_ua else "Деревина"
        
        parts_en = [p for p in [cat_en, type_en, species_en] if p]
        product_name_en = " ".join(parts_en) if parts_en else "Wood product"
        
        parts_ru = [p for p in [cat_ru, type_ru, species_ru] if p]
        product_name_ru = " ".join(parts_ru) if parts_ru else "Древесина"
        
        # Generate comprehensive tags
        tags_ua_parts = [p for p in [cat_ua, type_ua, species_ua, grade_ua, thickness, "меблі", "WoodWay Expert"] if p]
        tags_en_parts = [p for p in [cat_en, type_en, species_en, grade_en, thickness_display, "furniture wood", "WoodWay Expert"] if p]
        tags_ru_parts = [p for p in [cat_ru, type_ru, species_ru, grade_ru, thickness, "мебельная древесина", "WoodWay Expert"] if p]
        
        tags_ua = ", ".join(tags_ua_parts) if tags_ua_parts else "WoodWay Expert"
        tags_en = ", ".join(tags_en_parts) if tags_en_parts else "WoodWay Expert"
        tags_ru = ", ".join(tags_ru_parts) if tags_ru_parts else "WoodWay Expert"
        
        # Build comprehensive descriptions
        grade_text_ua = f" {grade_ua} ґатунок," if grade_ua else ""
        grade_text_en = f" {grade_en} grade," if grade_en else ""
        grade_text_ru = f" {grade_ru} сорт," if grade_ru else ""
        
        thickness_text = f" {thickness_display}," if thickness_display else ""
        
        return {
            "ua": {
                "alt_text": f"Преміум {product_name_ua.lower()} з натуральною текстурою деревини,{grade_text_ua}{thickness_text} високої якості для меблів та інтер'єру"[:125],
                "title": f"{product_name_ua}{' ' + grade_ua if grade_ua else ''} | WoodWay Expert"[:60],
                "description": f"Купити преміум {product_name_ua.lower()},{grade_text_ua}{thickness_text} ідеально для меблів. Українська майстерність, швидка доставка. Замовте у WoodWay Expert!"[:160],
                "tags": tags_ua,
            },
            "en": {
                "alt_text": f"Premium {product_name_en.lower()} with natural wood grain pattern,{grade_text_en}{thickness_text} high quality for furniture and interior"[:125],
                "title": f"{product_name_en}{' ' + grade_en if grade_en else ''} | WoodWay Expert"[:60],
                "description": f"Buy premium {product_name_en.lower()},{grade_text_en}{thickness_text} perfect for furniture projects. Ukrainian craftsmanship, fast delivery. Order from WoodWay Expert!"[:160],
                "tags": tags_en,
            },
            "ru": {
                "alt_text": f"Премиум {product_name_ru.lower()} с натуральной текстурой древесины,{grade_text_ru}{thickness_text} высокого качества для мебели и интерьера"[:125],
                "title": f"{product_name_ru}{' ' + grade_ru if grade_ru else ''} | WoodWay Expert"[:60],
                "description": f"Купить премиум {product_name_ru.lower()},{grade_text_ru}{thickness_text} идеально для мебели. Украинское мастерство, быстрая доставка. Закажите у WoodWay Expert!"[:160],
                "tags": tags_ru,
            },
        }
    
    def _upload_video_file(self, video_path: Path) -> Optional[Any]:
        """
        Upload a video file to Gemini Files API for analysis.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Uploaded file object or None if upload fails
        """
        try:
            # Determine MIME type
            suffix = video_path.suffix.lower()
            video_mime_types = {
                '.mp4': 'video/mp4',
                '.mov': 'video/quicktime',
                '.avi': 'video/x-msvideo',
                '.mkv': 'video/x-matroska',
                '.webm': 'video/webm',
                '.m4v': 'video/mp4',
            }
            mime_type = video_mime_types.get(suffix, 'video/mp4')
            
            # Upload the video file
            print(f"[Gemini] Uploading video: {video_path.name} ({mime_type})")
            uploaded_file = self.client.files.upload(
                file=video_path,
                config={"mime_type": mime_type}
            )
            
            # Wait for processing to complete
            print(f"[Gemini] Video uploaded, waiting for processing...")
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(2)
                uploaded_file = self.client.files.get(name=uploaded_file.name)
            
            if uploaded_file.state.name == "FAILED":
                print(f"[Gemini] Video processing failed")
                return None
                
            print(f"[Gemini] Video ready for analysis: {uploaded_file.name}")
            return uploaded_file
            
        except Exception as e:
            print(f"[Gemini] Video upload error: {e}")
            return None
    
    def generate_video_seo_metadata(
        self,
        video_path: Optional[Path] = None,
        thumbnail_path: Optional[Path] = None,
        thumbnail_bytes: Optional[bytes] = None,
        video_duration: float = 0.0,
        category: str = "",
        product_type: str = "",
        species: str = "",
        finish: str = "",
        thickness: str = "",
        size: str = "",
        grade: str = "",
        video_type: str = "",  # e.g., "presentation", "review", "tutorial"
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Generate SEO metadata for a video using the full video or thumbnail.
        
        Args:
            video_path: Path to the full video file (preferred - enables full video analysis)
            thumbnail_path: Path to the video thumbnail/poster image (fallback)
            thumbnail_bytes: Thumbnail data as bytes (alternative to path)
            video_duration: Duration of the video in seconds
            category: Product category
            product_type: Specific product type
            species: Wood species
            finish: Surface finish
            thickness: Material thickness
            size: Dimensions
            grade: Quality grade
            video_type: Type of video content (presentation, review, tutorial, etc.)
            max_retries: Number of retries on validation failure
            
        Returns:
            Dictionary with video-specific multi-language metadata
        """
        # Build context string with translation hints
        context_parts = []
        
        # Add product attributes with translations for AI guidance
        if category:
            cat_en = self._get_translation(category, "en")
            cat_ru = self._get_translation(category, "ru")
            context_parts.append(f"Category: {category} (EN: {cat_en}, RU: {cat_ru})")
        if product_type:
            type_en = self._get_translation(product_type, "en")
            type_ru = self._get_translation(product_type, "ru")
            context_parts.append(f"Product Type: {product_type} (EN: {type_en}, RU: {type_ru})")
        if species:
            species_en = self._get_translation(species, "en")
            species_ru = self._get_translation(species, "ru")
            context_parts.append(f"Wood Species: {species} (EN: {species_en}, RU: {species_ru})")
        if finish:
            finish_en = self._get_translation(finish, "en")
            finish_ru = self._get_translation(finish, "ru")
            context_parts.append(f"Finish: {finish} (EN: {finish_en}, RU: {finish_ru})")
        if thickness:
            # Get imperial equivalent if available
            imperial_value = self._get_imperial_value(thickness)
            if imperial_value:
                context_parts.append(f"Thickness: {thickness} ({imperial_value})")
            else:
                context_parts.append(f"Thickness: {thickness}")
        if size:
            context_parts.append(f"Size: {size}")
        if grade:
            grade_en = self._get_translation(grade, "en")
            grade_ru = self._get_translation(grade, "ru")
            context_parts.append(f"Grade: {grade} (EN: {grade_en}, RU: {grade_ru})")
        if video_type:
            context_parts.append(f"Video Type: {video_type}")
        if video_duration > 0:
            minutes = int(video_duration // 60)
            seconds = int(video_duration % 60)
            duration_str = f"{minutes}:{seconds:02d}" if minutes > 0 else f"{seconds}s"
            context_parts.append(f"Duration: {duration_str}")
        
        context = "\n".join(context_parts) if context_parts else "General wood product video"
        
        # Determine if we have video or just thumbnail
        has_full_video = video_path is not None and video_path.exists()
        
        prompt = f"""You are a senior SEO specialist for WoodWay Expert, a premium Ukrainian wood products company specializing in high-quality lumber, veneer, and wood materials.

PRODUCT VIDEO CONTEXT:
{context}

YOUR TASK: {"Watch and analyze this product video" if has_full_video else "Analyze this video thumbnail"} and generate comprehensive SEO-optimized metadata in THREE languages (Ukrainian, English, Russian).

**CRITICAL LANGUAGE REQUIREMENTS:**
- "ua" section: ONLY Ukrainian language
- "en" section: ONLY English language - translate ALL terms
- "ru" section: ONLY Russian language - translate ALL terms
- Use the translations provided in parentheses above
- NEVER mix languages within a section

=== VIDEO ANALYSIS INSTRUCTIONS ===
{"Watch the entire video and describe:" if has_full_video else "Look at the thumbnail and describe:"}
- What wood product is being shown
- The quality and characteristics visible
- Key selling points that would appeal to woodworkers
- The overall presentation style

=== 2025-2026 VIDEO SEO BEST PRACTICES ===

**1. VIDEO_TITLE (50-60 characters):**
Create an engaging, keyword-rich title:
- Start with Category + Type + Species
- Include key specification (thickness/grade)
- Add video type indicator (Review, Showcase, Overview)
- End with "| WoodWay Expert"

GOOD EXAMPLES:
- "Lumber Edged American Walnut 52mm Review | WoodWay Expert"
- "Premium Oak Veneer A-Grade Showcase | WoodWay Expert"
- "Birch Plywood 18mm Overview | WoodWay Expert"

**2. VIDEO_DESCRIPTION (140-160 characters):**
Write a compelling description:
- Describe what viewers will see/learn
- Include product specs (thickness with imperial, grade)
- Mention quality/expertise signals
- End with call-to-action

GOOD EXAMPLES:
- "Watch our detailed review of premium Edged American Walnut lumber, 52mm (2 inch), Extra grade. See the stunning grain patterns. Order samples today!"
- "Discover our premium sliced Oak veneer collection. A-grade quality with cathedral grain. Perfect for high-end furniture projects. Get expert advice!"

**3. THUMBNAIL_ALT_TEXT (80-125 characters):**
Describe the video poster image:
- What's shown in the thumbnail
- Product identification
- Visual characteristics

GOOD EXAMPLE: "Video thumbnail showing stack of premium American Walnut lumber boards with rich chocolate brown grain and Extra grade quality"

**4. VIDEO_TAGS (6-8 relevant tags):**
Include:
- Category, Type, Species (in target language)
- Grade with descriptor
- Thickness with imperial
- Use cases (furniture, interior, woodworking)
- "WoodWay Expert"
- Video type (review, showcase)

GOOD EXAMPLE: "Lumber, Edged, American Walnut, Extra Grade, 52mm 2 inch, furniture wood, wood review, WoodWay Expert"

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "ua": {{
    "video_title": "[50-60 chars engaging title | WoodWay Expert]",
    "video_description": "[140-160 chars description with CTA]",
    "thumbnail_alt_text": "[80-125 chars thumbnail description]",
    "video_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]
  }},
  "en": {{
    "video_title": "[50-60 chars engaging title | WoodWay Expert]",
    "video_description": "[140-160 chars description with CTA]",
    "thumbnail_alt_text": "[80-125 chars thumbnail description]",
    "video_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]
  }},
  "ru": {{
    "video_title": "[50-60 chars engaging title | WoodWay Expert]",
    "video_description": "[140-160 chars description with CTA]",
    "thumbnail_alt_text": "[80-125 chars thumbnail description]",
    "video_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]
  }}
}}"""

        # Prepare content parts
        contents = []
        uploaded_video_file = None
        
        # Try to upload full video first (preferred for better analysis)
        if video_path and video_path.exists():
            uploaded_video_file = self._upload_video_file(video_path)
            if uploaded_video_file:
                contents.append(types.Part.from_uri(
                    file_uri=uploaded_video_file.uri,
                    mime_type=uploaded_video_file.mime_type
                ))
        
        # Fall back to thumbnail if video upload failed or not provided
        if not uploaded_video_file:
            if thumbnail_path:
                thumbnail_path = Path(thumbnail_path)
                with open(thumbnail_path, 'rb') as f:
                    image_data = f.read()
                
                # Determine MIME type
                suffix = thumbnail_path.suffix.lower()
                mime_types = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.webp': 'image/webp',
                    '.gif': 'image/gif',
                }
                mime_type = mime_types.get(suffix, 'image/jpeg')
                
                contents.append(types.Part.from_bytes(data=image_data, mime_type=mime_type))
            elif thumbnail_bytes:
                # Assume JPEG if bytes provided without path
                contents.append(types.Part.from_bytes(data=thumbnail_bytes, mime_type='image/jpeg'))
        
        contents.append(prompt)
        
        # Retry logic with validation
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.config.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=self.config.temperature,
                        max_output_tokens=self.config.max_output_tokens,
                    )
                )
                
                # Parse response
                response_text = response.text.strip()
                
                # Try to extract JSON from response (handle markdown code blocks)
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
                if json_match:
                    response_text = json_match.group(1)
                
                # Parse JSON
                result = json.loads(response_text)
                
                # Validate structure
                if not all(key in result for key in ['ua', 'en', 'ru']):
                    raise ValueError("Invalid response structure: missing language keys")
                
                # Validate each language has required fields
                required_fields = ['video_title', 'video_description', 'thumbnail_alt_text', 'video_tags']
                for lang in ['ua', 'en', 'ru']:
                    if lang not in result:
                        raise ValueError(f"Missing language section: {lang}")
                    lang_data = result[lang]
                    if not isinstance(lang_data, dict):
                        raise ValueError(f"Invalid structure for {lang}")
                    
                    # Check for missing fields and add empty defaults
                    for field in required_fields:
                        if field not in lang_data:
                            lang_data[field] = "" if field != 'video_tags' else []
                    
                    # Convert video_tags list to comma-separated string if it's a list
                    if isinstance(lang_data.get('video_tags'), list):
                        lang_data['video_tags'] = ", ".join(lang_data['video_tags'])
                
                # Validate tags are present and not empty
                tags_missing = False
                for lang in ['ua', 'en', 'ru']:
                    tags = result[lang].get('video_tags', '')
                    if not tags or (isinstance(tags, str) and not tags.strip()):
                        tags_missing = True
                        break
                
                if tags_missing and attempt < max_retries:
                    # Retry if tags are missing
                    continue
                
                # Post-process to ensure proper translations in EN/RU sections
                result = self._post_process_video_translations(result)
                
                return result
                
            except json.JSONDecodeError as e:
                last_error = e
                if attempt < max_retries:
                    continue
            except ValueError as e:
                last_error = e
                if attempt < max_retries:
                    continue
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    continue
        
        # Return fallback structure after all retries failed
        return self._generate_video_fallback(category, product_type, species, video_type, grade, thickness)
    
    def _generate_video_fallback(
        self,
        category: str = "",
        product_type: str = "",
        species: str = "",
        video_type: str = "",
        grade: str = "",
        thickness: str = "",
    ) -> Dict[str, Any]:
        """Generate comprehensive fallback video metadata when AI fails."""
        # Get translations for each language
        cat_ua = category or ""
        cat_en = self._get_translation(category, "en") if category else ""
        cat_ru = self._get_translation(category, "ru") if category else ""
        
        type_ua = product_type or ""
        type_en = self._get_translation(product_type, "en") if product_type else ""
        type_ru = self._get_translation(product_type, "ru") if product_type else ""
        
        species_ua = species or ""
        species_en = self._get_translation(species, "en") if species else ""
        species_ru = self._get_translation(species, "ru") if species else ""
        
        grade_ua = grade or ""
        grade_en = self._get_translation(grade, "en") if grade else ""
        grade_ru = self._get_translation(grade, "ru") if grade else ""
        
        # Get imperial thickness
        imperial = self._get_imperial_value(thickness) if thickness else ""
        thickness_display = f"{thickness} ({imperial})" if imperial else thickness
        
        # Build product names
        parts_ua = [p for p in [cat_ua, type_ua, species_ua] if p]
        product_name_ua = " ".join(parts_ua) if parts_ua else "Продукт"
        
        parts_en = [p for p in [cat_en, type_en, species_en] if p]
        product_name_en = " ".join(parts_en) if parts_en else "Product"
        
        parts_ru = [p for p in [cat_ru, type_ru, species_ru] if p]
        product_name_ru = " ".join(parts_ru) if parts_ru else "Продукт"
        
        # Translate video type
        video_type_map = {
            "product showcase": ("Огляд продукту", "Product Showcase", "Обзор продукта"),
            "review": ("Огляд", "Review", "Обзор"),
            "tutorial": ("Інструкція", "Tutorial", "Инструкция"),
            "presentation": ("Презентація", "Presentation", "Презентация"),
        }
        vt_lower = video_type.lower() if video_type else "product showcase"
        video_type_ua, video_type_en, video_type_ru = video_type_map.get(vt_lower, ("Огляд", "Review", "Обзор"))
        
        # Build comprehensive tags
        tags_ua_parts = [p for p in [cat_ua, type_ua, species_ua, grade_ua, thickness, "відео огляд", "WoodWay Expert"] if p]
        tags_en_parts = [p for p in [cat_en, type_en, species_en, grade_en, thickness_display, "video review", "WoodWay Expert"] if p]
        tags_ru_parts = [p for p in [cat_ru, type_ru, species_ru, grade_ru, thickness, "видео обзор", "WoodWay Expert"] if p]
        
        tags_ua = ", ".join(tags_ua_parts) if tags_ua_parts else "WoodWay Expert"
        tags_en = ", ".join(tags_en_parts) if tags_en_parts else "WoodWay Expert"
        tags_ru = ", ".join(tags_ru_parts) if tags_ru_parts else "WoodWay Expert"
        
        # Build grade/thickness text
        spec_ua = f", {grade_ua}" if grade_ua else ""
        spec_ua += f", {thickness}" if thickness else ""
        spec_en = f", {grade_en}" if grade_en else ""
        spec_en += f", {thickness_display}" if thickness_display else ""
        spec_ru = f", {grade_ru}" if grade_ru else ""
        spec_ru += f", {thickness}" if thickness else ""
        
        return {
            "ua": {
                "video_title": f"{product_name_ua} {video_type_ua} | WoodWay Expert"[:60],
                "video_description": f"Дивіться детальний огляд преміум {product_name_ua.lower()}{spec_ua}. Українська якість, експертний підбір. Замовте зразки у WoodWay Expert!"[:160],
                "thumbnail_alt_text": f"Кадр з відео огляду преміум {product_name_ua.lower()}{spec_ua} з натуральною текстурою деревини"[:125],
                "video_tags": tags_ua,
            },
            "en": {
                "video_title": f"{product_name_en} {video_type_en} | WoodWay Expert"[:60],
                "video_description": f"Watch our detailed review of premium {product_name_en.lower()}{spec_en}. Ukrainian quality, expert selection. Order samples from WoodWay Expert!"[:160],
                "thumbnail_alt_text": f"Video frame showing premium {product_name_en.lower()}{spec_en} with natural wood grain texture"[:125],
                "video_tags": tags_en,
            },
            "ru": {
                "video_title": f"{product_name_ru} {video_type_ru} | WoodWay Expert"[:60],
                "video_description": f"Смотрите детальный обзор премиум {product_name_ru.lower()}{spec_ru}. Украинское качество, экспертный подбор. Закажите образцы у WoodWay Expert!"[:160],
                "thumbnail_alt_text": f"Кадр из видео обзора премиум {product_name_ru.lower()}{spec_ru} с натуральной текстурой древесины"[:125],
                "video_tags": tags_ru,
            },
        }
    
    def test_connection(self) -> bool:
        """Test if the API connection is working."""
        try:
            response = self.client.models.generate_content(
                model=self.config.model,
                contents="Say 'OK' if you can read this.",
            )
            return bool(response.text)
        except Exception:
            return False
    
    def list_available_models(self) -> list:
        """
        Get list of available Gemini models.
        
        Returns:
            List of model names suitable for text generation
        """
        try:
            models = self.client.models.list()
            # Filter for models that support generateContent
            available = []
            for model in models:
                model_name = model.name
                # Remove 'models/' prefix if present
                if model_name.startswith('models/'):
                    model_name = model_name[7:]
                
                # Only include generative models (not embedding, image generation, etc.)
                if 'gemini' in model_name.lower() and 'embed' not in model_name.lower() and 'image' not in model_name.lower():
                    available.append(model_name)
            
            # Sort: preview/newest first, then by version
            def sort_key(name):
                if 'preview' in name or 'latest' in name:
                    return (0, name)
                return (1, name)
            
            return sorted(available, key=sort_key)
        except Exception as e:
            print(f"Error listing models: {e}")
            # Fallback with latest models from the image
            return [
                "gemini-3-flash-preview",
                "gemini-3-pro-preview", 
                "gemini-flash-latest",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-2.5-flash-lite",
                "gemini-flash-lite-latest",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-1.5-pro"
            ]


def create_client_from_settings() -> Optional[GeminiClient]:
    """
    Create a Gemini client from local appdata settings.
    
    Returns:
        GeminiClient if API key is available, None otherwise
    """
    from src.core.settings import load_gemini_key
    
    api_key = load_gemini_key()
    if not api_key:
        return None
    
    config = GeminiConfig(api_key=api_key)
    return GeminiClient(config)


def create_client_from_env() -> Optional[GeminiClient]:
    """
    Create a Gemini client from settings only (deprecated name, kept for compatibility).
    This function now only uses settings, not environment variables.
    
    Returns:
        GeminiClient if API key is available, None otherwise
    """
    # Only use settings - no environment variable fallback
    return create_client_from_settings()

