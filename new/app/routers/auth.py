from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta, date
from pydantic import BaseModel
from typing import Optional, Literal

from app.database import get_db
from app.core import security
from app.models.auth_models import User, Role
from app.models.residence_models import Resident, Gender, ResidentStatus
from app.config import settings

router = APIRouter(tags=["Authentication"])

# ==========================================
# SCHEMAS
# ==========================================
class RegisterRequest(BaseModel):
    username: str
    password: str
    role: Literal["admin", "leader", "resident"]
    verification_code: Optional[str] = None  # Required for admin/leader
    cccd: Optional[str] = None  # Required for citizen
    # New fields for creating new resident (only needed if CCCD is new)
    full_name: Optional[str] = None
    dob: Optional[str] = None  # Format: YYYY-MM-DD
    gender: Optional[Literal["MALE", "FEMALE"]] = None

class RegisterResponse(BaseModel):
    message: str
    username: str
    is_new_resident: Optional[bool] = False

class CheckCCCDRequest(BaseModel):
    cccd: str

class CheckCCCDResponse(BaseModel):
    exists: bool
    resident_name: Optional[str] = None
    has_account: bool = False

# ==========================================
# CHECK CCCD ENDPOINT (for frontend)
# ==========================================
@router.post("/check-cccd", response_model=CheckCCCDResponse)
async def check_cccd(request: CheckCCCDRequest, db: AsyncSession = Depends(get_db)):
    """Check if a CCCD exists in the system"""
    resident_result = await db.execute(select(Resident).where(Resident.cid == request.cccd))
    resident = resident_result.scalars().first()
    
    if not resident:
        return CheckCCCDResponse(exists=False)
    
    # Check if resident already has an account
    existing_user = await db.execute(select(User).where(User.resident_id == resident.id))
    has_account = existing_user.scalars().first() is not None
    
    return CheckCCCDResponse(
        exists=True,
        resident_name=resident.full_name,
        has_account=has_account
    )

# ==========================================
# LOGIN ENDPOINT
# ==========================================
@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Get user's role
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalars().first()
    role_name = role.name.lower() if role else "resident"

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={
            "sub": user.username,
            "role": role_name,
            "role_id": user.role_id,
            "user_id": user.id,
            "resident_id": user.resident_id
        }, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": role_name,
        "username": user.username
    }

# ==========================================
# REGISTRATION ENDPOINT
# ==========================================
@router.post("/register", response_model=RegisterResponse)
async def register_user(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
    - Admin/Leader: Requires verification_code
    - Resident with existing CCCD: Links to existing Resident
    - Resident with new CCCD: Creates new Resident + User account
    """
    # Check if username already exists
    existing_user = await db.execute(select(User).where(User.username == request.username))
    if existing_user.scalars().first():
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")
    
    # Get role from database
    role_result = await db.execute(select(Role).where(Role.name == request.role))
    role = role_result.scalars().first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Vai trò '{request.role}' không tồn tại")
    
    resident_id = None
    is_new_resident = False
    
    # Role-based validation
    if request.role in ["admin", "leader"]:
        # Validate verification code
        if not request.verification_code:
            raise HTTPException(status_code=400, detail="Mã xác minh là bắt buộc cho vai trò này")
        
        expected_code = settings.ADMIN_REGISTER_CODE if request.role == "admin" else settings.LEADER_REGISTER_CODE
        if request.verification_code != expected_code:
            raise HTTPException(status_code=400, detail="Mã xác minh không chính xác")
    
    elif request.role == "resident":
        # Validate CCCD
        if not request.cccd:
            raise HTTPException(status_code=400, detail="Số CCCD là bắt buộc cho cư dân")
        
        # Check CCCD format (12 digits)
        if not request.cccd.isdigit() or len(request.cccd) != 12:
            raise HTTPException(status_code=400, detail="Số CCCD phải có đúng 12 chữ số")
        
        # Find resident by CCCD
        resident_result = await db.execute(select(Resident).where(Resident.cid == request.cccd))
        resident = resident_result.scalars().first()
        
        if resident:
            # CCCD exists - link to existing resident
            existing_resident_user = await db.execute(select(User).where(User.resident_id == resident.id))
            if existing_resident_user.scalars().first():
                raise HTTPException(status_code=400, detail="Cư dân này đã có tài khoản")
            
            resident_id = resident.id
        else:
            # CCCD is new - create new resident
            # Validate required fields for new resident
            if not request.full_name:
                raise HTTPException(status_code=400, detail="Họ và tên là bắt buộc cho CCCD mới")
            if not request.dob:
                raise HTTPException(status_code=400, detail="Ngày sinh là bắt buộc cho CCCD mới")
            if not request.gender:
                raise HTTPException(status_code=400, detail="Giới tính là bắt buộc cho CCCD mới")
            
            # Parse date of birth
            try:
                dob_date = date.fromisoformat(request.dob)
            except ValueError:
                raise HTTPException(status_code=400, detail="Định dạng ngày sinh không hợp lệ (YYYY-MM-DD)")
            
            # Create new resident
            new_resident = Resident(
                full_name=request.full_name,
                dob=dob_date,
                gender=Gender(request.gender),
                cid=request.cccd,
                relation_to_owner="HEAD",  # Default, can be changed later
                status=ResidentStatus.PERMANENT,
                household_id=None  # Will be assigned later via request
            )
            db.add(new_resident)
            await db.flush()  # Get the ID
            
            resident_id = new_resident.id
            is_new_resident = True
    
    # Create new user
    password_hash = security.get_password_hash(request.password)
    new_user = User(
        username=request.username,
        password_hash=password_hash,
        role_id=role.id,
        resident_id=resident_id,
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    
    if is_new_resident:
        return RegisterResponse(
            message="Đăng ký thành công! Đã tạo hồ sơ cư dân mới. Vui lòng liên hệ quản trị để được nhập hộ khẩu.",
            username=request.username,
            is_new_resident=True
        )
    else:
        return RegisterResponse(message="Đăng ký thành công!", username=request.username)

