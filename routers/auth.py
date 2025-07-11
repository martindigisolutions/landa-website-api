from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from schemas.auth import UserCreate, UserUpdate, ResetPasswordSchema, LoginResponse, UserOut
from database import get_db
from services import auth_service
from models import User

router = APIRouter()

@router.post(
    "/register",
    summary="Register new user",
    description="Creates a new user account with email, phone, and password.",
    status_code=201
)
def register(user: UserCreate, db: Session = Depends(get_db)):
    return auth_service.register_user(user, db)

@router.patch(
    "/users/{user_id}",
    summary="Update user profile",
    description="Updates user fields like name, phone, email, birthdate, or user type. Only fields provided in the request will be updated."
)
def update_user(user_id: int, updates: UserUpdate, db: Session = Depends(get_db)):
    return auth_service.update_user_profile(user_id, updates, db)

@router.post(
    "/login",
    summary="User login",
    description="Authenticates user by email/phone and password. Returns access token.",
    response_model=LoginResponse,
)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return auth_service.login_user(form_data, db)

@router.post(
    "/forgot-password",
    summary="Request password reset",
    description="Sends a password reset email with a token link. Limit one request per hour."
)
def forgot_password(email: str = Body(..., embed=True), db: Session = Depends(get_db)):
    return auth_service.request_password_reset(email, db)

@router.post(
    "/reset-password",
    summary="Reset user password",
    description="Resets the user's password using a valid token received via email."
)
def reset_password(data: ResetPasswordSchema, db: Session = Depends(get_db)):
    return auth_service.reset_password(data, db)

@router.get(
    "/users/{user_id}",
    summary="Get user by ID",
    description="Returns the user's data if the requester is an admin or the user themselves.",
    response_model=UserOut
)
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    return auth_service.get_user_by_id(user_id, current_user, db)


