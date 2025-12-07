from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, products, checkout_router, stripe_router, oauth_router, admin_router
from database import Base, engine, SessionLocal
from mangum import Mangum
from config import ADMIN_CLIENT_ID, ADMIN_CLIENT_SECRET

# Initialize app
app = FastAPI(
    title="Landa Beauty Supply API",
    description="API for Landa Beauty Supply e-commerce platform",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)


def init_admin_app():
    """
    Auto-create or update super admin app on startup if ADMIN_CLIENT_ID and ADMIN_CLIENT_SECRET
    are set in environment variables. This runs once when the API starts.
    
    - If app doesn't exist: creates it
    - If app exists: updates the secret (in case it changed in env vars)
    - If app was deactivated: reactivates it
    """
    if not ADMIN_CLIENT_ID or not ADMIN_CLIENT_SECRET:
        return  # No env vars set, skip
    
    from models import Application
    from services.admin_service import hash_secret, AVAILABLE_SCOPES
    
    db = SessionLocal()
    try:
        # Check if this specific app already exists
        existing = db.query(Application).filter(
            Application.client_id == ADMIN_CLIENT_ID
        ).first()
        
        new_secret_hash = hash_secret(ADMIN_CLIENT_SECRET)
        
        if existing:
            # App exists - update secret and ensure it's active
            updated = False
            
            if existing.client_secret_hash != new_secret_hash:
                existing.client_secret_hash = new_secret_hash
                updated = True
                print(f"🔄 Admin app '{ADMIN_CLIENT_ID}' secret updated")
            
            if not existing.is_active:
                existing.is_active = True
                updated = True
                print(f"✅ Admin app '{ADMIN_CLIENT_ID}' reactivated")
            
            # Always ensure all scopes are present
            if set(existing.scopes or []) != set(AVAILABLE_SCOPES):
                existing.scopes = AVAILABLE_SCOPES
                updated = True
                print(f"🔄 Admin app '{ADMIN_CLIENT_ID}' scopes updated")
            
            if updated:
                db.commit()
            return
        
        # Create the super admin app with the provided credentials
        new_app = Application(
            client_id=ADMIN_CLIENT_ID,
            client_secret_hash=new_secret_hash,
            name="Super Admin Dashboard",
            description="Main admin application with full access (auto-created)",
            scopes=AVAILABLE_SCOPES,
            is_active=True
        )
        
        db.add(new_app)
        db.commit()
        print(f"✅ Super Admin app created: {ADMIN_CLIENT_ID}")
        
    finally:
        db.close()


# Initialize admin app on startup
init_admin_app()

# Include routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(checkout_router.router)
app.include_router(stripe_router.router)
app.include_router(oauth_router.router)
app.include_router(admin_router.router)

# Lambda handler
handler = Mangum(app)
