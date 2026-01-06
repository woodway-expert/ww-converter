"""
Tests for image converter module.
"""

import unittest
import tempfile
import sys
from pathlib import Path
from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.converter import ImageConverter


class TestImageConverter(unittest.TestCase):
    """Tests for ImageConverter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.converter = ImageConverter(output_format="webp", quality=85)
        
        # Create a test image
        self.test_image_path = Path(self.temp_dir) / "test_image.png"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(self.test_image_path)
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_converter_initialization(self):
        """Test converter initializes with correct settings."""
        converter = ImageConverter(
            output_format="jpeg",
            quality=90,
            max_resolution=(800, 600)
        )
        self.assertEqual(converter.output_format, "jpeg")
        self.assertEqual(converter.quality, 90)
        self.assertEqual(converter.max_resolution, (800, 600))
    
    def test_quality_clamping(self):
        """Test that quality is clamped to 1-100."""
        converter = ImageConverter(quality=150)
        self.assertEqual(converter.quality, 100)
        
        converter = ImageConverter(quality=-10)
        self.assertEqual(converter.quality, 1)
    
    def test_convert_to_webp(self):
        """Test converting image to WebP."""
        output_path = self.converter.convert_image(self.test_image_path)
        
        self.assertTrue(output_path.exists())
        self.assertEqual(output_path.suffix, ".webp")
        
        # Verify it's a valid image
        with Image.open(output_path) as img:
            self.assertEqual(img.format, "WEBP")
    
    def test_convert_to_jpeg(self):
        """Test converting image to JPEG."""
        converter = ImageConverter(output_format="jpeg")
        output_path = converter.convert_image(self.test_image_path)
        
        self.assertTrue(output_path.exists())
        self.assertEqual(output_path.suffix, ".jpeg")
        
        with Image.open(output_path) as img:
            self.assertEqual(img.format, "JPEG")
    
    def test_convert_to_png(self):
        """Test converting image to PNG."""
        converter = ImageConverter(output_format="png")
        output_path = converter.convert_image(self.test_image_path)
        
        self.assertTrue(output_path.exists())
        self.assertEqual(output_path.suffix, ".png")
    
    def test_custom_output_path(self):
        """Test converting with custom output path."""
        custom_path = Path(self.temp_dir) / "custom_name.webp"
        output_path = self.converter.convert_image(
            self.test_image_path,
            output_path=custom_path
        )
        
        self.assertEqual(output_path, custom_path)
        self.assertTrue(custom_path.exists())
    
    def test_resize_image(self):
        """Test image resizing."""
        # Create a larger test image
        large_image_path = Path(self.temp_dir) / "large_image.png"
        img = Image.new('RGB', (2000, 1500), color='blue')
        img.save(large_image_path)
        
        converter = ImageConverter(
            output_format="webp",
            max_resolution=(800, 600)
        )
        output_path = converter.convert_image(large_image_path)
        
        with Image.open(output_path) as img:
            self.assertLessEqual(img.width, 800)
            self.assertLessEqual(img.height, 600)
    
    def test_preserve_aspect_ratio(self):
        """Test that aspect ratio is preserved during resize."""
        # Create a 4:3 aspect ratio image
        wide_image_path = Path(self.temp_dir) / "wide_image.png"
        img = Image.new('RGB', (1600, 1200), color='green')
        img.save(wide_image_path)
        
        converter = ImageConverter(
            output_format="webp",
            max_resolution=(800, 800),
            preserve_aspect_ratio=True
        )
        output_path = converter.convert_image(wide_image_path)
        
        with Image.open(output_path) as img:
            # Original ratio is 4:3 (1.333)
            ratio = img.width / img.height
            self.assertAlmostEqual(ratio, 4/3, places=1)
    
    def test_get_thumbnail(self):
        """Test thumbnail generation."""
        thumb = self.converter.get_thumbnail(self.test_image_path, size=(50, 50))
        
        self.assertIsInstance(thumb, Image.Image)
        self.assertLessEqual(thumb.width, 50)
        self.assertLessEqual(thumb.height, 50)
    
    def test_convert_to_bytes(self):
        """Test converting to bytes."""
        data = self.converter.convert_to_bytes(self.test_image_path)
        
        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)
    
    def test_get_image_info(self):
        """Test getting image information."""
        info = ImageConverter.get_image_info(self.test_image_path)
        
        self.assertEqual(info['filename'], 'test_image.png')
        self.assertEqual(info['format'], 'PNG')
        self.assertEqual(info['width'], 100)
        self.assertEqual(info['height'], 100)
        self.assertIn('size_bytes', info)
    
    def test_unsupported_format_raises(self):
        """Test that unsupported input format raises error."""
        fake_file = Path(self.temp_dir) / "test.xyz"
        fake_file.write_text("not an image")
        
        with self.assertRaises(ValueError):
            self.converter.convert_image(fake_file)
    
    def test_rgba_to_jpeg_conversion(self):
        """Test that RGBA images are properly converted to JPEG (no alpha)."""
        rgba_path = Path(self.temp_dir) / "rgba_image.png"
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        img.save(rgba_path)
        
        converter = ImageConverter(output_format="jpeg")
        output_path = converter.convert_image(rgba_path)
        
        with Image.open(output_path) as img:
            self.assertEqual(img.mode, "RGB")


if __name__ == "__main__":
    unittest.main()

