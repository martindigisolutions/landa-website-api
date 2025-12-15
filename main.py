import os
import sys
import traceback
from contextlib import asynccontextmanager

print("🚀 Starting Landa Beauty Supply API...")
print(f"Python version: {sys.version}")
print(f"DATABASE_URL set: {bool(os.getenv('DATABASE_URL'))}")

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    print("✅ FastAPI imported")
except Exception as e:
    print(f"❌ Error importing FastAPI: {e}")
    traceback.print_exc()
    raise

try:
    from routers import auth, products, checkout_router, stripe_router, oauth_router, admin_router
    print("✅ Routers imported")
except Exception as e:
    print(f"❌ Error importing routers: {e}")
    traceback.print_exc()
    raise

try:
    from database import Base, engine, SessionLocal
    print("✅ Database imported")
except Exception as e:
    print(f"❌ Error importing database: {e}")
    traceback.print_exc()
    raise

try:
    from mangum import Mangum
    from config import ADMIN_CLIENT_ID, ADMIN_CLIENT_SECRET
    print("✅ Config imported")
except Exception as e:
    print(f"❌ Error importing config: {e}")
    traceback.print_exc()
    raise


def init_admin_app():
    """
    Auto-create or update super admin app on startup if ADMIN_CLIENT_ID and ADMIN_CLIENT_SECRET
    are set in environment variables. This runs once when the API starts.
    """
    if not ADMIN_CLIENT_ID or not ADMIN_CLIENT_SECRET:
        return  # No env vars set, skip
    
    try:
        from models import Application
        from services.admin_service import hash_secret, AVAILABLE_SCOPES
        
        db = SessionLocal()
        try:
            existing = db.query(Application).filter(
                Application.client_id == ADMIN_CLIENT_ID
            ).first()
            
            new_secret_hash = hash_secret(ADMIN_CLIENT_SECRET)
            
            if existing:
                updated = False
                
                if existing.client_secret_hash != new_secret_hash:
                    existing.client_secret_hash = new_secret_hash
                    updated = True
                    print(f"🔄 Admin app '{ADMIN_CLIENT_ID}' secret updated")
                
                if not existing.is_active:
                    existing.is_active = True
                    updated = True
                    print(f"✅ Admin app '{ADMIN_CLIENT_ID}' reactivated")
                
                if set(existing.scopes or []) != set(AVAILABLE_SCOPES):
                    existing.scopes = AVAILABLE_SCOPES
                    updated = True
                    print(f"🔄 Admin app '{ADMIN_CLIENT_ID}' scopes updated")
                
                if updated:
                    db.commit()
                return
            
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
    except Exception as e:
        print(f"⚠️ Could not initialize admin app: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"⚠️ Could not create tables: {e}")
    
    init_admin_app()
    
    yield
    # Shutdown (nothing to do)


# Initialize app
app = FastAPI(
    title="Landa Beauty Supply API",
    description="API for Landa Beauty Supply e-commerce platform",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint to verify the API is running."""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "service": "Landa Beauty Supply API",
            "version": "1.0.0"
        }
    }

# Enable CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(checkout_router.router)
app.include_router(stripe_router.router)
app.include_router(oauth_router.router)
app.include_router(admin_router.router)

# Lambda handler
handler = Mangum(app)
