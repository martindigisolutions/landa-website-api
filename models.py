from sqlalchemy import Column, Integer, String, Boolean, Float, Date
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    hashed_password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    short_description = Column(String)
    regular_price = Column(Float)
    sale_price = Column(Float)
    stock = Column(Integer)
    is_in_stock = Column(Boolean)
    restock_date = Column(Date, nullable=True)
    is_favorite = Column(Boolean)
    notify_when_available = Column(Boolean)
    image_url = Column(String)
    currency = Column(String)
    low_stock_threshold = Column(Integer)
    has_variants = Column(Boolean, default=False)
    brand = Column(String)
