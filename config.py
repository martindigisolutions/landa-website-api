import os
import json
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

env_file = os.getenv("ENV_FILE", ".env.dev")
load_dotenv(env_file)

# Support for JSON secret from AWS Secrets Manager (for production)
# If APP_SECRETS_JSON is set, parse it and extract individual values
# Otherwise, use individual environment variables (for local development)
APP_SECRETS_JSON = os.getenv("APP_SECRETS_JSON")
_secrets_dict = {}
if APP_SECRETS_JSON:
    try:
        # Log that we're trying to parse the secret (but don't log the actual value)
        logger.info(f"Found APP_SECRETS_JSON, attempting to parse (length: {len(APP_SECRETS_JSON)})")
        _secrets_dict = json.loads(APP_SECRETS_JSON)
        logger.info(f"Successfully parsed APP_SECRETS_JSON, found {len(_secrets_dict)} keys")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse APP_SECRETS_JSON as JSON: {e}")
        logger.error(f"APP_SECRETS_JSON value (first 100 chars): {APP_SECRETS_JSON[:100] if APP_SECRETS_JSON else 'None'}")
        _secrets_dict = {}
    except Exception as e:
        logger.error(f"Unexpected error parsing APP_SECRETS_JSON: {e}")
        _secrets_dict = {}
else:
    logger.info("APP_SECRETS_JSON not set, using individual environment variables")

def _get_secret(key: str, default: str = "") -> str:
    """Get secret from JSON or individual env var"""
    if key in _secrets_dict:
        return _secrets_dict[key]
    return os.getenv(key, default)

EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
FRONTEND_RESET_URL = os.getenv("FRONTEND_RESET_URL", "")

SECRET_KEY = _get_secret("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

PASSWORD_RESET_MAX_REQUESTS_PER_HOUR = int(os.getenv("PASSWORD_RESET_MAX_REQUESTS_PER_HOUR", "3"))

# Stripe Configuration
STRIPE_SECRET_KEY = _get_secret("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = _get_secret("STRIPE_WEBHOOK_SECRET", "")

# Admin App Configuration (OAuth2)
# If these are set, the super admin app will be auto-created on startup
ADMIN_CLIENT_ID = _get_secret("ADMIN_CLIENT_ID")
ADMIN_CLIENT_SECRET = _get_secret("ADMIN_CLIENT_SECRET")

# Single Access Token Configuration
WHOLESALE_FRONTEND_URL = os.getenv("WHOLESALE_FRONTEND_URL", "https://wholesale.landabeautysupply.com")
SINGLE_ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("SINGLE_ACCESS_TOKEN_EXPIRE_HOURS", "24"))

# =============================================================================
# STORE MODE CONFIGURATION
# =============================================================================
# Determines which store mode this instance runs as.
# Set via environment variable: STORE_MODE=wholesale or STORE_MODE=retail
# Default: wholesale (maintains backward compatibility)

STORE_MODE = os.getenv("STORE_MODE", "wholesale")

# Store-specific configuration
STORE_CONFIG = {
    "wholesale": {
        "name": "Landa Beauty Supply - Wholesale",
        # Auth requirements
        "require_auth_for_catalog": True,    # Must login to see products/prices
        "require_auth_for_cart": True,       # Must login to add to cart
        "require_auth_for_checkout": True,   # Must login to checkout
        # Order settings
        "min_order_amount": 100,             # Minimum order amount in USD
        "payment_methods": ["stripe", "zelle"],
        "allow_pickup": True,                # Store pickup available
        # Features
        "enable_order_combination": True,
        "enable_single_access_tokens": True,
        # Users
        "default_user_type": "stylist",
    },
    "retail": {
        "name": "Landa Beauty Supply - Retail",
        # Auth requirements
        "require_auth_for_catalog": False,   # Public catalog
        "require_auth_for_cart": False,      # Guest can add to cart
        "require_auth_for_checkout": True,   # TBD: might allow guest checkout
        # Order settings
        "min_order_amount": 0,               # No minimum
        "payment_methods": ["stripe"],       # Stripe only
        "allow_pickup": False,               # Delivery only
        # Features
        "enable_order_combination": True,
        "enable_single_access_tokens": True,
        # Users
        "default_user_type": "client",
    }
}


def get_store_config() -> dict:
    """
    Get configuration for current store mode.
    
    Usage:
        from config import get_store_config
        config = get_store_config()
        if config["require_auth_for_catalog"]:
            # require authentication
    """
    if STORE_MODE not in STORE_CONFIG:
        raise ValueError(f"Invalid STORE_MODE: {STORE_MODE}. Must be 'wholesale' or 'retail'")
    return STORE_CONFIG[STORE_MODE]


# Convenience flags for quick checks
IS_WHOLESALE = STORE_MODE == "wholesale"
IS_RETAIL = STORE_MODE == "retail"

# Log store mode on startup
logger.info(f"Store mode: {STORE_MODE} ({get_store_config()['name']})")