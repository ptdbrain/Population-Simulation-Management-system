# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta, datetime

from ..db import get_db
from .. import models, crud
from ..Schemas import Token, LoginIn, UserCreate, UserOut
from app.core.security import hash_password, verify_password, create_access_token, create_and_persist_refresh_token, rotate_refresh_token, verify_refresh_token, revoke_refresh_token

router = APIRouter(tags=["auth"])

# Register endpoint: by default assign 'citizen' role; admin can create other roles via admin API
@router.post("/api/auth/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    # Basic password policy
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if crud.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="Username exists")
    user = crud.create_user(db, payload.username, payload.password, payload.full_name, payload.email, payload.phone)
    # assign default citizen role
    citizen_role = db.query(models.Role).filter(models.Role.name == "citizen").first()
    if citizen_role:
        db.add(models.UserRole(user_id=user.id, role_id=citizen_role.id))
        db.commit()
    return user

# Login (OAuth2PasswordRequestForm compatible)
@router.post("/api/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db), request: Request = None):
    user = crud.get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        # optional: increment failed_login_attempts, lockout, rate limit
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User disabled")
    # gather roles and permissions to include in token (optional)
    perm_rows = db.execute("""
        SELECT p.code FROM permissions p
        JOIN role_permissions rp ON rp.permission_id = p.id
        JOIN user_roles ur ON ur.role_id = rp.role_id
        WHERE ur.user_id = :uid
    """, {"uid": user.id}).fetchall()
    perms = [r[0] for r in perm_rows] if perm_rows else []
    role_rows = db.execute("SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id=r.id WHERE ur.user_id=:uid", {"uid": user.id}).fetchall()
    roles = [r[0] for r in role_rows] if role_rows else []

    # create short-lived access token with roles & perms (beware of token size)
    extra = {"roles": roles, "perms": perms}
    access_token = create_access_token(subject=str(user.id), extra=extra, expires_delta=timedelta(minutes=60))

    # create refresh token and persist hashed
    device_info = request.headers.get("user-agent", "") if request else ""
    refresh_token = create_and_persist_refresh_token(db, user_id=user.id, device_info=device_info)

    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}

# Refresh endpoint
@router.post("/api/auth/refresh", response_model=Token)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    # decode user id from refresh token DB lookup (we store user_id in RefreshToken), but token itself is random
    # we must find the refresh token hash in DB, get user_id
    # for performance we created verify_refresh_token to check existence
    # however we need user_id to issue access token and rotate
    token_hash = None
    from core.security import _hash_refresh_token  # if needed, else replicate logic
    h = _hash_refresh_token(refresh_token)
    row = db.query(models.RefreshToken).filter_by(token_hash=h, revoked=False).first()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")
    user = db.query(models.User).get(row.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")

    # gather perms/roles
    perm_rows = db.execute("""
        SELECT p.code FROM permissions p
        JOIN role_permissions rp ON rp.permission_id = p.id
        JOIN user_roles ur ON ur.role_id = rp.role_id
        WHERE ur.user_id = :uid
    """, {"uid": user.id}).fetchall()
    perms = [r[0] for r in perm_rows] if perm_rows else []
    role_rows = db.execute("SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id=r.id WHERE ur.user_id=:uid", {"uid": user.id}).fetchall()
    roles = [r[0] for r in role_rows] if role_rows else []

    # rotate refresh token (revoke old, issue new)
    new_refresh = rotate_refresh_token(db, refresh_token, user.id, device_info=row.device_info)
    if not new_refresh:
        raise HTTPException(status_code=401, detail="Refresh token invalid or rotation failed")

    access_token = create_access_token(subject=str(user.id), extra={"roles": roles, "perms": perms})
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": new_refresh}

# Logout: revoke refresh token(s)
@router.post("/api/auth/logout")
def logout(refresh_token: str, db: Session = Depends(get_db)):
    # revoke provided refresh token
    revoked = revoke_refresh_token(db, refresh_token, user_id=None)  # you can identify user via token hash or require auth
    return {"status": "ok"}
