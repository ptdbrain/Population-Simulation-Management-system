from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models
from ..Schemas import UserCreate, UserOut
from ..db import get_db
from ..deps import get_current_user, require_permission


router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _perm = Depends(require_permission("user.manage"))):
    if crud.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="Username exists")
    u = crud.create_user(db, payload.username, payload.password, payload.full_name, payload.email, payload.phone)
    return u


@router.get("", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), _perm = Depends(require_permission("user.manage"))):
    users = db.query(models.User).all()
    return users


@router.put("/{user_id}/roles")
def set_roles(
    user_id: int,
    role_ids: List[int] = Body(..., embed=True),
    db: Session = Depends(get_db),
    _perm = Depends(require_permission("user.manage")),
):
    db.query(models.UserRole).filter(models.UserRole.user_id == user_id).delete()
    for rid in role_ids:
        db.add(models.UserRole(user_id=user_id, role_id=rid))
    db.commit()
    return {"status": "ok"}