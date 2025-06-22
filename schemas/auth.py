from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import date, datetime

# ---------- User Schemas ----------

class BaseUser(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: EmailStr
    birthdate: Optional[date] = None
    user_type: Literal["client", "stylist"]

class UserCreate(BaseUser):
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    birthdate: Optional[date] = None
    user_type: Optional[Literal["client", "stylist"]] = None

class UserOut(BaseUser):
    id: int
    created_at: Optional[datetime] = None

# ---------- Auth Schemas ----------

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginResponse(Token):
    user: UserOut

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str
