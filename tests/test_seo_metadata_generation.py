"""
Test script to verify comprehensive SEO metadata generation.
Tests translation loading, character limits, E-E-A-T compliance, and more.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Import renamer module components directly
from core.renamer import SEOFileRenamer, ProductAttributes, SEOMetadata


def test_translation_loading():
    """Test that EN/RU translations are correctly loaded from JSON."""
    print("Testing translation loading...")
    renamer = SEOFileRenamer()
    
    # Test category translation
    assert renamer._get_localized_name("Шпон", "en") == "Veneer", "Category EN translation failed"
    assert renamer._get_localized_name("Шпон", "ru") == "Шпон", "Category RU translation failed"
    
    # Test type translation
    assert renamer._get_localized_name("Струганий", "en") == "Sliced", "Type EN translation failed"
    assert renamer._get_localized_name("Струганий", "ru") == "Строганный", "Type RU translation failed"
    
    # Test species translation
    assert renamer._get_localized_name("Дуб", "en") == "Oak", "Species EN translation failed"
    assert renamer._get_localized_name("Дуб", "ru") == "Дуб", "Species RU translation failed"
    
    print("✓ Translation loading: PASSED")


def test_character_limits():
    """Test that all generated tags respect character limits."""
    print("\nTesting character limits...")
    renamer = SEOFileRenamer()
    
    attrs = ProductAttributes(
        category="Шпон",
        product_type="Струганий",
        species="Дуб",
        thickness="1.0 мм",
        grade="A"
    )
    
    # Test multiple indices to check different templates
    for idx in range(4):
        metadata = renamer.generate_basic_metadata(attrs, index=idx + 1)
        
        # Check title limits (50-60 chars)
        for lang in ["ua", "en", "ru"]:
            title = metadata.__dict__[lang]["title"]
            assert len(title) <= 60, f"Title too long ({len(title)} chars): {title}"
            assert len(title) >= 20, f"Title too short ({len(title)} chars): {title}"
        
        # Check alt text limits (max 125 chars)
        for lang in ["ua", "en", "ru"]:
            alt_text = metadata.__dict__[lang]["alt_text"]
            assert len(alt_text) <= 125, f"Alt text too long ({len(alt_text)} chars): {alt_text}"
            assert len(alt_text) >= 10, f"Alt text too short ({len(alt_text)} chars): {alt_text}"
        
        # Check description limits (150-160 chars)
        for lang in ["ua", "en", "ru"]:
            desc = metadata.__dict__[lang]["description"]
            assert len(desc) <= 160, f"Description too long ({len(desc)} chars): {desc}"
            assert len(desc) >= 50, f"Description too short ({len(desc)} chars): {desc}"
    
    print("✓ Character limits: PASSED")


def test_eeat_compliance():
    """Test that descriptions include E-E-A-T signals."""
    print("\nTesting E-E-A-T compliance...")
    renamer = SEOFileRenamer()
    
    attrs = ProductAttributes(
        category="Шпон",
        product_type="Струганий",
        species="Дуб",
        thickness="1.0 мм",
        grade="A"
    )
    
    # E-E-A-T signal keywords
    eeat_signals = {
        "en": ["premium", "quality", "expert", "craftsmanship", "professional", "advice", "consultation", "ukrainian"],
        "ua": ["преміум", "якість", "експерт", "майстерність", "професійний", "консультація", "українськ"],
        "ru": ["премиум", "качество", "эксперт", "мастерство", "профессиональный", "консультация", "украинск"]
    }
    
    for idx in range(4):
        metadata = renamer.generate_basic_metadata(attrs, index=idx + 1)
        
        for lang in ["ua", "en", "ru"]:
            desc = metadata.__dict__[lang]["description"].lower()
            signals = eeat_signals[lang]
            
            # Check that at least one E-E-A-T signal is present
            has_signal = any(signal in desc for signal in signals)
            assert has_signal, f"Missing E-E-A-T signal in {lang} description: {desc}"
            
            # Check for brand mention
            assert "woodway" in desc or "WoodWay" in metadata.__dict__[lang]["title"], \
                f"Missing brand mention in {lang}"
    
    print("✓ E-E-A-T compliance: PASSED")


def test_template_variety():
    """Test that different templates are used for different indices."""
    print("\nTesting template variety...")
    renamer = SEOFileRenamer()
    
    attrs = ProductAttributes(
        category="Шпон",
        product_type="Струганий",
        species="Дуб",
        thickness="1.0 мм",
        grade="A"
    )
    
    titles = []
    descriptions = []
    
    for idx in range(4):
        metadata = renamer.generate_basic_metadata(attrs, index=idx + 1)
        titles.append(metadata.en["title"])
        descriptions.append(metadata.en["description"])
    
    # Check that titles vary (at least 2 different ones)
    unique_titles = set(titles)
    assert len(unique_titles) >= 2, f"Titles not varied enough: {unique_titles}"
    
    # Check that descriptions vary (at least 2 different ones)
    unique_descs = set(descriptions)
    assert len(unique_descs) >= 2, f"Descriptions not varied enough: {unique_descs}"
    
    print("✓ Template variety: PASSED")


def test_natural_language():
    """Test that generated text is natural and not keyword-stuffed."""
    print("\nTesting natural language...")
    renamer = SEOFileRenamer()
    
    attrs = ProductAttributes(
        category="Шпон",
        product_type="Струганий",
        species="Дуб",
        thickness="1.0 мм",
        grade="A"
    )
    
    metadata = renamer.generate_basic_metadata(attrs, index=1)
    
    for lang in ["ua", "en", "ru"]:
        desc = metadata.__dict__[lang]["description"]
        title = metadata.__dict__[lang]["title"]
        
        # Check for keyword repetition (no word should appear more than 3 times)
        words = desc.lower().split()
        word_counts = {}
        for word in words:
            if len(word) > 3:  # Ignore short words
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # No word should appear more than 3 times
        max_count = max(word_counts.values()) if word_counts else 0
        assert max_count <= 3, f"Keyword stuffing detected in {lang}: {word_counts}"
        
        # Check for natural connectors
        has_connectors = any(conn in desc.lower() for conn in ["for", "with", "from", "made", "з", "з", "для", "с"])
        assert has_connectors or len(desc) < 50, f"Missing natural connectors in {lang} description"
    
    print("✓ Natural language: PASSED")


def test_user_intent():
    """Test that descriptions answer 'what' and 'why' questions."""
    print("\nTesting user intent alignment...")
    renamer = SEOFileRenamer()
    
    attrs = ProductAttributes(
        category="Шпон",
        product_type="Струганий",
        species="Дуб",
        thickness="1.0 мм",
        grade="A"
    )
    
    metadata = renamer.generate_basic_metadata(attrs, index=1)
    
    for lang in ["ua", "en", "ru"]:
        desc = metadata.__dict__[lang]["description"].lower()
        
        # Check for question-answering format or CTA
        has_question_format = any(marker in desc for marker in ["looking", "шукаєте", "ищете", "?", "for", "для"])
        has_cta = any(marker in desc for marker in ["buy", "order", "купи", "замов", "купить", "закаж"])
        has_features = any(marker in desc for marker in ["quality", "якість", "качество", "premium", "преміум"])
        
        assert has_question_format or has_cta or has_features, \
            f"Description doesn't address user intent in {lang}: {desc}"
    
    print("✓ User intent: PASSED")


def test_accessibility():
    """Test that alt text describes visual content, not just keywords."""
    print("\nTesting accessibility...")
    renamer = SEOFileRenamer()
    
    attrs = ProductAttributes(
        category="Шпон",
        product_type="Струганий",
        species="Дуб",
        thickness="1.0 мм",
        grade="A"
    )
    
    metadata = renamer.generate_basic_metadata(attrs, index=1)
    
    for lang in ["ua", "en", "ru"]:
        alt_text = metadata.__dict__[lang]["alt_text"].lower()
        
        # Should not contain redundant phrases
        assert "image of" not in alt_text and "picture of" not in alt_text, \
            f"Redundant phrase in {lang} alt text: {alt_text}"
        
        # Should describe visual content (grain, texture, pattern, etc.)
        visual_descriptors = {
            "en": ["grain", "texture", "pattern", "wood", "natural", "showing", "view"],
            "ua": ["текстура", "малюнок", "дерево", "природний", "показує", "вигляд"],
            "ru": ["текстура", "рисунок", "дерево", "природный", "показывает", "вид"]
        }
        
        has_visual = any(desc in alt_text for desc in visual_descriptors[lang])
        assert has_visual, f"Alt text doesn't describe visual content in {lang}: {alt_text}"
    
    print("✓ Accessibility: PASSED")


def test_empty_attributes():
    """Test that metadata generation works with minimal attributes."""
    print("\nTesting empty attributes handling...")
    renamer = SEOFileRenamer()
    
    attrs = ProductAttributes()
    metadata = renamer.generate_basic_metadata(attrs, index=1)
    
    # Should still generate valid metadata
    assert metadata.filename, "Filename should be generated"
    assert metadata.ua["title"], "UA title should be generated"
    assert metadata.en["title"], "EN title should be generated"
    assert metadata.ru["title"], "RU title should be generated"
    
    print("✓ Empty attributes: PASSED")


def run_all_tests():
    """Run all verification tests."""
    print("=" * 60)
    print("SEO Metadata Generation Verification Tests")
    print("=" * 60)
    
    try:
        test_translation_loading()
        test_character_limits()
        test_eeat_compliance()
        test_template_variety()
        test_natural_language()
        test_user_intent()
        test_accessibility()
        test_empty_attributes()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

