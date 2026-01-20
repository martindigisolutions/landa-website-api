from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import date, datetime

# ---------- User Schemas ----------

class BaseUser(BaseModel):
    first_name: str
    last_name: str
    phone: str
    whatsapp_phone: Optional[str] = None
    email: EmailStr
    birthdate: Optional[date] = None
    user_type: Optional[Literal["client", "stylist"]] = None  # Optional - backend assigns based on STORE_MODE

class UserCreate(BaseUser):
    password: str
    # Note: user_type is optional. If not provided, backend uses default from STORE_CONFIG
    
    # Business info (only used in wholesale registration)
    estimated_monthly_purchase: Optional[float] = None  # Estimated monthly purchase amount (USD)
    notes: Optional[str] = None  # Additional notes from the applicant
    
    # Business profile (multiple choice - only used in wholesale registration)
    # business_types: ["independent_stylist", "salon", "barbershop", "student", "distributor", "other"]
    business_types: Optional[list[str]] = None
    # services_offered: ["coloring", "bleaching", "straightening", "treatments", "cuts_styling", "other"]
    services_offered: Optional[list[str]] = None
    # frequent_products: ["dyes", "peroxides", "bleaches", "treatments", "professional_shampoo"]
    frequent_products: Optional[list[str]] = None
    # team_size: "solo", "2-3", "4-6", "7+"
    team_size: Optional[str] = None

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    birthdate: Optional[date] = None
    user_type: Optional[Literal["client", "stylist"]] = None

class UserOut(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    email: Optional[str] = None
    birthdate: Optional[date] = None
    user_type: str
    registration_complete: bool = True
    created_at: Optional[datetime] = None
    
    # Password status fields
    has_password: bool = True  # Computed: True if user has a password set
    password_requires_update: bool = False  # True if user needs to set/update password
    password_last_updated: Optional[datetime] = None  # Last time password was changed

    class Config:
        from_attributes = True

# ---------- Auth Schemas ----------

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginResponse(Token):
    user: UserOut

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str
