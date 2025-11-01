from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models
from ..Schemas import UserCreate, UserOut
from ..db import get_db     # phiên làm việc với cơ sở dữ liệu
from ..deps import get_current_user, require_permission
from .. import crud, models
from ..Schemas import PersonCreate, PersonOut, RoleOut
from pydantic import BaseModel
from typing import List


router = APIRouter(prefix="/api/users", tags=["users"]) # Định nghĩa router với tiền tố /api/users

@router.post("/api/users", response_model=UserOut) # tạo người dùng mới , route POST /api/users/
def create_user(payload: UserCreate, db: Session = Depends(get_db), _perm = Depends(require_permission("user.manage"))): # yêu cầu quyền user.manage để tạo người dùng mới
    if crud.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="Username exists") # nếu tên người dùng đã tồn tại thì trả về lỗi 400
    u = crud.create_user(db, payload.username, payload.password, payload.full_name, payload.email, payload.phone) # tạo người dùng mới
    return u

@router.get("/api/users", response_model=List[UserOut]) # lấy danh sách người dùng , route GET /api/users/
def list_users(db: Session = Depends(get_db), _perm = Depends(require_permission("user.manage"))): # yêu cầu quyền user.manage để lấy danh sách người dùng
    users = db.query(models.User).all()# lấy tất cả người dùng từ cơ sở dữ liệu
    return users

@router.put("/api/users/{user_id}/roles") # gán vai trò cho người dùng , route PUT /api/users/{user_id}/roles
def set_roles(user_id: int, role_ids: List[int], db: Session = Depends(get_db), _perm = Depends(require_permission("user.manage"))): # yêu cầu quyền user.manage để gán vai trò cho người dùng
    # simple replace behaviour
    db.query(models.UserRole).filter(models.UserRole.user_id==user_id).delete() # xóa tất cả vai trò hiện tại của người dùng
    for rid in role_ids:    # gán vai trò mới cho người dùng
        db.add(models.UserRole(user_id=user_id, role_id=rid))# thêm vai trò mới vào phiên làm việc với cơ sở dữ liệu
    db.commit()
    return {"status": "ok"}