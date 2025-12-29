from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from datetime import date
from typing import List, Optional

from app.database import get_db
from app.core.security import get_current_user, PermissionChecker
from app.models.temp_models import AbsentRequest, TempResidenceRegistration, RequestStatus
from app.models.residence_models import Resident, ResidentStatus, Gender
from app.models.auth_models import User

router = APIRouter(prefix="", tags=["Temporary Residence"])  # No prefix here since routes already have full paths

# --- Schemas ---
class AbsentRequestCreate(BaseModel):
    resident_id: int
    start_date: date
    end_date: date
    reason: str
    destination: str

class TempResidenceCreate(BaseModel):
    full_name: str
    dob: date
    origin_address: str
    host_household_id: int
    start_date: date
    end_date: date
    reason: str

# --- Absent Requests ---
@router.post("/absent-requests", dependencies=[Depends(PermissionChecker("temp_absence.create"))])
async def create_absent_request(req: AbsentRequestCreate, db: AsyncSession = Depends(get_db)):
    # Verify resident
    resident = await db.get(Resident, req.resident_id)
    if not resident:
        raise HTTPException(status_code=404, detail="Resident not found")
        
    new_req = AbsentRequest(**req.dict())
    db.add(new_req)
    await db.commit()
    return {"status": "success", "id": new_req.id}

@router.post("/absent-requests/{id}/approve", dependencies=[Depends(PermissionChecker("temp_absence.approve"))])
async def approve_absent_request(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = await db.get(AbsentRequest, id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    req.status = RequestStatus.APPROVED
    req.approved_by = current_user.id
    
    # Update resident status immediately if date is valid? 
    # Logic 3 says "Scheduler Check", but we can also check now.
    resident = await db.get(Resident, req.resident_id)
    today = date.today()
    if req.start_date <= today <= req.end_date:
        resident.status = ResidentStatus.TEMPORARY_ABSENT
        db.add(resident)
        
    db.add(req)
    await db.commit()
    return {"status": "approved"}

# --- Temp Residence ---
@router.post("/temp-residences", dependencies=[Depends(PermissionChecker("temp_residence.create"))])
async def create_temp_residence(req: TempResidenceCreate, db: AsyncSession = Depends(get_db)):
    # Verify host household
    # (Assuming we just store it, or verify existence)
    # logic skipped for brevity, standard lookup
    
    new_reg = TempResidenceRegistration(**req.dict())
    # Note: Temp Residency usually doesn't create a 'Resident' entity until approved or depends on system design.
    # Here we just store the registration slip.
    db.add(new_reg)
    await db.commit()
    return {"status": "success", "id": new_reg.id}

@router.post("/temp-residences/{id}/approve", dependencies=[Depends(PermissionChecker("temp_residence.approve"))])
async def approve_temp_residence(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Approval logic for Temp Residence usually involves adding a record to Residents table with status=TEMPORARY_RESIDENT
    # This aligns the systems.
    
    reg = await db.get(TempResidenceRegistration, id)
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    
    # Update registration status
    reg.status = RequestStatus.APPROVED
    reg.approved_by = current_user.id
    db.add(reg)
        
    # Create a Resident record
    temp_resident = Resident(
        full_name=reg.full_name,
        dob=reg.dob,
        gender=Gender.MALE,
        cid=f"TEMP-{id}",
        household_id=reg.host_household_id,
        relation_to_owner="GUEST",
        status=ResidentStatus.TEMPORARY_RESIDENT
    )
    db.add(temp_resident)
    await db.commit()
    return {"status": "approved", "resident_id": temp_resident.id}

# --- Reject Endpoints ---
class RejectRequest(BaseModel):
    reason: Optional[str] = None

@router.post("/absent-requests/{id}/reject", dependencies=[Depends(PermissionChecker("temp_absence.approve"))])
async def reject_absent_request(id: int, reject_data: RejectRequest = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = await db.get(AbsentRequest, id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    req.status = RequestStatus.REJECTED
    req.approved_by = current_user.id
    db.add(req)
    await db.commit()
    return {"status": "rejected"}

@router.post("/temp-residences/{id}/reject", dependencies=[Depends(PermissionChecker("temp_residence.approve"))])
async def reject_temp_residence(id: int, reject_data: RejectRequest = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    reg = await db.get(TempResidenceRegistration, id)
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    
    reg.status = RequestStatus.REJECTED
    reg.approved_by = current_user.id
    db.add(reg)
    await db.commit()
    return {"status": "rejected"}

# --- Certificate Generation ---
@router.get("/absent-requests/{id}/certificate", dependencies=[Depends(PermissionChecker("temp_absence.approve"))])
async def generate_absent_certificate(id: int, db: AsyncSession = Depends(get_db)):
    """Generate a certificate for an approved absent request"""
    req = await db.get(AbsentRequest, id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req.status != RequestStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Certificate can only be generated for approved requests")
    
    # Get resident info
    resident = await db.get(Resident, req.resident_id)
    if not resident:
        raise HTTPException(status_code=404, detail="Resident not found")
    
    # Return certificate data (frontend will format and display/print)
    return {
        "certificate_type": "TEMPORARY_ABSENCE",
        "resident_name": resident.full_name,
        "resident_cid": resident.cid,
        "resident_dob": str(resident.dob),
        "start_date": str(req.start_date),
        "end_date": str(req.end_date),
        "destination": req.destination,
        "reason": req.reason,
        "issue_date": str(date.today()),
        "request_id": req.id
    }

# --- GET Endpoints for Frontend ---
@router.get("/absent-requests")
async def get_absent_requests(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(AbsentRequest))
    return result.scalars().all()

@router.get("/temp-residences")
async def get_temp_residences(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(TempResidenceRegistration))
    return result.scalars().all()
