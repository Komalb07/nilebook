from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import (
    UserCreate,
    UserLogin,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ResendVerificationRequest,
)
import models
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
import secrets
import hashlib
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from email_service import send_verification_email, send_password_reset_email
from currency_conversion import SUPPORTED_CURRENCIES

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

security = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-this-later")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

EMAIL_VERIFICATION_EXPIRE_HOURS = 24
PASSWORD_RESET_EXPIRE_MINUTES = 30

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_raw_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    default_currency = (user.default_currency or "USD").strip().upper()
    if default_currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail="Unsupported default currency")

    raw_verification_token = create_raw_token()
    verification_token_hash = hash_token(raw_verification_token)

    new_user = models.User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password_hash=hash_password(user.password),
        default_currency=default_currency,
        is_verified=False,
        email_verification_token_hash=verification_token_hash,
        email_verification_expires_at=datetime.utcnow()
        + timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS),
    )

    db.add(new_user)
    db.flush()

    verification_link = f"{FRONTEND_URL}/verify-email?token={raw_verification_token}"

    try:
        send_verification_email(new_user.email, verification_link)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Account was not created because the verification email could not be sent.",
        )

    db.commit()
    db.refresh(new_user)

    return {
        "message": "User created successfully. Please verify your email before logging in.",
        "user_id": new_user.id,
        "email": new_user.email,
    }


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    token_hash = hash_token(token)

    user = (
        db.query(models.User)
        .filter(models.User.email_verification_token_hash == token_hash)
        .first()
    )

    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification link")

    if user.is_verified:
        return {"message": "Email already verified. You can log in."}

    if (
        not user.email_verification_expires_at
        or user.email_verification_expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=400, detail="Verification link expired")

    user.is_verified = True
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None

    db.commit()

    return {"message": "Email verified successfully. You can now log in."}

@router.post("/resend-verification")
def resend_verification(
    request: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == request.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="This email does not exist.")

    if user.is_verified:
        return {"message": "This email is already verified. You can log in."}

    raw_verification_token = create_raw_token()
    verification_token_hash = hash_token(raw_verification_token)

    user.email_verification_token_hash = verification_token_hash
    user.email_verification_expires_at = datetime.utcnow() + timedelta(
        hours=EMAIL_VERIFICATION_EXPIRE_HOURS
    )

    verification_link = f"{FRONTEND_URL}/verify-email?token={raw_verification_token}"

    try:
        send_verification_email(user.email, verification_link)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Verification email could not be sent. Please try again later.",
        )

    db.commit()

    return {
        "message": "Verification link sent. Please check your inbox."
    }


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()

    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(user.password, existing_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not existing_user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in.",
        )

    access_token = create_access_token(
        data={
            "sub": existing_user.id,
            "email": existing_user.email,
        }
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": existing_user.id,
        "first_name": existing_user.first_name,
        "last_name": existing_user.last_name,
        "email": existing_user.email,
        "default_currency": existing_user.default_currency,
    }


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == request.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="This email does not exist.")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before resetting your password.",
        )

    raw_reset_token = create_raw_token()
    reset_token_hash = hash_token(raw_reset_token)

    user.password_reset_token_hash = reset_token_hash
    user.password_reset_expires_at = datetime.utcnow() + timedelta(
        minutes=PASSWORD_RESET_EXPIRE_MINUTES
    )

    reset_link = f"{FRONTEND_URL}/reset-password?token={raw_reset_token}"

    try:
        send_password_reset_email(user.email, reset_link)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Password reset email could not be sent. Please try again later.",
        )

    db.commit()

    return {
        "message": "A password reset link has been sent, please check your inbox."
    }


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = hash_token(request.token)

    user = (
        db.query(models.User)
        .filter(models.User.password_reset_token_hash == token_hash)
        .first()
    )

    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset link")

    if (
        not user.password_reset_expires_at
        or user.password_reset_expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=400, detail="Reset link expired")

    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters long",
        )

    user.password_hash = hash_password(request.new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None

    db.commit()

    return {"message": "Password reset successfully. You can now log in."}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    return user
