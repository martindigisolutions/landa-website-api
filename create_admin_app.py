"""
Script to create the first admin application with all scopes.
Run this once to bootstrap your OAuth2 system.

Usage:
    # Auto-generate credentials (shown in console):
    python create_admin_app.py

    # Use predefined credentials from environment variables:
    set ADMIN_CLIENT_ID=app_my_custom_id
    set ADMIN_CLIENT_SECRET=sk_live_my_super_secret_key_here
    python create_admin_app.py

    # Force create even if apps exist:
    python create_admin_app.py --force

    # Output credentials to file (for automation):
    python create_admin_app.py --output credentials.json
"""

import os
import sys
import json
from database import SessionLocal
from models import Application
from services.admin_service import generate_client_id, generate_client_secret, hash_secret, AVAILABLE_SCOPES


def create_super_admin_app(force: bool = False, output_file: str = None):
    """Create a super admin application with all scopes"""
    db = SessionLocal()
    
    try:
        # Check if any app already exists
        existing = db.query(Application).filter(Application.name == "Super Admin Dashboard").first()
        if existing and not force:
            print("⚠️  Super Admin application already exists.")
            print(f"   client_id: {existing.client_id}")
            print()
            print("   Use --force to create another admin app.")
            print("   Or use the API to create apps with limited scopes.")
            return None
        
        # Check for environment variables (useful for production/CI)
        env_client_id = os.getenv("ADMIN_CLIENT_ID")
        env_client_secret = os.getenv("ADMIN_CLIENT_SECRET")
        
        if env_client_id and env_client_secret:
            client_id = env_client_id
            client_secret = env_client_secret
            print("📌 Using credentials from environment variables")
        else:
            client_id = generate_client_id()
            client_secret = generate_client_secret()
            print("🔑 Generating new credentials")
        
        # Create the super admin app with wildcard scope (all permissions)
        app = Application(
            client_id=client_id,
            client_secret_hash=hash_secret(client_secret),
            name="Super Admin Dashboard",
            description="Main admin application with full access",
            scopes=["*"],  # Wildcard = all permissions
            is_active=True
        )
        
        db.add(app)
        db.commit()
        
        credentials = {
            "client_id": client_id,
            "client_secret": client_secret,
            "scopes": ["*"]  # Wildcard = all permissions
        }
        
        # Output to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(credentials, f, indent=2)
            print(f"✅ Credentials saved to: {output_file}")
            print("   ⚠️  Keep this file secure and don't commit to git!")
            return credentials
        
        # Print to console
        print()
        print("=" * 60)
        print("✅ Super Admin Application Created Successfully!")
        print("=" * 60)
        print()
        print("🔐 SAVE THESE CREDENTIALS (shown only once):")
        print()
        print(f"   client_id:     {client_id}")
        print(f"   client_secret: {client_secret}")
        print()
        print("📋 Granted scopes:")
        print("   - * (all permissions)")
        print()
        print("   Includes:")
        for scope in AVAILABLE_SCOPES:
            print(f"     • {scope}")
        print()
        print("=" * 60)
        print("🚀 How to use:")
        print()
        print("1. Get an access token:")
        print("   POST /oauth/token")
        print("   Content-Type: application/x-www-form-urlencoded")
        print()
        print(f"   grant_type=client_credentials&client_id={client_id}&client_secret=<your_secret>")
        print()
        print("2. Use the token in requests:")
        print("   Authorization: Bearer <your_access_token>")
        print()
        print("3. Access admin endpoints:")
        print("   GET /admin/orders")
        print("   POST /admin/products")
        print("   GET /admin/stats")
        print("=" * 60)
        
        return credentials
        
    finally:
        db.close()


def print_help():
    print("""
Usage: python create_admin_app.py [OPTIONS]

Options:
    --force         Create a new admin app even if one exists
    --output FILE   Save credentials to a JSON file instead of printing
    --help          Show this help message

Environment Variables:
    ADMIN_CLIENT_ID      Use a custom client_id
    ADMIN_CLIENT_SECRET  Use a custom client_secret

Examples:
    python create_admin_app.py
    python create_admin_app.py --force
    python create_admin_app.py --output credentials.json
    
    # With custom credentials:
    set ADMIN_CLIENT_ID=app_production_admin
    set ADMIN_CLIENT_SECRET=sk_live_your_secure_secret_here_64_chars_minimum
    python create_admin_app.py
""")


if __name__ == "__main__":
    args = sys.argv[1:]
    
    if "--help" in args:
        print_help()
        sys.exit(0)
    
    force = "--force" in args
    output_file = None
    
    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 < len(args):
            output_file = args[idx + 1]
        else:
            print("Error: --output requires a filename")
            sys.exit(1)
    
    create_super_admin_app(force=force, output_file=output_file)

