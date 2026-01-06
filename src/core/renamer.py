"""
SEO-friendly file renaming module with algorithmic naming based on product attributes.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .transliterate import to_seo_slug


@dataclass
class ProductAttributes:
    """Product attributes for generating SEO filename."""
    category: str = ""
    product_type: str = ""
    species: str = ""
    thickness: str = ""
    finish: str = ""
    size: str = ""
    grade: str = ""
    extra: str = ""
    
    def to_dict(self) -> Dict[str, str]:
        return {k: v for k, v in self.__dict__.items() if v}


@dataclass
class SEOMetadata:
    """Multi-language SEO metadata for an image."""
    filename: str = ""
    ua: Dict[str, str] = field(default_factory=lambda: {"alt_text": "", "title": "", "description": "", "tags": ""})
    en: Dict[str, str] = field(default_factory=lambda: {"alt_text": "", "title": "", "description": "", "tags": ""})
    ru: Dict[str, str] = field(default_factory=lambda: {"alt_text": "", "title": "", "description": "", "tags": ""})
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "ua": self.ua.copy(),
            "en": self.en.copy(),
            "ru": self.ru.copy(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SEOMetadata":
        return cls(
            filename=data.get("filename", ""),
            ua=data.get("ua", {"alt_text": "", "title": "", "description": ""}),
            en=data.get("en", {"alt_text": "", "title": "", "description": ""}),
            ru=data.get("ru", {"alt_text": "", "title": "", "description": ""}),
        )


class SEOFileRenamer:
    """
    Generates SEO-friendly filenames based on product attributes.
    """
    
    def __init__(self, categories_path: Optional[Path] = None):
        """
        Initialize renamer with categories data.
        
        Args:
            categories_path: Path to categories.json file
        """
        self.categories_data: Dict[str, Any] = {}
        
        if categories_path is None:
            # Default path relative to this module
            categories_path = Path(__file__).parent.parent / "data" / "categories.json"
        
        if categories_path.exists():
            with open(categories_path, 'r', encoding='utf-8') as f:
                self.categories_data = json.load(f)
    
    def generate_filename(
        self,
        attributes: ProductAttributes,
        index: int = 0,
        extension: str = "webp"
    ) -> str:
        """
        Generate SEO-friendly filename from product attributes.
        
        Args:
            attributes: Product attributes
            index: Sequential number (0 = no number, 1+ = add number)
            extension: File extension
            
        Returns:
            SEO-friendly filename
        """
        parts = []
        
        # Build filename parts in order of importance
        # Include category first, then product_type (if both are present)
        if attributes.category:
            parts.append(self._get_slug(attributes.category))
        if attributes.product_type:
            parts.append(self._get_slug(attributes.product_type))
        
        if attributes.species:
            parts.append(self._get_slug(attributes.species))
        
        if attributes.finish:
            parts.append(self._get_slug(attributes.finish))
        
        if attributes.thickness:
            parts.append(self._get_slug(attributes.thickness))
        
        if attributes.size:
            parts.append(self._get_slug(attributes.size))
        
        if attributes.grade:
            parts.append(self._get_slug(attributes.grade))
        
        if attributes.extra:
            parts.append(self._get_slug(attributes.extra))
        
        # Add index if provided
        if index > 0:
            parts.append(f"{index:02d}")
        
        # Join with hyphens
        filename = "-".join(filter(None, parts))
        
        # Fallback if empty
        if not filename:
            filename = f"image-{index:03d}" if index > 0 else "image"
        elif index > 0 and not any(str(index).zfill(2) in filename for _ in [1]):
            # Ensure index is in filename
            pass
        
        return f"{filename}.{extension}"
    
    def generate_basic_metadata(
        self,
        attributes: ProductAttributes,
        index: int = 0,
        extension: str = "webp"
    ) -> SEOMetadata:
        """
        Generate comprehensive SEO metadata algorithmically (without AI).
        Uses varied templates with E-E-A-T compliance and 2024-2025 SEO best practices.
        
        Args:
            attributes: Product attributes
            index: Sequential number (used for template rotation)
            extension: File extension
            
        Returns:
            SEOMetadata with filename and complete SEO tags
        """
        filename = self.generate_filename(attributes, index, extension)
        
        # Get localized attribute values
        product_ua = self._get_localized_name(attributes.product_type or attributes.category, "ua")
        product_en = self._get_localized_name(attributes.product_type or attributes.category, "en")
        product_ru = self._get_localized_name(attributes.product_type or attributes.category, "ru")
        
        # Get category separately (to include even when product_type is present)
        category_ua = self._get_localized_name(attributes.category, "ua") if attributes.category else ""
        category_en = self._get_localized_name(attributes.category, "en") if attributes.category else ""
        category_ru = self._get_localized_name(attributes.category, "ru") if attributes.category else ""
        
        species_ua = self._get_localized_name(attributes.species, "ua") if attributes.species else ""
        species_en = self._get_localized_name(attributes.species, "en") if attributes.species else ""
        species_ru = self._get_localized_name(attributes.species, "ru") if attributes.species else ""
        
        grade_ua = self._get_localized_name(attributes.grade, "ua") if attributes.grade else ""
        grade_en = self._get_localized_name(attributes.grade, "en") if attributes.grade else ""
        grade_ru = self._get_localized_name(attributes.grade, "ru") if attributes.grade else ""
        
        thickness_ua = attributes.thickness if attributes.thickness else ""
        thickness_en = attributes.thickness if attributes.thickness else ""
        thickness_ru = attributes.thickness if attributes.thickness else ""
        
        # Get imperial equivalent for thickness if available
        imperial_value = self._get_imperial_value(attributes.thickness) if attributes.thickness else ""
        
        # Generate metadata using varied templates (rotate based on index)
        template_idx = index % 4  # 4 different templates
        
        metadata = SEOMetadata(
            filename=filename,
            ua=self._generate_ua_metadata(
                category_ua, product_ua, species_ua, grade_ua, thickness_ua, imperial_value, template_idx
            ),
            en=self._generate_en_metadata(
                category_en, product_en, species_en, grade_en, thickness_en, imperial_value, template_idx
            ),
            ru=self._generate_ru_metadata(
                category_ru, product_ru, species_ru, grade_ru, thickness_ru, imperial_value, template_idx
            ),
        )
        
        return metadata
    
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
    
    def _format_thickness_with_imperial(self, thickness: str, imperial: str, lang: str) -> str:
        """Format thickness with imperial measurement in parentheses."""
        if not thickness:
            return ""
        if not imperial:
            return thickness
        
        # For UA/RU: metric first, imperial in parentheses
        # For EN: can use either format, but prefer metric first for consistency
        if lang in ("ua", "ru"):
            return f"{thickness} ({imperial})"
        else:  # en
            return f"{thickness} ({imperial})"
    
    def _generate_ua_metadata(
        self, category: str, product: str, species: str, grade: str, thickness: str, imperial: str, template_idx: int
    ) -> Dict[str, str]:
        """Generate Ukrainian metadata with varied templates."""
        # Build parts list for checking if we have content
        parts = []
        if category:
            parts.append(category)
        if species:
            parts.append(species)
        if product:
            parts.append(product)
        if grade:
            parts.append(grade)
        if thickness:
            parts.append(thickness)
        
        # Build display strings with category included
        # Always include category when present, even if product_type is also present
        # Format: "Category ProductType" or just "Category" if no product_type
        if category and product and category != product:
            # Both category and product_type are present and different
            category_product = f"{category} {product}"
        elif category:
            # Only category
            category_product = category
        elif product:
            # Only product_type (no category)
            category_product = product
        else:
            category_product = ""
        
        category_product_part = f"{category_product} " if category_product else ""
        species_part = species if species else ""
        grade_part = grade if grade else ""
        thickness_part = self._format_thickness_with_imperial(thickness, imperial, "ua")
        
        # Title templates (50-60 chars) - always include category when present
        title_templates = [
            lambda: self._truncate(f"{category_product_part}{species_part} {thickness_part} | WoodWay Expert", 60),
            lambda: self._truncate(f"Купити {category_product_part}{species_part} {grade_part} | WoodWay Expert", 60),
            lambda: self._truncate(f"{category_product_part}{species_part} {grade_part} якість | WoodWay", 60),
            lambda: self._truncate(f"Преміум {category_product_part}{species_part} | WoodWay Expert", 60),
        ]
        
        # Alt text templates (max 125 chars, descriptive) - always include category when present
        alt_templates = [
            lambda: self._truncate(f"Натуральний {category_product_part}{species_part} з {grade_part} ґатунком, показує текстуру дерева", 125),
            lambda: self._truncate(f"{category_product_part}{species_part} деревини, товщина {thickness_part}, високоякісний матеріал", 125),
            lambda: self._truncate(f"Крупний план {category_product_part}{species_part} з природним малюнком дерева", 125),
            lambda: self._truncate(f"Високоякісний {category_product_part}{species_part}, {grade_part} ґатунок, підходить для меблів", 125),
        ]
        
        # Description templates (150-160 chars, E-E-A-T, user intent, CTA) - always include category when present
        desc_templates = [
            lambda: self._truncate(f"Шукаєте {category_product_part}{species_part}? Преміум {grade_part} якість, {thickness_part}. Ідеально для меблів та інтер'єру. Купіть у WoodWay Expert з доставкою по Україні.", 160),
            lambda: self._truncate(f"Замовте {category_product_part}{species_part} онлайн. {thickness_part}, {grade_part} ґатунок. Українська майстерність, висока якість. Швидка доставка. WoodWay Expert.", 160),
            lambda: self._truncate(f"Купити {category_product_part}{species_part} - {grade_part} якість, {thickness_part}. Ідеально для професійних проектів. Експертна консультація. WoodWay Expert.", 160),
            lambda: self._truncate(f"{category_product_part}{species_part} на продаж. {thickness_part}, {grade_part}. Преміум українські деревинні матеріали. Безкоштовна консультація. Замовте у WoodWay Expert.", 160),
        ]
        
        if parts:
            title = self._clean_template_string(title_templates[template_idx]())
            alt_text = self._clean_template_string(alt_templates[template_idx]())
            description = self._clean_template_string(desc_templates[template_idx]())
        else:
            title = "WoodWay Expert"
            alt_text = "Деревина"
            description = "Купити деревину. Доставка по Україні. WoodWay Expert."
        
        # Generate tags from available attributes
        tag_parts = []
        if category:
            tag_parts.append(category)
        if product:
            tag_parts.append(product)
        if species:
            tag_parts.append(species)
        if grade:
            tag_parts.append(grade)
        tag_parts.append("WoodWay Expert")
        tags = ", ".join(tag_parts) if tag_parts else ""
        
        return {
            "alt_text": alt_text,
            "title": title,
            "description": description,
            "tags": tags,
        }
    
    def _generate_en_metadata(
        self, category: str, product: str, species: str, grade: str, thickness: str, imperial: str, template_idx: int
    ) -> Dict[str, str]:
        """Generate English metadata with varied templates."""
        # Build parts list for checking if we have content
        parts = []
        if category:
            parts.append(category)
        if species:
            parts.append(species)
        if product:
            parts.append(product)
        if grade:
            parts.append(grade)
        if thickness:
            parts.append(thickness)
        
        # Build display strings with category included
        # Always include category when present, even if product_type is also present
        # Format: "Category ProductType" or just "Category" if no product_type
        if category and product and category != product:
            # Both category and product_type are present and different
            category_product = f"{category} {product}"
        elif category:
            # Only category
            category_product = category
        elif product:
            # Only product_type (no category)
            category_product = product
        else:
            category_product = ""
        
        category_product_part = f"{category_product} " if category_product else ""
        species_part = species if species else ""
        grade_part = grade if grade else ""
        thickness_part = self._format_thickness_with_imperial(thickness, imperial, "en")
        
        # Title templates (50-60 chars) - always include category when present
        title_templates = [
            lambda: self._truncate(f"{category_product_part}{species_part} {thickness_part} | WoodWay Expert", 60),
            lambda: self._truncate(f"Buy {category_product_part}{species_part} {grade_part} | WoodWay Expert", 60),
            lambda: self._truncate(f"{category_product_part}{species_part} {grade_part} Quality | WoodWay", 60),
            lambda: self._truncate(f"Premium {category_product_part}{species_part} | WoodWay Expert", 60),
        ]
        
        # Alt text templates (max 125 chars) - always include category when present
        alt_templates = [
            lambda: self._truncate(f"Natural {category_product_part}{species_part} showing {grade_part} grade wood grain and texture", 125),
            lambda: self._truncate(f"{category_product_part}{species_part} wood, {thickness_part} thickness, high quality material", 125),
            lambda: self._truncate(f"Close-up view of {category_product_part}{species_part} with natural wood pattern", 125),
            lambda: self._truncate(f"High-quality {category_product_part}{species_part} material, {grade_part} grade, suitable for furniture", 125),
        ]
        
        # Description templates (150-160 chars, E-E-A-T) - always include category when present
        desc_templates = [
            lambda: self._truncate(f"Looking for {category_product_part}{species_part}? Premium {grade_part} quality material, {thickness_part}. Perfect for furniture and interior design. Buy from WoodWay Expert with delivery across Ukraine.", 160),
            lambda: self._truncate(f"Order {category_product_part}{species_part} online. {thickness_part}, {grade_part} grade. Ukrainian craftsmanship, high quality. Fast delivery. WoodWay Expert.", 160),
            lambda: self._truncate(f"Buy {category_product_part}{species_part} - {grade_part} quality, {thickness_part}. Ideal for professional projects. Expert advice available. WoodWay Expert.", 160),
            lambda: self._truncate(f"{category_product_part}{species_part} for sale. {thickness_part}, {grade_part}. Premium Ukrainian wood products. Free consultation. Order from WoodWay Expert.", 160),
        ]
        
        if parts:
            title = self._clean_template_string(title_templates[template_idx]())
            alt_text = self._clean_template_string(alt_templates[template_idx]())
            description = self._clean_template_string(desc_templates[template_idx]())
        else:
            title = "WoodWay Expert"
            alt_text = "Wood product"
            description = "Buy wood products. Delivery in Ukraine. WoodWay Expert."
        
        # Generate tags from available attributes
        tag_parts = []
        if category:
            tag_parts.append(category)
        if product:
            tag_parts.append(product)
        if species:
            tag_parts.append(species)
        if grade:
            tag_parts.append(grade)
        tag_parts.append("WoodWay Expert")
        tags = ", ".join(tag_parts) if tag_parts else ""
        
        return {
            "alt_text": alt_text,
            "title": title,
            "description": description,
            "tags": tags,
        }
    
    def _generate_ru_metadata(
        self, category: str, product: str, species: str, grade: str, thickness: str, imperial: str, template_idx: int
    ) -> Dict[str, str]:
        """Generate Russian metadata with varied templates."""
        # Build parts list for checking if we have content
        parts = []
        if category:
            parts.append(category)
        if species:
            parts.append(species)
        if product:
            parts.append(product)
        if grade:
            parts.append(grade)
        if thickness:
            parts.append(thickness)
        
        # Build display strings with category included
        # Always include category when present, even if product_type is also present
        # Format: "Category ProductType" or just "Category" if no product_type
        if category and product and category != product:
            # Both category and product_type are present and different
            category_product = f"{category} {product}"
        elif category:
            # Only category
            category_product = category
        elif product:
            # Only product_type (no category)
            category_product = product
        else:
            category_product = ""
        
        category_product_part = f"{category_product} " if category_product else ""
        species_part = species if species else ""
        grade_part = grade if grade else ""
        thickness_part = self._format_thickness_with_imperial(thickness, imperial, "ru")
        
        # Title templates (50-60 chars) - always include category when present
        title_templates = [
            lambda: self._truncate(f"{category_product_part}{species_part} {thickness_part} | WoodWay Expert", 60),
            lambda: self._truncate(f"Купить {category_product_part}{species_part} {grade_part} | WoodWay Expert", 60),
            lambda: self._truncate(f"{category_product_part}{species_part} {grade_part} качество | WoodWay", 60),
            lambda: self._truncate(f"Премиум {category_product_part}{species_part} | WoodWay Expert", 60),
        ]
        
        # Alt text templates (max 125 chars) - always include category when present
        alt_templates = [
            lambda: self._truncate(f"Натуральный {category_product_part}{species_part} сорт {grade_part}, показывает текстуру дерева", 125),
            lambda: self._truncate(f"{category_product_part}{species_part} древесины, толщина {thickness_part}, высококачественный материал", 125),
            lambda: self._truncate(f"Крупный план {category_product_part}{species_part} с природным рисунком дерева", 125),
            lambda: self._truncate(f"Высококачественный {category_product_part}{species_part}, {grade_part} сорт, подходит для мебели", 125),
        ]
        
        # Description templates (150-160 chars, E-E-A-T) - always include category when present
        desc_templates = [
            lambda: self._truncate(f"Ищете {category_product_part}{species_part}? Премиум {grade_part} качество, {thickness_part}. Идеально для мебели и интерьера. Купите у WoodWay Expert с доставкой по Украине.", 160),
            lambda: self._truncate(f"Закажите {category_product_part}{species_part} онлайн. {thickness_part}, {grade_part} сорт. Украинское мастерство, высокое качество. Быстрая доставка. WoodWay Expert.", 160),
            lambda: self._truncate(f"Купить {category_product_part}{species_part} - {grade_part} качество, {thickness_part}. Идеально для профессиональных проектов. Экспертная консультация. WoodWay Expert.", 160),
            lambda: self._truncate(f"{category_product_part}{species_part} в продаже. {thickness_part}, {grade_part}. Премиум украинские древесные материалы. Бесплатная консультация. Закажите у WoodWay Expert.", 160),
        ]
        
        if parts:
            title = self._clean_template_string(title_templates[template_idx]())
            alt_text = self._clean_template_string(alt_templates[template_idx]())
            description = self._clean_template_string(desc_templates[template_idx]())
        else:
            title = "WoodWay Expert"
            alt_text = "Древесина"
            description = "Купить древесину. Доставка по Украине. WoodWay Expert."
        
        # Generate tags from available attributes
        tag_parts = []
        if category:
            tag_parts.append(category)
        if product:
            tag_parts.append(product)
        if species:
            tag_parts.append(species)
        if grade:
            tag_parts.append(grade)
        tag_parts.append("WoodWay Expert")
        tags = ", ".join(tag_parts) if tag_parts else ""
        
        return {
            "alt_text": alt_text,
            "title": title,
            "description": description,
            "tags": tags,
        }
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Intelligently truncate text to max_length, preserving words."""
        # Clean up multiple spaces first
        import re
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) <= max_length:
            return text
        
        # Try to truncate at word boundary
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.7:  # Only if we're not losing too much
            truncated = truncated[:last_space]
        
        return truncated.strip()
    
    def _clean_template_string(self, text: str) -> str:
        """Clean template string by removing extra spaces from empty variables."""
        import re
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove spaces before/after punctuation
        text = re.sub(r'\s+([|,.-])', r'\1', text)
        text = re.sub(r'([|,.-])\s+', r'\1 ', text)
        # Remove leading/trailing spaces and clean up empty sections
        text = text.strip()
        # Fix cases like "| WoodWay" -> "WoodWay" (if nothing before |)
        text = re.sub(r'^\|\s+', '', text)
        return text
    
    def _get_slug(self, text: str) -> str:
        """Convert text to slug, using predefined slug if available."""
        # Check if it's a known value with a predefined slug
        if self.categories_data:
            for list_name, list_data in self.categories_data.get("lists", {}).items():
                for option in list_data.get("options", []):
                    if option.get("ua") == text or option.get("slug") == text:
                        return option.get("slug", to_seo_slug(text))
            
            for cat_key, cat_data in self.categories_data.get("categories", {}).items():
                if cat_data.get("name_ua") == text:
                    return cat_data.get("slug", to_seo_slug(text))
                for type_key, type_data in cat_data.get("types", {}).items():
                    if type_data.get("name_ua") == text:
                        return type_data.get("slug", to_seo_slug(text))
        
        return to_seo_slug(text)
    
    def _build_description_parts(
        self,
        attributes: ProductAttributes,
        lang: str
    ) -> List[str]:
        """Build description parts for a specific language."""
        parts = []
        
        # Get category/type name
        if attributes.product_type:
            parts.append(self._get_localized_name(attributes.product_type, lang))
        elif attributes.category:
            parts.append(self._get_localized_name(attributes.category, lang))
        
        if attributes.species:
            parts.append(self._get_localized_name(attributes.species, lang))
        
        if attributes.finish:
            parts.append(self._get_localized_name(attributes.finish, lang))
        
        if attributes.thickness:
            parts.append(attributes.thickness)
        
        return parts
    
    def _get_localized_name(self, key: str, lang: str) -> str:
        """Get localized name for a key from enriched JSON data."""
        # Try to find in categories
        for cat_key, cat_data in self.categories_data.get("categories", {}).items():
            if cat_data.get("name_ua") == key:
                if lang == "en":
                    return cat_data.get("name_en", to_seo_slug(key).replace("-", " ").title())
                elif lang == "ru":
                    return cat_data.get("name_ru", key)
                return key  # UA
            
            # Check types
            for type_key, type_data in cat_data.get("types", {}).items():
                if type_data.get("name_ua") == key:
                    if lang == "en":
                        return type_data.get("name_en", to_seo_slug(key).replace("-", " ").title())
                    elif lang == "ru":
                        return type_data.get("name_ru", key)
                    return key  # UA
        
        # Try to find in lists
        for list_name, list_data in self.categories_data.get("lists", {}).items():
            for option in list_data.get("options", []):
                if option.get("ua") == key:
                    if lang == "en":
                        return option.get("en", to_seo_slug(key).replace("-", " ").title())
                    elif lang == "ru":
                        return option.get("ru", key)
                    return key  # UA
        
        # Fallback: transliterate for EN, return original for UA/RU
        if lang == "en":
            return to_seo_slug(key).replace("-", " ").title()
        return key
    
    def get_category_options(self) -> List[Dict[str, str]]:
        """Get list of available categories."""
        options = []
        for key, data in self.categories_data.get("categories", {}).items():
            options.append({
                "key": key,
                "name_ua": data.get("name_ua", key),
                "slug": data.get("slug", key),
            })
        return options
    
    def get_types_for_category(self, category_key: str) -> List[Dict[str, str]]:
        """Get available types for a category."""
        options = []
        category = self.categories_data.get("categories", {}).get(category_key, {})
        for key, data in category.get("types", {}).items():
            options.append({
                "key": key,
                "name_ua": data.get("name_ua", key),
                "slug": data.get("slug", key),
            })
        return options
    
    def get_properties_for_category(self, category_key: str) -> List[str]:
        """Get list of property keys applicable to a category."""
        category = self.categories_data.get("categories", {}).get(category_key, {})
        return category.get("properties", [])
    
    def get_list_options(self, list_name: str) -> List[Dict[str, str]]:
        """Get options for a property list."""
        options = []
        list_data = self.categories_data.get("lists", {}).get(list_name, {})
        for option in list_data.get("options", []):
            options.append({
                "ua": option.get("ua", ""),
                "slug": option.get("slug", ""),
            })
        return options

