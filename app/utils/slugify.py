import re
from typing import Optional


def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly slug.
    
    Examples:
        "My Company Name" -> "my-company-name"
        "Hello, World!" -> "hello-world"
        "Multiple   Spaces" -> "multiple-spaces"
    """
    if not text:
        return ""
    
    # Convert to lowercase and replace spaces and special chars with hyphens
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
    slug = re.sub(r'[\s-]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Ensure slug is not empty
    if not slug:
        slug = "unnamed"
    
    return slug


def generate_unique_slug(base_text: str, existing_slugs: list) -> str:
    """
    Generate a unique slug by appending a number if the slug already exists.
    
    Args:
        base_text: The base text to slugify
        existing_slugs: List of existing slugs to check against
    
    Returns:
        A unique slug
    """
    base_slug = slugify(base_text)
    
    if base_slug not in existing_slugs:
        return base_slug
    
    # Try appending numbers until we find a unique one
    counter = 1
    while f"{base_slug}-{counter}" in existing_slugs:
        counter += 1
    
    return f"{base_slug}-{counter}"