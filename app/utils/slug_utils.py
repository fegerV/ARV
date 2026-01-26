import re
from typing import Optional


# Russian to Latin transliteration table (GOST 7.79-2000 System B)
TRANSLIT_TABLE = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def transliterate(text: str) -> str:
    """
    Transliterate Russian/Cyrillic text to Latin.
    
    Args:
        text (str): Text to transliterate
        
    Returns:
        str: Transliterated text (lowercase)
    
    Examples:
        >>> transliterate("Портреты")
        'portrety'
        >>> transliterate("Компания")
        'kompaniya'
    """
    result = []
    text_lower = text.lower()
    for char in text_lower:
        if char in TRANSLIT_TABLE:
            result.append(TRANSLIT_TABLE[char])
        else:
            # Keep Latin characters and numbers as-is
            result.append(char)
    return ''.join(result)


def generate_slug(text: str) -> str:
    """
    Generate a URL-friendly slug from text with transliteration support.
    
    Transliterates Cyrillic characters to Latin, then creates a filesystem-safe slug.
    
    Args:
        text (str): Text to convert to slug (can contain Cyrillic)
        
    Returns:
        str: Generated slug (Latin only, filesystem-safe)
    
    Examples:
        >>> generate_slug("Портреты")
        'portrety'
        >>> generate_slug("Vertex AR")
        'vertex-ar'
        >>> generate_slug("Компания 123")
        'kompaniya-123'
    """
    if not text:
        return ""
    
    # First transliterate Cyrillic to Latin
    slug = transliterate(text)
    
    # Convert to lowercase
    slug = slug.lower()
    
    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Remove leading and trailing hyphens
    slug = slug.strip('-')
    
    # Ensure we don't have consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    return slug


def generate_unique_slug(text: str, existing_slugs: set) -> str:
    """
    Generate a unique slug, adding a number suffix if needed.
    
    Args:
        text (str): Text to convert to slug
        existing_slugs (set): Set of existing slugs to avoid duplicates
        
    Returns:
        str: Unique slug
    """
    base_slug = generate_slug(text)
    if not base_slug:
        base_slug = "company"
    
    # If slug is unique, return it
    if base_slug not in existing_slugs:
        return base_slug
    
    # Otherwise, add a number suffix
    counter = 1
    while f"{base_slug}-{counter}" in existing_slugs:
        counter += 1
    
    return f"{base_slug}-{counter}"