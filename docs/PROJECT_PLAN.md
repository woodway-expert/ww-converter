# 🖼️ WoodWay Image Converter & SEO Tool — Project Plan

## 📋 Overview

A Python-based GUI application (.exe) for **WoodWay Expert** that enables mass image renaming, format conversion, and SEO-optimized metadata generation using **Gemini Flash** AI.

**Target Model:** `gemini-flash-latest`

---

## 🎯 Core Features

### 1. Image Processing
- **Mass Conversion:** Convert images to WebP (primary), JPEG, PNG
- **Quality Control:** Configurable compression (1-100%)
- **Resolution Scaling:** Resize images with aspect ratio preservation
- **Batch Processing:** Process multiple images simultaneously

### 2. SEO-Friendly File Naming
**Naming Convention (as per task description):**
- **Format:** `tovar-kharakterystyka-kolir-rozmir.format`
- **Rules:**
  - Latin characters only (transliteration)
  - Words separated by hyphens (`-`)
  - No spaces or underscores (`_`)
  - Lowercase only
  
**Examples:**
- `shpon-dub-naturalnyi.webp`
- `fanera-fsf-berezova-18mm.webp`
- `mdf-plyta-shponovanyi-dub-19mm.webp`

### 3. AI-Powered Meta Tag Generation (Toggle)
- **Algorithmic Mode:** Generate names based on user dropdown selections
- **AI Mode:** Use `gemini-flash-latest` to generate:
  - SEO-optimized file names
  - Alt text descriptions
  - Title attributes
  - Extended descriptions for product pages
  
**🌐 Multi-Language Output (Required):**
All generated tags/descriptions in **3 languages**:
- 🇺🇦 Ukrainian (primary)
- 🇬🇧 English
- 🇷🇺 Russian

### 4. User Interface
- **Dynamic Dropdowns:** Cascading selections (Category → Type → Species → Properties)
- **Image Preview Grid:** Thumbnails with drag-and-drop reordering
- **Order-Based Numbering:** Drag position affects sequential numbering
- **Tag Preview:** Show generated tags before applying
- **Multi-Language Tabs:** UA / EN / RU tabs for viewing/copying each language's tags
- **Copy Fields:** Easy copy-to-clipboard for all metadata fields (per language)
- **Metadata Embedding:** Write EXIF/XMP data into image files (primary language or all)

---

## 🏷️ Data Structure & Dynamic Dropdowns

The application will use a hierarchical JSON structure (`data/categories.json`) to drive the UI.

### Logic Flow
1. **Category** selected (e.g., "Lumber")
2. **Type** dropdown populates (e.g., "Edged", "Unedged")
3. **Properties** appear based on Category (e.g., "Thickness", "Grade" for Lumber; "Backing" for Veneer)

### JSON Schema Example
```json
{
  "categories": {
    "lumber": {
      "name_ua": "Дошка",
      "types": {
        "edged": { "name_ua": "Обрізна", "slug": "obrizna" },
        "unedged": { "name_ua": "Необрізна", "slug": "neobrizna" }
      },
      "properties": ["species", "thickness", "grade", "length"]
    },
    "veneer": {
      "name_ua": "Шпон",
      "types": {
        "sliced": { "name_ua": "Струганий", "slug": "struhanyi" },
        "sawn": { "name_ua": "Пиляний", "slug": "pylianyi" },
        "root": { "name_ua": "Кореневі зрізи", "slug": "korenevi" }
      },
      "properties": ["species", "thickness", "cutting_method"]
    }
  },
  "common_lists": {
    "species": { ... },
    "thickness": { ... }
  }
}
```

## 🏷️ Wood-Way Expert Product Categories (Reference)

