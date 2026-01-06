"""
Tests for WordPress exporter module.
"""

import unittest
import tempfile
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.exporter import WordPressExporter, ExportSettings


class MockMetadata:
    """Mock SEOMetadata for testing."""
    def __init__(self, filename="test.webp"):
        self.filename = filename
        self.ua = {"alt_text": "Тест UA", "title": "Заголовок UA", "description": "Опис UA"}
        self.en = {"alt_text": "Test EN", "title": "Title EN", "description": "Desc EN"}
        self.ru = {"alt_text": "Тест RU", "title": "Заголовок RU", "description": "Описание RU"}


class MockImageItem:
    """Mock ImageItem for testing."""
    def __init__(self, index=1, filename="test.webp"):
        self.index = index
        self.path = Path(f"/fake/path/original_{index}.jpg")
        self.output_path = Path(f"/fake/output/{filename}")
        self.metadata = MockMetadata(filename)


class TestWordPressExporter(unittest.TestCase):
    """Tests for WordPressExporter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.output_folder = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_export_single_image(self):
        """Test exporting single image metadata."""
        images = [MockImageItem(1, "test-image-01.webp")]
        settings = ExportSettings(category="Шпон", product_type="Струганий")
        
        result_path = WordPressExporter.export_to_json(
            images=images,
            output_folder=self.output_folder,
            settings=settings
        )
        
        self.assertTrue(result_path.exists())
        self.assertEqual(result_path.name, "export.json")
        
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(data["total_images"], 1)
        self.assertEqual(data["settings"]["category"], "Шпон")
        self.assertEqual(len(data["images"]), 1)
    
    def test_export_multiple_images(self):
        """Test exporting multiple images."""
        images = [
            MockImageItem(1, "image-01.webp"),
            MockImageItem(2, "image-02.webp"),
            MockImageItem(3, "image-03.webp"),
        ]
        settings = ExportSettings()
        
        result_path = WordPressExporter.export_to_json(
            images=images,
            output_folder=self.output_folder,
            settings=settings
        )
        
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(data["total_images"], 3)
        self.assertEqual(len(data["images"]), 3)
    
    def test_export_contains_wp_attachment_fields(self):
        """Test that export contains WordPress attachment fields."""
        images = [MockImageItem(1)]
        settings = ExportSettings()
        
        result_path = WordPressExporter.export_to_json(
            images=images,
            output_folder=self.output_folder,
            settings=settings
        )
        
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        wp_fields = data["images"][0]["wp_attachment"]
        
        self.assertIn("_wp_attachment_image_alt", wp_fields)
        self.assertIn("post_title", wp_fields)
        self.assertIn("post_excerpt", wp_fields)
        self.assertIn("_alt_text_ua", wp_fields)
        self.assertIn("_alt_text_en", wp_fields)
        self.assertIn("_alt_text_ru", wp_fields)
    
    def test_export_multilingual_metadata(self):
        """Test that all three languages are exported."""
        images = [MockImageItem(1)]
        settings = ExportSettings()
        
        result_path = WordPressExporter.export_to_json(
            images=images,
            output_folder=self.output_folder,
            settings=settings
        )
        
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data["images"][0]["metadata"]
        
        self.assertIn("ua", metadata)
        self.assertIn("en", metadata)
        self.assertIn("ru", metadata)
        
        self.assertEqual(metadata["ua"]["alt_text"], "Тест UA")
        self.assertEqual(metadata["en"]["alt_text"], "Test EN")
        self.assertEqual(metadata["ru"]["alt_text"], "Тест RU")
    
    def test_export_custom_filename(self):
        """Test exporting with custom filename."""
        images = [MockImageItem(1)]
        settings = ExportSettings()
        
        result_path = WordPressExporter.export_to_json(
            images=images,
            output_folder=self.output_folder,
            settings=settings,
            filename="custom_export.json"
        )
        
        self.assertEqual(result_path.name, "custom_export.json")
        self.assertTrue(result_path.exists())
    
    def test_export_settings_preserved(self):
        """Test that export settings are saved in JSON."""
        images = [MockImageItem(1)]
        settings = ExportSettings(
            category="Дошка",
            product_type="Обрізна",
            species="Акація",
            thickness="35 мм",
            grade="Екстра",
            output_format="webp",
            quality=90
        )
        
        result_path = WordPressExporter.export_to_json(
            images=images,
            output_folder=self.output_folder,
            settings=settings
        )
        
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(data["settings"]["category"], "Дошка")
        self.assertEqual(data["settings"]["species"], "Акація")
        self.assertEqual(data["settings"]["quality"], 90)
    
    def test_export_csv(self):
        """Test CSV export functionality."""
        images = [
            MockImageItem(1, "image-01.webp"),
            MockImageItem(2, "image-02.webp"),
        ]
        
        result_path = WordPressExporter.export_csv(
            images=images,
            output_folder=self.output_folder
        )
        
        self.assertTrue(result_path.exists())
        self.assertEqual(result_path.name, "export.csv")
        
        # Read and verify CSV
        with open(result_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        # Header + 2 data rows
        self.assertEqual(len(lines), 3)


class TestExportSettings(unittest.TestCase):
    """Tests for ExportSettings dataclass."""
    
    def test_default_values(self):
        """Test default settings values."""
        settings = ExportSettings()
        
        self.assertEqual(settings.category, "")
        self.assertEqual(settings.output_format, "webp")
        self.assertEqual(settings.quality, 85)
    
    def test_custom_values(self):
        """Test custom settings values."""
        settings = ExportSettings(
            category="Фанера",
            quality=75
        )
        
        self.assertEqual(settings.category, "Фанера")
        self.assertEqual(settings.quality, 75)


if __name__ == "__main__":
    unittest.main()

