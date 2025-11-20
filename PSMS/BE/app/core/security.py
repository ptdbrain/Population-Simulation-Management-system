# app/security.py
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app import models

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ----- password helpers -----
def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


# ----- access token helpers -----
def create_access_token(
    subject: str,
    extra: dict | None = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    payload = {"sub": str(subject)}
    if extra:
        payload.update(extra)
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# ----- refresh token helpers -----
def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def create_and_persist_refresh_token(db: Session, user_id: int, device_info: Optional[str] = None) -> str:
    token = generate_refresh_token()
    token_hash = _hash_refresh_token(token)
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    rt = models.RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info=device_info,
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return token


def rotate_refresh_token(db: Session, old_token: str, user_id: int, device_info: Optional[str] = None) -> Optional[str]:
    old_hash = _hash_refresh_token(old_token)
    existing = db.query(models.RefreshToken).filter_by(token_hash=old_hash, user_id=user_id, revoked=False).first()
    if not existing:
        return None
    existing.revoked = True
    db.add(existing)
    db.commit()
    return create_and_persist_refresh_token(db, user_id=user_id, device_info=device_info)


def revoke_refresh_token(db: Session, token: str, user_id: int) -> bool:
    h = _hash_refresh_token(token)
    rt = db.query(models.RefreshToken).filter_by(token_hash=h, user_id=user_id).first()
    if not rt:
        return False
    rt.revoked = True
    db.add(rt)
    db.commit()
    return True


def verify_refresh_token(db: Session, token: str, user_id: int) -> bool:
    h = _hash_refresh_token(token)
    rt = db.query(models.RefreshToken).filter_by(token_hash=h, user_id=user_id, revoked=False).first()
    return bool(rt and rt.expires_at >= datetime.utcnow())