### Product Types (Тип товару)
| Ukrainian | Transliterated |
|-----------|----------------|
| Струганий шпон | struhanyi-shpon |
| Пиляний шпон | pylianyi-shpon |
| Шпон кореневі зрізи | shpon-korenevi-zrizy |
| Кромка зі шпону | kromka-zi-shponu |
| Столярні плити (blockboard) БОРД шпонований | stoliarna-plyta-bord-shponovanyi |
| Шпоновані плити ДСП | dsp-shponovanyi |
| МДФ-плити | mdf-plyta |
| Фанера | fanera |
| Фанера береза | fanera-bereza |
| Гнучка фанера сейба | hnuchka-fanera-seiba |
| Фанера шпонована | fanera-shponovana |
| Фанера OKOUME | fanera-okoume |
| Фанера вогнетривка OKOUME | fanera-vohnetrypka-okoume |
| Фанера тополя | fanera-topolia |
| Клей для деревини | klei-dlia-derevyny |
| Дерев'яні декоративні решітки | dereviani-dekoratyvni-reshitky |
| Усе для склеювання шпону | materialy-skleiu-shponu |
| Дошка обрізна та необрізна | doshka-obrizna |
| Олії, лаки, віск для деревини | olii-laky-visk |
| Лакофарбові матеріали | lakofarbovi-materialy |
| Епоксидна смола | epoksydna-smola |
| Стінові панелі | stinovi-paneli |
| Меблевий щит | meblevyi-shchyt |
| Tikkurila | tikkurila |

### Wood Species (Порода дерева)
| Ukrainian | Transliterated |
|-----------|----------------|
| Дуб | dub |
| Бук | buk |
| Ясен | yasen |
| Горіх | horikh |
| Клен | klen |
| Береза | bereza |
| Сосна | sosna |
| Вільха | vilkha |
| Черешня | chereshnia |
| Венге | venhe |
| Зебрано | zebrano |
| Тік | tik |
| Махагон | mahahon |
| Анегрі | anehri |
| Сапелі | sapeli |
| Тополя | topolia |
| Сейба | seiba |
| Окуме | okume |

### Colors/Finishes (Колір/Обробка)
| Ukrainian | Transliterated |
|-----------|----------------|
| Натуральний | naturalnyi |
| Вибілений | vybіlenyi |
| Тонований | tonovanyi |
| Лакований | lakovanyi |
| Матовий | matovyi |
| Глянцевий | hliantsevyi |
| Брашований | brashovanyi |
| Патинований | patynovanyi |

### Sizes/Thickness (Розміри)
- Thickness: 0.6mm, 1mm, 2mm, 3mm, 4mm, 6mm, 9mm, 12mm, 15mm, 18mm, 19mm, 21mm, 24mm, 30mm
- Sheet sizes: 2500x1250, 2800x2070, 3050x1220, custom

### Quality Grades
- A, AB, B, BB, C, CP

---

## 🔧 Technical Architecture

### Tech Stack
```
Python 3.11+
├── GUI: CustomTkinter (modern themed tkinter)
├── Image Processing: Pillow (PIL Fork)
├── AI Integration: google-genai (NEW official Gemini SDK)
├── Metadata: piexif, Pillow (EXIF/XMP)
├── Build: PyInstaller (→ .exe)
└── Config: python-dotenv (env for API key)
```

> ⚠️ **Important:** Using `google-genai` (not deprecated `google-generativeai`)
> GitHub: https://github.com/googleapis/python-genai

### Project Structure
```
ww-converter/
├── docs/
│   └── PROJECT_PLAN.md
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── app.py           # Main application window
│   │   ├── preview_grid.py  # Draggable image grid
│   │   ├── settings_panel.py
│   │   └── widgets/
│   │       ├── image_card.py
│   │       └── tag_field.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── converter.py     # Image conversion logic
│   │   ├── renamer.py       # SEO naming algorithm
│   │   ├── metadata.py      # EXIF/XMP handling
│   │   └── transliterate.py # UA→Latin conversion
│   ├── ai/
│   │   ├── __init__.py
│   │   └── gemini_client.py # Gemini API integration
│   └── data/
│       ├── categories.json  # Product categories
│       └── transliteration.json
├── assets/
│   └── icon.ico
├── .env.example             # API key template
├── requirements.txt
├── build.py                 # PyInstaller build script
└── README.md
```

