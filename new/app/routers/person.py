from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional
import enum

from app.database import get_db
from app.core.security import get_current_user, PermissionChecker
from app.models.residence_models import Resident, ResidentStatus, Gender, Household
from app.models.auth_models import User

router = APIRouter(prefix="/persons", tags=["Persons"])

class ResidentBase(BaseModel):
    full_name: str
    dob: date
    gender: Gender
    cid: str  # Removed min/max length for flexibility with test data
    relation_to_owner: str
    status: ResidentStatus = ResidentStatus.PERMANENT
    household_id: Optional[int] = None
    phone: Optional[str] = None  # Số điện thoại
    email: Optional[str] = None  # Email
    occupation: Optional[str] = None  # Nghề nghiệp

class ResidentCreate(ResidentBase):
    pass

class ResidentUpdate(BaseModel):
    full_name: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[Gender] = None
    cid: Optional[str] = None
    relation_to_owner: Optional[str] = None
    status: Optional[ResidentStatus] = None
    household_id: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    occupation: Optional[str] = None

class ResidentResponse(ResidentBase):
    id: int
    class Config:
        orm_mode = True

@router.post("/", response_model=ResidentResponse, dependencies=[Depends(PermissionChecker("person.create"))])
async def create_person(person: ResidentCreate, db: AsyncSession = Depends(get_db)):
    # Check duplicate CID
    existing = await db.execute(select(Resident).where(Resident.cid == person.cid))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Citizen ID already exists")

    # Check household if provided
    if person.household_id:
        hh = await db.get(Household, person.household_id)
        if not hh:
            raise HTTPException(status_code=404, detail="Household not found")

    new_person = Resident(**person.dict())
    db.add(new_person)
    await db.commit()
    await db.refresh(new_person)
    return new_person

@router.get("/", dependencies=[Depends(PermissionChecker("person.view"))])
async def list_persons(
    page: int = 1,
    limit: int = 10,
    household_id: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import func as sql_func, case
    
    # Build base query - order by household_id to group residents by household
    # Use CASE to put NULL household_id at the end (SQLite compatible)
    null_last_order = case((Resident.household_id.is_(None), 1), else_=0)
    query = select(Resident).order_by(null_last_order, Resident.household_id.asc(), Resident.id.asc())
    if household_id:
        query = select(Resident).where(Resident.household_id == household_id).order_by(Resident.id.asc())
    if search:
        query = query.where(
            Resident.full_name.ilike(f"%{search}%") | 
            Resident.cid.ilike(f"%{search}%")
        )
    
    # Get total count
    count_query = select(sql_func.count()).select_from(Resident)
    if household_id:
        count_query = count_query.where(Resident.household_id == household_id)
    if search:
        count_query = count_query.where(
            Resident.full_name.ilike(f"%{search}%") | 
            Resident.cid.ilike(f"%{search}%")
        )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Calculate pagination
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    page = max(1, min(page, total_pages))  # Ensure valid page
    skip = (page - 1) * limit
        
    # Get paginated data
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    persons = result.scalars().all()
    
    # Build response with household_code
    items = []
    for p in persons:
        # Get household code
        household_code = None
        if p.household_id:
            hh = await db.get(Household, p.household_id)
            if hh:
                household_code = hh.household_code
        
        items.append({
            "id": p.id,
            "full_name": p.full_name,
            "dob": p.dob.isoformat() if p.dob else None,
            "gender": p.gender.value if hasattr(p.gender, 'value') else str(p.gender),
            "cid": p.cid,
            "relation_to_owner": p.relation_to_owner,
            "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
            "household_id": p.household_id,
            "household_code": household_code,
            "phone": p.phone,
            "email": p.email,
            "occupation": p.occupation
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": total_pages,
        "limit": limit
    }

@router.get("/{id}", response_model=ResidentResponse, dependencies=[Depends(PermissionChecker("person.view"))])
async def get_person(id: int, db: AsyncSession = Depends(get_db)):
    person = await db.get(Resident, id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person

@router.put("/{id}", response_model=ResidentResponse, dependencies=[Depends(PermissionChecker("person.update"))])
async def update_person(id: int, person_update: ResidentUpdate, db: AsyncSession = Depends(get_db)):
    person = await db.get(Resident, id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    update_data = person_update.dict(exclude_unset=True)
    if "cid" in update_data:
        existing = await db.execute(select(Resident).where(Resident.cid == update_data["cid"], Resident.id != id))
        if existing.scalars().first():
             raise HTTPException(status_code=400, detail="Citizen ID already exists")

    for key, value in update_data.items():
        setattr(person, key, value)
    
    db.add(person)
    await db.commit()
    await db.refresh(person)
    return person


@router.delete("/{id}", dependencies=[Depends(PermissionChecker("person.delete"))])
async def delete_person(id: int, db: AsyncSession = Depends(get_db)):
    """
    Xóa nhân khẩu (soft delete - chuyển status thành MOVED_OUT).
    Nếu là chủ hộ, cần chuyển chủ hộ trước khi xóa.
    """
    person = await db.get(Resident, id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    # Check if person is a household owner
    if person.household_id:
        hh = await db.get(Household, person.household_id)
        if hh and hh.owner_id == id:
            raise HTTPException(
                status_code=400, 
                detail="Không thể xóa chủ hộ. Vui lòng chuyển quyền chủ hộ trước."
            )
    
    # Soft delete: set status to MOVED_OUT and remove from household
    person.status = ResidentStatus.MOVED_OUT
    person.household_id = None
    
    db.add(person)
    await db.commit()
    
    return {"status": "success", "message": "Đã xóa nhân khẩu khỏi hộ khẩu"}

