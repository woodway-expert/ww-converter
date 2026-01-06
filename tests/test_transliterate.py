"""
Tests for transliteration module.
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.transliterate import transliterate_ua, to_seo_slug


class TestTransliterate(unittest.TestCase):
    """Tests for Ukrainian transliteration."""
    
    def test_basic_transliteration(self):
        """Test basic Ukrainian to Latin conversion."""
        self.assertEqual(transliterate_ua("Привіт"), "Pryvit")
        self.assertEqual(transliterate_ua("шпон"), "shpon")
        self.assertEqual(transliterate_ua("дуб"), "dub")
    
    def test_special_characters(self):
        """Test special Ukrainian characters."""
        self.assertEqual(transliterate_ua("є"), "ye")
        self.assertEqual(transliterate_ua("ї"), "yi")
        self.assertEqual(transliterate_ua("ґ"), "g")
        self.assertEqual(transliterate_ua("щ"), "shch")
    
    def test_soft_sign_removed(self):
        """Test that soft sign is removed."""
        self.assertEqual(transliterate_ua("мʼякий"), "myakyy")  # й→y consistently
        self.assertEqual(transliterate_ua("сіль"), "sil")
    
    def test_mixed_text(self):
        """Test mixed Ukrainian and Latin text."""
        self.assertEqual(transliterate_ua("Wood-way Експерт"), "Wood-way Ekspert")
    
    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        self.assertEqual(transliterate_ua("шпон 18мм"), "shpon 18mm")


class TestSeoSlug(unittest.TestCase):
    """Tests for SEO slug generation."""
    
    def test_basic_slug(self):
        """Test basic slug generation."""
        self.assertEqual(to_seo_slug("Шпон дуб"), "shpon-dub")
        self.assertEqual(to_seo_slug("МДФ плита"), "mdf-plyta")
    
    def test_lowercase_conversion(self):
        """Test that output is lowercase."""
        result = to_seo_slug("ФАНЕРА БЕРЕЗА")
        self.assertEqual(result, result.lower())
    
    def test_space_to_hyphen(self):
        """Test that spaces become hyphens."""
        self.assertNotIn(" ", to_seo_slug("Шпон дуб натуральний"))
        self.assertIn("-", to_seo_slug("Шпон дуб натуральний"))
    
    def test_underscore_to_hyphen(self):
        """Test that underscores become hyphens."""
        self.assertNotIn("_", to_seo_slug("shpon_dub"))
        self.assertEqual(to_seo_slug("shpon_dub"), "shpon-dub")
    
    def test_no_double_hyphens(self):
        """Test that double hyphens are collapsed."""
        self.assertNotIn("--", to_seo_slug("Шпон  дуб"))
    
    def test_special_chars_removed(self):
        """Test that special characters are removed."""
        result = to_seo_slug("Шпон (дуб) #1")
        self.assertNotIn("(", result)
        self.assertNotIn(")", result)
        self.assertNotIn("#", result)
    
    def test_trim_hyphens(self):
        """Test that leading/trailing hyphens are removed."""
        result = to_seo_slug(" Шпон дуб ")
        self.assertFalse(result.startswith("-"))
        self.assertFalse(result.endswith("-"))
    
    def test_real_product_examples(self):
        """Test real product name examples."""
        self.assertEqual(
            to_seo_slug("Шпон дуб натуральний"),
            "shpon-dub-naturalnyy"  # й→y consistently
        )
        self.assertEqual(
            to_seo_slug("Фанера ФСФ березова 18мм"),
            "fanera-fsf-berezova-18mm"
        )
        self.assertEqual(
            to_seo_slug("МДФ плита шпонована"),
            "mdf-plyta-shponovana"
        )


if __name__ == "__main__":
    unittest.main()