### API Key Security
```python
# During development: .env file
GEMINI_API_KEY=your_key_here

# For production build: baked into binary
# build.py will embed key from environment variable
```

---

## ✅ Pros

| Aspect | Benefit |
|--------|---------|
| **Efficiency** | Batch processing saves hours of manual work |
| **SEO Compliance** | Consistent naming following Google image SEO guidelines |
| **User Control** | Drag-to-reorder gives precise control over file numbering |
| **AI Enhancement** | Gemini generates contextually relevant descriptions |
| **Product-Specific** | Dropdowns ensure accurate Wood-way product terminology |
| **Metadata Embedding** | Alt text embedded in files travels with them |
| **Offline Capable** | Algorithmic mode works without internet |
| **Copy-Ready** | Easy clipboard copy for CMS integration |

---

## ❌ Cons & Mitigations

| Challenge | Mitigation |
|-----------|------------|
| **API Costs** | Toggle AI on/off; batch requests; use Flash tier (cheaper) |
| **API Key Exposure** | Bake key at build time; obfuscate in binary; limit key permissions |
| **Large Batch Performance** | Async processing with progress bar; chunked batches |
| **Gemini Rate Limits** | Implement retry logic with exponential backoff |
| **Complex UI** | Phased approach: MVP first, then enhancements |
| **Ukrainian Transliteration** | Use standard scientific transliteration (consistent) |
| **Metadata Format Support** | Support both EXIF and XMP for maximum compatibility |
| **PyInstaller .exe Size** | UPX compression; exclude unnecessary modules |

---

## 🚀 Improvements & Suggestions

### Must-Have Additions
1. **Progress Indicators** — Visual feedback for batch operations
2. **Undo/Redo** — Revert changes before saving
3. **Preview Before/After** — Show original vs. new filename
4. **Export Manifest** — CSV/JSON of all renames for records
5. **Preset Configurations** — Save common settings (e.g., "Product Photos", "Website Gallery")

### Nice-to-Have Features
1. **Duplicate Detection** — Warn if generated name already exists
2. **Batch AI Review** — Review all AI suggestions before applying
3. **Template System** — Custom naming patterns like `{category}-{wood}-{num:03d}`
4. **Dark/Light Mode** — Theme toggle for user preference
5. **Auto-Update** — Check for new versions on startup

### AI Prompt Engineering
For optimal Gemini results, send structured context with multi-language output:

```python
from google import genai

client = genai.Client(api_key=API_KEY)

prompt = f"""
Analyze this product image for WoodWay Expert (Ukrainian wood products company).

Product Context:
- Category: {category}
- Wood Type: {wood_species}  
- Finish: {finish}
- Size: {size}

Generate SEO metadata in THREE languages (Ukrainian, English, Russian):

1. filename: SEO-optimized (Latin transliteration, hyphens, no spaces) - SINGLE version
2. alt_text: (max 125 chars each language)
3. title: (max 60 chars each language)  
4. description: (max 160 chars each language)

Follow Google Image SEO best practices:
- Descriptive but concise
- Include relevant keywords naturally
- No keyword stuffing
- Human-readable

Return JSON in this exact structure:
{{
  "filename": "shpon-dub-naturalnyi-0.6mm.webp",
  "ua": {{
    "alt_text": "...",
    "title": "...",
    "description": "..."
  }},
  "en": {{
    "alt_text": "...",
    "title": "...",
    "description": "..."
  }},
  "ru": {{
    "alt_text": "...",
    "title": "...",
    "description": "..."
  }}
}}
"""

response = client.models.generate_content(
    model="gemini-flash-latest",
    contents=prompt
)
```

---

## 📊 SEO Best Practices Reference

