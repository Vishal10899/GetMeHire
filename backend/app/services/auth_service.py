import datetime
import uuid
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import User, Profile, AuditLog
from app.core.security import verify_password, get_password_hash, create_access_token, create_password_reset_token, verify_password_reset_token
from app.schemas.auth import UserCreate, UserLogin, UserResponse, Token

class AuthService:
    @staticmethod
    def register_user(db: Session, user_in: UserCreate) -> User:
        existing_user = db.query(User).filter(User.email == user_in.email.lower().strip()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists"
            )
        
        verification_token = str(uuid.uuid4())
        hashed_password = get_password_hash(user_in.password)
        
        new_user = User(
            email=user_in.email.lower().strip(),
            hashed_password=hashed_password,
            role="USER",
            account_status="ACTIVE",
            is_verified=True,  # Default to verified for immediate dev/test ease, token recorded
            verification_token=verification_token,
        )
        db.add(new_user)
        db.flush()

        # Initialize blank profile
        profile = Profile(
            user_id=new_user.id,
            skills=[],
            preferred_roles=[],
            preferred_countries=[],
            preferred_locations=[],
            work_arrangements=[],
            employment_types=[],
            profile_completion_pct=10
        )
        db.add(profile)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def authenticate_user(db: Session, credentials: UserLogin) -> Tuple[Token, User]:
        user = db.query(User).filter(User.email == credentials.email.lower().strip()).first()
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if user.account_status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.account_status.lower()}"
            )
        
        user.last_login_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        db.refresh(user)

        access_token = create_access_token(subject=user.id)
        token_response = Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
        return token_response, user

    @staticmethod
    def verify_email(db: Session, token: str) -> bool:
        user = db.query(User).filter(User.verification_token == token).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid verification token")
        user.is_verified = True
        user.verification_token = None
        db.commit()
        return True

    @staticmethod
    def request_password_reset(db: Session, email: str) -> str:
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if not user:
            # Avoid leaking whether user exists
            return "If an account exists, a reset link has been dispatched."
        token = create_password_reset_token(email=user.email, password_hash_sig=user.hashed_password)
        return token

    @staticmethod
    def confirm_password_reset(db: Session, token: str, new_password: str) -> bool:
        payload = verify_password_reset_token(token)
        if not payload or not payload.get("sub"):
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
        email = payload["sub"]
        expected_sig = payload.get("sig", "")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Single-use check: if signature does not match current hash, token was already used!
        if expected_sig and user.hashed_password[:12] != expected_sig:
            raise HTTPException(status_code=400, detail="Password reset token has already been used.")

        user.hashed_password = get_password_hash(new_password)
        db.commit()
        return True

    @staticmethod
    def delete_account(db: Session, user: User) -> bool:
        audit = AuditLog(
            actor_user_id=user.id,
            action="ACCOUNT_DELETION",
            target_type="USER",
            target_id=str(user.id),
            details={"email": user.email, "timestamp": datetime.datetime.utcnow().isoformat()}
        )
        db.add(audit)
        db.delete(user)
        db.commit()
        return True
