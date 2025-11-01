# app/security.py
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import hashlib
import secrets
from app.core.config import settings
from app import models

load_dotenv()


pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ----- password helpers -----
def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

# ----- token helpers -----
def create_access_token(subject: str, extra: dict | None = None, expires_delta: Optional[timedelta] = None) -> str:
    data = {"sub": str(subject)}
    if extra:
        data.update(extra)
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_EXPIRE_MINUTES))
    data.update({"exp": expire})
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

# ----- refresh token helpers -----
def _hash_refresh_token(token: str) -> str:
    # hash refresh token with SHA256 (store hash in DB)
    return hashlib.sha256(token.encode()).hexdigest()

def generate_refresh_token() -> str:
    # generate a secure random token
    return secrets.token_urlsafe(64)

def create_and_persist_refresh_token(db: Session, user_id: int, device_info: Optional[str] = None) -> str:
    token = generate_refresh_token()
    token_hash = _hash_refresh_token(token)
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_EXPIRE_DAYS)
    rt = models.RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at, device_info=device_info)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return token  # return plain token to client (only shown once)

def rotate_refresh_token(db: Session, old_token: str, user_id: int, device_info: Optional[str] = None) -> Optional[str]:
    """
    When refreshing, revoke old refresh token and issue a new one (rotation).
    """
    old_hash = _hash_refresh_token(old_token)
    existing = db.query(models.RefreshToken).filter_by(token_hash=old_hash, user_id=user_id, revoked=False).first()
    if not existing:
        return None
    # revoke old
    existing.revoked = True
    db.add(existing)
    db.commit()
    # create new
    return create_and_persist_refresh_token(db, user_id=user_id, device_info=device_info)

def revoke_refresh_token(db: Session, token: str, user_id: int):
    h = _hash_refresh_token(token)
    rt = db.query(models.RefreshToken).filter_by(token_hash=h, user_id=user_id).first()
    if rt:
        rt.revoked = True
        db.add(rt)
        db.commit()
        return True
    return False

def verify_refresh_token(db: Session, token: str, user_id: int) -> bool:
    h = _hash_refresh_token(token)
    rt = db.query(models.RefreshToken).filter_by(token_hash=h, user_id=user_id, revoked=False).first()
    if not rt:
        return False
    if rt.expires_at < datetime.utcnow():
        return False
    return True
