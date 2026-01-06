"""
Tests for metadata handler module.
"""

import unittest
import tempfile
import sys
from pathlib import Path
from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.metadata import MetadataHandler


class TestMetadataHandler(unittest.TestCase):
    """Tests for MetadataHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test JPEG image (JPEG supports EXIF)
        self.test_image_path = Path(self.temp_dir) / "test_image.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(self.test_image_path, 'JPEG')
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_read_empty_metadata(self):
        """Test reading metadata from image without EXIF."""
        metadata = MetadataHandler.read_metadata(self.test_image_path)
        
        self.assertIsInstance(metadata, dict)
    
    def test_write_description(self):
        """Test writing description metadata."""
        output_path = Path(self.temp_dir) / "with_meta.jpg"
        
        MetadataHandler.write_metadata(
            self.test_image_path,
            output_path,
            description="Test description"
        )
        
        self.assertTrue(output_path.exists())
    
    def test_write_title(self):
        """Test writing title metadata."""
        output_path = Path(self.temp_dir) / "with_title.jpg"
        
        MetadataHandler.write_metadata(
            self.test_image_path,
            output_path,
            title="Test Title"
        )
        
        self.assertTrue(output_path.exists())
    
    def test_write_multiple_fields(self):
        """Test writing multiple metadata fields."""
        output_path = Path(self.temp_dir) / "multi_meta.jpg"
        
        MetadataHandler.write_metadata(
            self.test_image_path,
            output_path,
            description="Description",
            title="Title",
            keywords="keyword1, keyword2",
            comment="A comment"
        )
        
        self.assertTrue(output_path.exists())
    
    def test_write_custom_data(self):
        """Test writing custom JSON data."""
        output_path = Path(self.temp_dir) / "custom_data.jpg"
        
        custom = {
            "product_id": "12345",
            "category": "veneer"
        }
        
        MetadataHandler.write_metadata(
            self.test_image_path,
            output_path,
            custom_data=custom
        )
        
        self.assertTrue(output_path.exists())
    
    def test_write_seo_metadata(self):
        """Test writing multi-language SEO metadata."""
        output_path = Path(self.temp_dir) / "seo_meta.jpg"
        
        result = MetadataHandler.write_seo_metadata(
            self.test_image_path,
            output_path,
            filename="shpon-dub.webp",
            ua={"alt_text": "Шпон дуб", "title": "Шпон", "description": "Опис"},
            en={"alt_text": "Oak veneer", "title": "Veneer", "description": "Desc"},
            ru={"alt_text": "Шпон дуб", "title": "Шпон", "description": "Описание"},
        )
        
        self.assertTrue(result.exists())
        self.assertEqual(result, output_path)
    
    def test_overwrite_original(self):
        """Test overwriting original file when no output path given."""
        # Create a copy to not affect other tests
        copy_path = Path(self.temp_dir) / "copy.jpg"
        img = Image.new('RGB', (50, 50), color='blue')
        img.save(copy_path, 'JPEG')
        
        result = MetadataHandler.write_metadata(
            copy_path,
            description="Overwritten"
        )
        
        self.assertEqual(result, copy_path)
    
    def test_unicode_metadata(self):
        """Test writing Unicode (Ukrainian) metadata."""
        output_path = Path(self.temp_dir) / "unicode_meta.jpg"
        
        MetadataHandler.write_metadata(
            self.test_image_path,
            output_path,
            description="Шпон дуба натуральний",
            title="Деревина преміум"
        )
        
        self.assertTrue(output_path.exists())
    
    def test_webp_metadata(self):
        """Test metadata handling for WebP images."""
        # Create WebP test image
        webp_path = Path(self.temp_dir) / "test.webp"
        img = Image.new('RGB', (100, 100), color='green')
        img.save(webp_path, 'WEBP')
        
        output_path = Path(self.temp_dir) / "webp_meta.webp"
        
        result = MetadataHandler.write_metadata(
            webp_path,
            output_path,
            description="WebP description"
        )
        
        self.assertTrue(result.exists())
    
    def test_png_no_crash(self):
        """Test that PNG handling doesn't crash (limited EXIF support)."""
        png_path = Path(self.temp_dir) / "test.png"
        img = Image.new('RGB', (100, 100), color='yellow')
        img.save(png_path, 'PNG')
        
        output_path = Path(self.temp_dir) / "png_meta.png"
        
        # Should not raise, even if EXIF isn't fully supported
        result = MetadataHandler.write_metadata(
            png_path,
            output_path,
            description="PNG description"
        )
        
        self.assertTrue(result.exists())


if __name__ == "__main__":
    unittest.main()

