from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, products
from database import Base, engine
from mangum import Mangum

# Initialize app
app = FastAPI()

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

# Include routers
app.include_router(auth.router)
app.include_router(products.router)

# Lambda handler
handler = Mangum(app)
