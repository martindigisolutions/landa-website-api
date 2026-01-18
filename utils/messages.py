"""
User-facing messages in multiple languages
"""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "es": {
        "insufficient_stock": "Los siguientes productos ya no están disponibles: {items}. Por favor, regresa al carrito para ajustar las cantidades.",
        "lock_expired": "Tu reserva expiró. Por favor, regresa e intenta de nuevo.",
        "lock_already_used": "Esta reserva ya fue utilizada para crear una orden. Por favor, inicia una nueva compra.",
        "lock_not_found": "No se encontró tu reserva. Por favor, regresa al carrito e intenta de nuevo.",
        "lock_cancelled": "Tu reserva fue cancelada. Por favor, regresa al carrito e intenta de nuevo.",
        "generic_error": "Ocurrió un error al procesar tu solicitud. Por favor, intenta de nuevo."
    },
    "en": {
        "insufficient_stock": "The following products are no longer available: {items}. Please return to cart to adjust quantities.",
        "lock_expired": "Your reservation expired. Please go back and try again.",
        "lock_already_used": "This reservation was already used to create an order. Please start a new purchase.",
        "lock_not_found": "Your reservation was not found. Please return to cart and try again.",
        "lock_cancelled": "Your reservation was cancelled. Please return to cart and try again.",
        "generic_error": "An error occurred while processing your request. Please try again."
    }
}


def get_message(key: str, lang: str = "es", **kwargs) -> str:
    """
    Get a localized message by key.
    
    Args:
        key: Message key (e.g., "insufficient_stock")
        lang: Language code ("es" or "en")
        **kwargs: Format arguments for the message (e.g., items="Product 1, Product 2")
    
    Returns:
        Localized message string
    """
    if lang not in MESSAGES:
        lang = "es"  # Fallback to Spanish
    
    messages = MESSAGES.get(lang, MESSAGES["es"])
    message = messages.get(key, messages.get("generic_error", "An error occurred."))
    
    # Format message with kwargs if provided
    try:
        return message.format(**kwargs)
    except (KeyError, ValueError):
        return message
