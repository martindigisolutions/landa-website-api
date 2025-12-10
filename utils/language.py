"""
Language utilities for handling Accept-Language header
"""
from typing import Optional


SUPPORTED_LANGUAGES = ["es", "en"]
DEFAULT_LANGUAGE = "es"


def get_language_from_header(accept_language: Optional[str]) -> str:
    """
    Extract language code from Accept-Language header.
    
    Examples:
        "en" -> "en"
        "en-US" -> "en"
        "es-ES,es;q=0.9,en;q=0.8" -> "es"
        None -> "es" (default)
    """
    if not accept_language:
        return DEFAULT_LANGUAGE
    
    # Parse the Accept-Language header
    # Format can be: "en", "en-US", "es-ES,es;q=0.9,en;q=0.8"
    languages = []
    
    for part in accept_language.split(","):
        part = part.strip()
        if ";q=" in part:
            lang, q = part.split(";q=")
            try:
                quality = float(q)
            except ValueError:
                quality = 1.0
        else:
            lang = part
            quality = 1.0
        
        # Extract base language code (en-US -> en)
        lang_code = lang.split("-")[0].lower()
        languages.append((lang_code, quality))
    
    # Sort by quality (highest first)
    languages.sort(key=lambda x: x[1], reverse=True)
    
    # Find first supported language
    for lang_code, _ in languages:
        if lang_code in SUPPORTED_LANGUAGES:
            return lang_code
    
    return DEFAULT_LANGUAGE


def localize_field(value_es: Optional[str], value_en: Optional[str], lang: str) -> Optional[str]:
    """
    Return the correct field value based on language.
    Falls back to Spanish if English is not available.
    
    Args:
        value_es: Spanish value (default)
        value_en: English value
        lang: Language code ("es" or "en")
    
    Returns:
        The appropriate value with fallback to Spanish
    """
    if lang == "en" and value_en:
        return value_en
    return value_es


def localize_gallery(gallery: Optional[list], lang: str) -> list:
    """
    Filter gallery images based on language.
    
    Rules:
        - URL containing _es or _es_ → Spanish only
        - URL containing _en or _en_ → English only
        - No language marker → Both languages
    
    Examples:
        "image1.webp" → Both
        "promo_es.webp" → Spanish only
        "promo_en.webp" → English only
        "gallery_011_es_12345.webp" → Spanish only
        "gallery_011_en_12345.webp" → English only
    
    Args:
        gallery: List of image URLs
        lang: Language code ("es" or "en")
    
    Returns:
        Filtered list of image URLs for the specified language
    """
    if not gallery:
        return []
    
    result = []
    other_lang = "en" if lang == "es" else "es"
    
    for url in gallery:
        if not url:
            continue
        
        url_lower = url.lower()
        
        # Check if it's for the OTHER language (exclude it)
        # Patterns: _en. or _en_ or ends with _en
        is_other_lang = (
            f"_{other_lang}." in url_lower or 
            f"_{other_lang}_" in url_lower or 
            url_lower.endswith(f"_{other_lang}")
        )
        
        if is_other_lang:
            continue
        
        # Include if it's for current language OR neutral (no language suffix)
        result.append(url)
    
    return result

