"""
Resident self-service endpoints
Allows residents to view their own data (household, family, requests)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime

from app.database import get_db
from app.core.security import get_current_user
from app.models.residence_models import Resident, Household, ResidentStatus, Gender
from app.models.auth_models import User
from app.models.request_models import ResidentRequest

router = APIRouter(prefix="/my", tags=["My Data (Resident Self-Service)"])

# Response Models
class MyHouseholdResponse(BaseModel):
    id: int
    household_code: str
    address: str
    owner_name: Optional[str] = None
    member_count: int = 0
    
    class Config:
        orm_mode = True

class MyFamilyMemberResponse(BaseModel):
    id: int
    full_name: str
    dob: date
    gender: str
    cid: str
    relation_to_owner: str
    status: str
    
    class Config:
        orm_mode = True

class MyRequestResponse(BaseModel):
    id: int
    request_type: str
    title: str
    content: str
    status: str
    admin_note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

@router.get("/household", response_model=Optional[MyHouseholdResponse])
async def get_my_household(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current user's household information"""
    
    if not current_user.resident_id:
        raise HTTPException(status_code=404, detail="Bạn chưa được liên kết với nhân khẩu nào")
    
    # Get the resident record
    resident = await db.get(Resident, current_user.resident_id)
    if not resident:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin nhân khẩu")
    
    if not resident.household_id:
        raise HTTPException(status_code=404, detail="Bạn chưa thuộc hộ khẩu nào")
    
    # Get household with member count
    household = await db.get(Household, resident.household_id)
    if not household:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin hộ khẩu")
    
    # Count members
    result = await db.execute(
        select(Resident).where(Resident.household_id == household.id)
    )
    members = result.scalars().all()
    
    # Get owner name
    owner_name = None
    if household.owner_id:
        owner = await db.get(Resident, household.owner_id)
        if owner:
            owner_name = owner.full_name
    
    return MyHouseholdResponse(
        id=household.id,
        household_code=household.household_code,
        address=household.address,
        owner_name=owner_name,
        member_count=len(members)
    )

@router.get("/family", response_model=List[MyFamilyMemberResponse])
async def get_my_family(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all family members in the user's household"""
    
    if not current_user.resident_id:
        raise HTTPException(status_code=404, detail="Bạn chưa được liên kết với nhân khẩu nào")
    
    # Get the resident record
    resident = await db.get(Resident, current_user.resident_id)
    if not resident:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin nhân khẩu")
    
    if not resident.household_id:
        return []  # Return empty list if no household
    
    # Get all members in the same household
    result = await db.execute(
        select(Resident).where(Resident.household_id == resident.household_id)
    )
    members = result.scalars().all()
    
    return [
        MyFamilyMemberResponse(
            id=m.id,
            full_name=m.full_name,
            dob=m.dob,
            gender=m.gender.value if hasattr(m.gender, 'value') else str(m.gender),
            cid=m.cid,
            relation_to_owner=m.relation_to_owner,
            status=m.status.value if hasattr(m.status, 'value') else str(m.status)
        )
        for m in members
    ]

@router.get("/requests", response_model=List[MyRequestResponse])
async def get_my_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all requests submitted by the current user"""
    
    result = await db.execute(
        select(ResidentRequest)
        .where(ResidentRequest.requester_id == current_user.id)  # Fixed: use requester_id
        .order_by(ResidentRequest.created_at.desc())
    )
    requests = result.scalars().all()
    
    return [
        MyRequestResponse(
            id=r.id,
            request_type=r.request_type or "",  # String, no .value needed
            title=r.title,
            content=r.description or "",  # Fixed: use description
            status=r.status or "PENDING",  # String, no .value needed
            admin_note=r.approval_note,  # Fixed: use approval_note
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in requests
    ]

@router.get("/profile", response_model=Optional[MyFamilyMemberResponse])
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current user's resident profile"""
    
    if not current_user.resident_id:
        raise HTTPException(status_code=404, detail="Bạn chưa được liên kết với nhân khẩu nào")
    
    resident = await db.get(Resident, current_user.resident_id)
    if not resident:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin nhân khẩu")
    
    return MyFamilyMemberResponse(
        id=resident.id,
        full_name=resident.full_name,
        dob=resident.dob,
        gender=resident.gender.value if hasattr(resident.gender, 'value') else str(resident.gender),
        cid=resident.cid,
        relation_to_owner=resident.relation_to_owner,
        status=resident.status.value if hasattr(resident.status, 'value') else str(resident.status)
    )
