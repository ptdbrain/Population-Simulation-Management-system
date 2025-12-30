"""
Admin User Management Router
Allows admins to manage users, roles, and permissions
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.core.security import get_current_user, get_password_hash, PermissionChecker
from app.models.auth_models import User, Role
from app.models.residence_models import Resident

router = APIRouter(prefix="/admin", tags=["Admin User Management"])


# ==========================================
# SCHEMAS
# ==========================================

class UserResponse(BaseModel):
    id: int
    username: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    resident_id: Optional[int] = None
    resident_name: Optional[str] = None
    is_active: bool
    
    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    username: str
    password: str
    role_id: int
    resident_id: Optional[int] = None
    is_active: bool = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[int] = None
    resident_id: Optional[int] = None
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    
    class Config:
        orm_mode = True


# ==========================================
# ROLE ENDPOINTS
# ==========================================

@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all available roles"""
    result = await db.execute(select(Role))
    roles = result.scalars().all()
    return [
        RoleResponse(id=r.id, name=r.name, description=r.description)
        for r in roles
    ]


# ==========================================
# USER ENDPOINTS
# ==========================================

@router.get("/users")
async def list_users(
    role_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users with optional filters"""
    # Check if current user is admin
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = role_result.scalars().first()
    if not role or role.name.lower() != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can manage users")
    
    # Build query
    query = select(User)
    
    if role_id is not None:
        query = query.where(User.role_id == role_id)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Build response with role and resident info
    response = []
    for user in users:
        # Get role name
        role_name = None
        if user.role_id:
            role_result = await db.get(Role, user.role_id)
            if role_result:
                role_name = role_result.name
        
        # Get resident name
        resident_name = None
        if user.resident_id:
            resident = await db.get(Resident, user.resident_id)
            if resident:
                resident_name = resident.full_name
        
        response.append({
            "id": user.id,
            "username": user.username,
            "role_id": user.role_id,
            "role_name": role_name,
            "resident_id": user.resident_id,
            "resident_name": resident_name,
            "is_active": user.is_active
        })
    
    return response


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a single user by ID"""
    # Check admin
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = role_result.scalars().first()
    if not role or role.name.lower() != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can manage users")
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get role name
    role_name = None
    if user.role_id:
        role_obj = await db.get(Role, user.role_id)
        if role_obj:
            role_name = role_obj.name
    
    # Get resident name
    resident_name = None
    if user.resident_id:
        resident = await db.get(Resident, user.resident_id)
        if resident:
            resident_name = resident.full_name
    
    return {
        "id": user.id,
        "username": user.username,
        "role_id": user.role_id,
        "role_name": role_name,
        "resident_id": user.resident_id,
        "resident_name": resident_name,
        "is_active": user.is_active
    }


@router.post("/users")
async def create_user(
    data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user"""
    # Check admin
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = role_result.scalars().first()
    if not role or role.name.lower() != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can create users")
    
    # Check if username exists
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if role exists
    role_exists = await db.get(Role, data.role_id)
    if not role_exists:
        raise HTTPException(status_code=400, detail="Role not found")
    
    # Create user
    new_user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        role_id=data.role_id,
        resident_id=data.resident_id,
        is_active=data.is_active
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {
        "status": "success",
        "message": "User created successfully",
        "user_id": new_user.id
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a user"""
    # Check admin
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = role_result.scalars().first()
    if not role or role.name.lower() != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can update users")
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent modifying own account's role
    if user_id == current_user.id and data.role_id and data.role_id != user.role_id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    # Update fields
    if data.username is not None:
        # Check if new username is taken
        existing = await db.execute(
            select(User).where(User.username == data.username, User.id != user_id)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Username already exists")
        user.username = data.username
    
    if data.password is not None:
        user.password_hash = get_password_hash(data.password)
    
    if data.role_id is not None:
        role_exists = await db.get(Role, data.role_id)
        if not role_exists:
            raise HTTPException(status_code=400, detail="Role not found")
        user.role_id = data.role_id
    
    if data.resident_id is not None:
        user.resident_id = data.resident_id
    
    if data.is_active is not None:
        # Prevent deactivating self
        if user_id == current_user.id and not data.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        user.is_active = data.is_active
    
    db.add(user)
    await db.commit()
    
    return {"status": "success", "message": "User updated successfully"}


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Activate or deactivate a user"""
    # Check admin
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = role_result.scalars().first()
    if not role or role.name.lower() != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can change user status")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own status")
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = is_active
    db.add(user)
    await db.commit()
    
    status_text = "activated" if is_active else "deactivated"
    return {"status": "success", "message": f"User {status_text} successfully"}


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change a user's role"""
    # Check admin
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = role_result.scalars().first()
    if not role or role.name.lower() != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can change user roles")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate new role
    new_role = await db.get(Role, role_id)
    if not new_role:
        raise HTTPException(status_code=400, detail="Role not found")
    
    user.role_id = role_id
    db.add(user)
    await db.commit()
    
    return {"status": "success", "message": f"User role changed to {new_role.name}"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user"""
    # Check admin
    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = role_result.scalars().first()
    if not role or role.name.lower() != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can delete users")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    
    return {"status": "success", "message": "User deleted successfully"}
