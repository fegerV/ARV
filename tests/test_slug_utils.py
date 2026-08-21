from app.utils import slug_utils as mod


def test_transliterate_preserves_latin_digits_and_transliterates_known_chars():
    assert mod.transliterate("Vertex 123") == "vertex 123"
    assert mod.transliterate("АБВ abc 123") == "abv abc 123"


def test_generate_slug_handles_cyrillic_spacing_symbols_and_empty():
    assert mod.generate_slug("") == ""
    assert mod.generate_slug("Vertex AR") == "vertex-ar"
    assert mod.generate_slug("Компания 123") == "kompaniya-123"
    assert mod.generate_slug("  Hello___World!!  ") == "hello-world"
    assert mod.generate_slug("___###___") == ""