### Image File Naming
- ✅ Use hyphens (`-`) to separate words
- ✅ Keep names descriptive but concise (3-5 words)
- ✅ Include primary keyword
- ✅ Use lowercase letters only
- ✅ Include product identifiers (size, color, material)
- ❌ No spaces, underscores, or special characters
- ❌ No generic names like `IMG_001.jpg` or `photo.png`
- ❌ No keyword stuffing

### Alt Text Guidelines
- Describe the image content accurately
- Keep under 125 characters
- Include target keywords naturally
- Don't start with "Image of..." or "Picture of..."
- Be specific: "Oak veneer sheet 18mm natural finish" > "Wood product"

### Meta Description
- 150-160 characters maximum
- Include call-to-action when appropriate
- Highlight unique selling points
- Include product specifications

### Multi-Language SEO Notes
- **UA (Ukrainian):** Primary for Ukrainian market SEO, use native terminology
- **EN (English):** For international visibility and Google Images global search
- **RU (Russian):** Large Russian-speaking audience in Ukraine and CIS markets

**Example Output:**
```json
{
  "filename": "shpon-dub-naturalnyi-0.6mm.webp",
  "ua": {
    "alt_text": "Струганий шпон дуба натуральний 0.6 мм — деревина преміум якості",
    "title": "Шпон дуба натуральний | WoodWay Expert",
    "description": "Купити струганий шпон дуба 0.6 мм з натуральним малюнком. Ідеально для меблів та оздоблення. Доставка по Україні."
  },
  "en": {
    "alt_text": "Natural oak sliced veneer 0.6mm premium quality wood grain",
    "title": "Natural Oak Veneer | WoodWay Expert",
    "description": "Buy premium sliced oak veneer 0.6mm with natural grain pattern. Perfect for furniture and interior finishing."
  },
  "ru": {
    "alt_text": "Строганый шпон дуба натуральный 0.6 мм — древесина премиум качества",
    "title": "Шпон дуба натуральный | WoodWay Expert",
    "description": "Купить строганый шпон дуба 0.6 мм с натуральным рисунком. Идеально для мебели и отделки. Доставка по Украине."
  }
}
```

---

## 📅 Development Phases

### Phase 1: Core MVP (Week 1-2)
- [ ] Project setup & dependencies
- [ ] Basic GUI with file selection
- [ ] Image preview grid (non-draggable)
- [ ] WebP conversion with quality settings
- [ ] Algorithmic renaming (dropdown-based)

### Phase 2: Enhanced UI (Week 3)
- [ ] Drag-and-drop reordering
- [ ] Sequential numbering based on order
- [ ] Preview of new filenames
- [ ] Copy-to-clipboard functionality

### Phase 3: AI Integration (Week 4)
- [ ] Gemini API client
- [ ] Toggle between algorithmic/AI modes
- [ ] Generated tag display and editing
- [ ] Error handling and rate limiting

### Phase 4: Polish & Build (Week 5)
- [ ] Metadata embedding (EXIF/XMP)
- [ ] Settings persistence
- [ ] PyInstaller .exe build
- [ ] Testing & bug fixes

---

## 📚 Resources

- [google-genai SDK (Official)](https://github.com/googleapis/python-genai)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [Image SEO Best Practices](https://developers.google.com/search/docs/appearance/google-images)
- [CustomTkinter Documentation](https://customtkinter.tomschimansky.com/)
- [PyInstaller Manual](https://pyinstaller.org/en/stable/)
- [WoodWay Expert Website](https://wood-way.expert)

---

## 🔐 Environment Configuration

```bash
# .env file (development only, not committed to git)
GEMINI_API_KEY=your_gemini_api_key_here

# For build, set environment variable:
# Windows: set GEMINI_API_KEY=your_key
# Then run: python build.py
```

---

*Document Version: 1.0*  
*Created: January 2026*  
*Project: WoodWay Expert Image Converter*

