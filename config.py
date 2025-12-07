import os
from dotenv import load_dotenv

env_file = os.getenv("ENV_FILE", ".env.dev")
load_dotenv(env_file)

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")
FRONTEND_RESET_URL = os.getenv("FRONTEND_RESET_URL")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

PASSWORD_RESET_MAX_REQUESTS_PER_HOUR = int(os.getenv("PASSWORD_RESET_MAX_REQUESTS_PER_HOUR", 3))

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Admin App Configuration (OAuth2)
# If these are set, the super admin app will be auto-created on startup
ADMIN_CLIENT_ID = os.getenv("ADMIN_CLIENT_ID")
ADMIN_CLIENT_SECRET = os.getenv("ADMIN_CLIENT_SECRET")