"""
Tests for SEO file renamer module.
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.renamer import SEOFileRenamer, ProductAttributes, SEOMetadata


class TestProductAttributes(unittest.TestCase):
    """Tests for ProductAttributes dataclass."""
    
    def test_default_values(self):
        """Test default empty values."""
        attrs = ProductAttributes()
        self.assertEqual(attrs.category, "")
        self.assertEqual(attrs.species, "")
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        attrs = ProductAttributes(
            category="Шпон",
            species="Дуб",
            thickness="0.6 мм"
        )
        d = attrs.to_dict()
        
        self.assertEqual(d["category"], "Шпон")
        self.assertEqual(d["species"], "Дуб")
        self.assertNotIn("finish", d)  # Empty values excluded


class TestSEOMetadata(unittest.TestCase):
    """Tests for SEOMetadata dataclass."""
    
    def test_default_values(self):
        """Test default structure."""
        meta = SEOMetadata()
        self.assertEqual(meta.filename, "")
        self.assertIn("alt_text", meta.ua)
        self.assertIn("title", meta.en)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        meta = SEOMetadata(
            filename="test.webp",
            ua={"alt_text": "Тест", "title": "Тест", "description": "Тест"}
        )
        d = meta.to_dict()
        
        self.assertEqual(d["filename"], "test.webp")
        self.assertEqual(d["ua"]["alt_text"], "Тест")
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "filename": "shpon-dub.webp",
            "ua": {"alt_text": "Шпон дуб", "title": "Шпон", "description": "Опис"},
            "en": {"alt_text": "Oak veneer", "title": "Veneer", "description": "Desc"},
            "ru": {"alt_text": "Шпон дуб", "title": "Шпон", "description": "Описание"},
        }
        meta = SEOMetadata.from_dict(data)
        
        self.assertEqual(meta.filename, "shpon-dub.webp")
        self.assertEqual(meta.ua["alt_text"], "Шпон дуб")
        self.assertEqual(meta.en["title"], "Veneer")


class TestSEOFileRenamer(unittest.TestCase):
    """Tests for SEOFileRenamer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.renamer = SEOFileRenamer()
    
    def test_generate_filename_basic(self):
        """Test basic filename generation."""
        attrs = ProductAttributes(
            product_type="Струганий",
            species="Дуб"
        )
        filename = self.renamer.generate_filename(attrs, extension="webp")
        
        self.assertTrue(filename.endswith(".webp"))
        self.assertIn("dub", filename.lower())
    
    def test_generate_filename_with_index(self):
        """Test filename generation with index."""
        attrs = ProductAttributes(product_type="Шпон", species="Дуб")
        filename = self.renamer.generate_filename(attrs, index=5, extension="webp")
        
        self.assertIn("05", filename)
    
    def test_generate_filename_all_attributes(self):
        """Test filename with all attributes."""
        attrs = ProductAttributes(
            product_type="Шпон",
            species="Дуб",
            finish="Натуральний",
            thickness="0.6mm",
            grade="A"
        )
        filename = self.renamer.generate_filename(attrs, extension="webp")
        
        # Should contain all parts
        self.assertIn("dub", filename.lower())
        self.assertIn("0.6mm", filename.lower())
    
    def test_generate_filename_fallback(self):
        """Test fallback when no attributes provided."""
        attrs = ProductAttributes()
        filename = self.renamer.generate_filename(attrs, index=1, extension="webp")
        
        self.assertTrue(filename.endswith(".webp"))
        # With index only, should at least contain the index number
        self.assertIn("01", filename)
    
    def test_generate_basic_metadata(self):
        """Test basic metadata generation."""
        attrs = ProductAttributes(
            category="Шпон",
            product_type="Струганий",
            species="Дуб"
        )
        meta = self.renamer.generate_basic_metadata(attrs, index=1, extension="webp")
        
        self.assertIsInstance(meta, SEOMetadata)
        self.assertTrue(meta.filename.endswith(".webp"))
        self.assertIn("01", meta.filename)
        
        # Check all languages have content
        self.assertTrue(len(meta.ua["alt_text"]) > 0)
        self.assertTrue(len(meta.en["alt_text"]) > 0)
        self.assertTrue(len(meta.ru["alt_text"]) > 0)
    
    def test_metadata_title_includes_brand(self):
        """Test that title includes brand name."""
        attrs = ProductAttributes(product_type="Шпон", species="Дуб")
        meta = self.renamer.generate_basic_metadata(attrs)
        
        self.assertIn("WoodWay Expert", meta.ua["title"])
        self.assertIn("WoodWay Expert", meta.en["title"])
    
    def test_metadata_description_length(self):
        """Test that description respects max length."""
        attrs = ProductAttributes(
            product_type="Шпон струганий натуральний преміум якості",
            species="Дуб європейський відбірний",
            finish="Натуральний матовий",
            thickness="0.6mm"
        )
        meta = self.renamer.generate_basic_metadata(attrs)
        
        self.assertLessEqual(len(meta.ua["description"]), 160)
        self.assertLessEqual(len(meta.en["description"]), 160)
    
    def test_get_category_options(self):
        """Test getting category options."""
        options = self.renamer.get_category_options()
        
        self.assertIsInstance(options, list)
        if options:  # If categories.json is loaded
            self.assertIn("key", options[0])
            self.assertIn("name_ua", options[0])
    
    def test_get_types_for_category(self):
        """Test getting types for a category."""
        types = self.renamer.get_types_for_category("veneer")
        
        self.assertIsInstance(types, list)
    
    def test_get_list_options(self):
        """Test getting list options."""
        species = self.renamer.get_list_options("species")
        
        self.assertIsInstance(species, list)
        if species:
            self.assertIn("ua", species[0])
            self.assertIn("slug", species[0])


class TestFilenameFormat(unittest.TestCase):
    """Tests for SEO filename format compliance."""
    
    def setUp(self):
        self.renamer = SEOFileRenamer()
    
    def test_no_spaces_in_filename(self):
        """Test that filename has no spaces."""
        attrs = ProductAttributes(product_type="Шпон дуб", species="Дуб натуральний")
        filename = self.renamer.generate_filename(attrs)
        
        self.assertNotIn(" ", filename)
    
    def test_no_underscores_in_filename(self):
        """Test that filename has no underscores."""
        attrs = ProductAttributes(product_type="Шпон_дуб", species="Дуб")
        filename = self.renamer.generate_filename(attrs)
        
        self.assertNotIn("_", filename)
    
    def test_lowercase_filename(self):
        """Test that filename is lowercase."""
        attrs = ProductAttributes(product_type="ШПОН", species="ДУБ")
        filename = self.renamer.generate_filename(attrs)
        
        # Extension can have dots, but letters should be lowercase
        name_part = filename.rsplit(".", 1)[0]
        self.assertEqual(name_part, name_part.lower())
    
    def test_hyphen_separated(self):
        """Test that words are separated by hyphens."""
        attrs = ProductAttributes(product_type="Шпон", species="Дуб", finish="Натуральний")
        filename = self.renamer.generate_filename(attrs)
        
        self.assertIn("-", filename)
    
    def test_latin_only(self):
        """Test that filename contains only Latin characters."""
        attrs = ProductAttributes(product_type="Шпон", species="Дуб")
        filename = self.renamer.generate_filename(attrs)
        
        # Remove extension for check
        name_part = filename.rsplit(".", 1)[0]
        for char in name_part:
            if char.isalpha():
                self.assertTrue(char.isascii(), f"Non-ASCII character found: {char}")


if __name__ == "__main__":
    unittest.main()

