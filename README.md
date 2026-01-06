# 🖼️🎬 WoodWay Image & Video Converter

A Python-based GUI application for mass image/video renaming, format conversion, and SEO-optimized metadata generation.

Built for **WoodWay Expert** (Ukrainian wood products company).

## ✨ Features

### Image Processing
- **Mass Image Conversion** — Convert to WebP, JPEG, PNG with configurable quality
- **Resolution Presets** — SEO-optimal, high quality, social media, thumbnail sizes
- **Metadata Embedding** — EXIF/XMP metadata written to files

### Video Processing (NEW)
- **Web Video Optimization** — Convert to MP4 (H.264) or WebM (VP9)
- **Quality Presets** — 720p SEO optimal, 1080p high quality, 480p fast loading
- **Automatic Thumbnails** — Extract poster images from videos
- **CRF-Based Compression** — Fine-tune quality vs file size

### SEO Features
- **SEO-Friendly Naming** — Algorithmic filename generation following SEO best practices
- **AI-Powered Descriptions** — Optional Gemini AI integration for generating meta tags
- **Multi-Language Support** — Tags in Ukrainian, English, and Russian
- **Dynamic Dropdowns** — Category-specific product attributes
- **Drag & Drop** — Reorder media to control numbering
- **Copy-Ready Tags** — Easy clipboard copy for CMS integration

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- (Optional) Gemini API key for AI features
- (Optional) **FFmpeg** for video processing

### FFmpeg Installation (for Video Support)

Video conversion requires FFmpeg to be installed and available in PATH:

**Windows (choose one):**
```bash
# Using winget (Windows 10/11)
winget install ffmpeg

# Using Chocolatey
choco install ffmpeg

# Manual: Download from https://ffmpeg.org/download.html and add to PATH
```

**Linux:**
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
sudo dnf install ffmpeg  # Fedora
```

**macOS:**
```bash
brew install ffmpeg
```

### Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/ww-converter.git
cd ww-converter

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
python -m src.main
```

Or directly:

```bash
python src/main.py
```

### Setting up AI Features

To enable Gemini AI-powered metadata generation:

1. Get an API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a `.env` file in the project root:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
3. Restart the application

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

## 🏗️ Building Executable

To create a standalone `.exe` file:

```bash
# Set API key (optional, for AI features)
set GEMINI_API_KEY=your_key_here

# Run build script
python build.py
```

The executable will be created in the `dist/` folder.

## 📁 Project Structure

```
ww-converter/
├── src/
│   ├── main.py              # Entry point
│   ├── gui/                 # GUI components
│   │   └── app.py           # Main application window
│   ├── core/                # Core functionality
│   │   ├── converter.py     # Image conversion
│   │   ├── video_converter.py # Video conversion (NEW)
│   │   ├── renamer.py       # SEO naming logic
│   │   ├── metadata.py      # EXIF/XMP handling
│   │   └── transliterate.py
│   ├── ai/                  # AI integration
│   │   └── gemini_client.py # Gemini AI for SEO metadata
│   └── data/
│       └── categories.json  # Product categories
├── tests/                   # Unit tests
├── docs/
│   └── PROJECT_PLAN.md      # Detailed project plan
├── requirements.txt
├── build.py                 # PyInstaller build script
└── README.md
```

## 🎯 Usage Guide

1. **Add Media** — Click "Add Files" or drag images/videos into the window
2. **Select Category** — Choose product category from dropdown (e.g., "Шпон", "Фанера")
3. **Set Attributes** — Select type, wood species, thickness, etc.
4. **Configure Output** — Choose format, quality, and resolution presets
5. **Generate Names** — Click "Generate Names" (toggle AI for richer descriptions)
6. **Review & Reorder** — Drag items to change order/numbering
7. **Copy Tags** — Use the UA/EN/RU tabs to copy metadata
8. **Convert & Save** — Click "Convert & Save" to process all media

### Video-Specific Settings

When videos are detected, additional settings appear:
- **Video Format** — MP4 (H.264, universal) or WebM (VP9, modern browsers)
- **Resolution Preset** — 720p SEO optimal, 1080p high quality, 480p fast loading
- **Quality (CRF)** — Lower = better quality, larger file (18-28 recommended)
- **Extract Thumbnail** — Automatically create poster image for each video

## 📝 SEO Naming Convention

Files are named following this structure:

```
{product-type}-{species}-{finish}-{size}.{format}
```

**Image Examples:**
- `shpon-dub-naturalnyy-0.6mm.webp`
- `fanera-fsf-bereza-18mm.webp`

**Video Examples:**
- `shpon-dub-naturalnyi-prezentacija.mp4`
- `fanera-bereza-18mm-ohliad.webm`

**Video Thumbnail:**
- `shpon-dub-naturalnyi-prezentacija-poster.webp`

**Rules:**
- Latin characters only (Ukrainian transliterated)
- Words separated by hyphens
- No spaces or underscores
- Lowercase only

## 🌍 Languages

Generated metadata includes:
- 🇺🇦 **Ukrainian** — Primary, used for EXIF description
- 🇬🇧 **English** — For international SEO
- 🇷🇺 **Russian** — For CIS market reach

## 📄 License

MIT License — see LICENSE file for details.

## 🤝 Contributing

Contributions welcome! Please read the project plan in `docs/PROJECT_PLAN.md` first.

---

Made with ❤️ for [WoodWay Expert](https://wood-way.expert)

