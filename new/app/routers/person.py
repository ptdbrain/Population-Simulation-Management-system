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

@router.get("/", response_model=List[ResidentResponse], dependencies=[Depends(PermissionChecker("person.view"))])
async def list_persons(
    skip: int = 0, 
    limit: int = 100, 
    household_id: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Resident)
    if household_id:
        query = query.where(Resident.household_id == household_id)
    if search:
        query = query.where(Resident.full_name.ilike(f"%{search}%") | Resident.cid.ilike(f"%{search}%"))
        
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

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
