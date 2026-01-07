import os
import json
from dotenv import load_dotenv

env_file = os.getenv("ENV_FILE", ".env.dev")
load_dotenv(env_file)

# Support for JSON secret from AWS Secrets Manager (for production)
# If APP_SECRETS_JSON is set, parse it and extract individual values
# Otherwise, use individual environment variables (for local development)
APP_SECRETS_JSON = os.getenv("APP_SECRETS_JSON")
_secrets_dict = {}
if APP_SECRETS_JSON:
    try:
        _secrets_dict = json.loads(APP_SECRETS_JSON)
    except json.JSONDecodeError:
        _secrets_dict = {}

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