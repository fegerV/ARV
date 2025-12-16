import re
from typing import Optional


def generate_slug(text: str) -> str:
    """
    Generate a URL-friendly slug from text.
    
    Args:
        text (str): Text to convert to slug
        
    Returns:
        str: Generated slug
    """
    if not text:
        return ""
    
    # Convert to lowercase
    slug = text.lower()
    
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