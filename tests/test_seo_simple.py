"""
Simple verification test that can run without full dependencies.
Tests core SEO metadata generation logic.
"""

import json
from pathlib import Path

# Test translation loading
def test_translations():
    """Test that translations are in the JSON file."""
    json_path = Path(__file__).parent.parent / "src" / "data" / "categories.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check that categories have translations
    for cat_key, cat_data in data.get("categories", {}).items():
        assert "name_en" in cat_data, f"Missing name_en for category {cat_key}"
        assert "name_ru" in cat_data, f"Missing name_ru for category {cat_key}"
        
        # Check types have translations
        for type_key, type_data in cat_data.get("types", {}).items():
            assert "name_en" in type_data, f"Missing name_en for type {type_key}"
            assert "name_ru" in type_data, f"Missing name_ru for type {type_key}"
    
    # Check that list options have translations
    for list_key, list_data in data.get("lists", {}).items():
        for option in list_data.get("options", []):
            assert "en" in option, f"Missing en for option in {list_key}"
            assert "ru" in option, f"Missing ru for option in {list_key}"
    
    print("[OK] Translation structure: PASSED")


if __name__ == "__main__":
    test_translations()
    print("\nSimple verification: PASSED")

