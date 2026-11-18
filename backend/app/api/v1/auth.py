from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models import User
from app.schemas.auth import (
    UserCreate, UserLogin, UserResponse, Token,
    PasswordResetRequest, PasswordResetConfirm, EmailVerificationRequest
)
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    return AuthService.register_user(db, user_in)

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    token, _ = AuthService.authenticate_user(db, credentials)
    return token

@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    credentials = UserLogin(email=form_data.username, password=form_data.password)
    token, _ = AuthService.authenticate_user(db, credentials)
    return token

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Successfully logged out"}

@router.post("/verify-email")
def verify_email(req: EmailVerificationRequest, db: Session = Depends(get_db)):
    AuthService.verify_email(db, req.token)
    return {"message": "Email successfully verified"}

@router.post("/password-reset/request")
def request_password_reset(req: PasswordResetRequest, db: Session = Depends(get_db)):
    token_or_msg = AuthService.request_password_reset(db, req.email)
    return {"message": "Password reset token generated", "token": token_or_msg}

@router.post("/password-reset/confirm")
def confirm_password_reset(req: PasswordResetConfirm, db: Session = Depends(get_db)):
    AuthService.confirm_password_reset(db, req.token, req.new_password)
    return {"message": "Password reset successful"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.delete("/me")
def delete_account(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    AuthService.delete_account(db, current_user)
    return {"message": "Account successfully deleted"}
