from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from pydantic import BaseModel
from typing import List, Optional
import json

from app.database import get_db
from app.core.security import get_current_user, PermissionChecker
from app.models.residence_models import Household, Resident, ChangeHistory, ChangeType, Gender
from app.models.auth_models import User

router = APIRouter(prefix="/households", tags=["Households"])

class HouseholdBase(BaseModel):
    household_code: str
    owner_id: int
    address: str

class HouseholdCreate(HouseholdBase):
    pass

class HouseholdResponse(HouseholdBase):
    id: int
    class Config:
        orm_mode = True

class SplitHouseholdRequest(BaseModel):
    old_household_id: int
    new_owner_id: int
    moving_resident_ids: List[int] # Includes new_owner_id
    new_address: str
    new_household_code: str
    replacement_owner_id: Optional[int] = None # Required if new_owner was old owner


@router.post("/", response_model=HouseholdResponse, dependencies=[Depends(PermissionChecker("household.create"))])
async def create_household(household: HouseholdCreate, db: AsyncSession = Depends(get_db)):
    # Verify owner exists
    owner = await db.get(Resident, household.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner resident not found")
        
    # Check distinct code
    existing = await db.execute(select(Household).where(Household.household_code == household.household_code))
    if existing.scalars().first():
         raise HTTPException(status_code=400, detail="Household code already exists")
    
    new_hh = Household(**household.dict())
    db.add(new_hh)
    await db.commit()
    await db.refresh(new_hh)
    
    # Update owner's household_id and relation
    owner.household_id = new_hh.id
    owner.relation_to_owner = "HEAD"
    db.add(owner)
    await db.commit()
    
    return new_hh

@router.get("/", dependencies=[Depends(PermissionChecker("household.view"))])
async def list_households(
    page: int = 1, 
    limit: int = 10, 
    search: Optional[str] = None, 
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import func as sql_func
    
    # Build base query
    query = select(Household).where(Household.deleted_at.is_(None))
    if search:
        query = query.where(
            Household.household_code.ilike(f"%{search}%") | 
            Household.address.ilike(f"%{search}%")
        )
    
    # Get total count
    count_query = select(sql_func.count()).select_from(Household).where(Household.deleted_at.is_(None))
    if search:
        count_query = count_query.where(
            Household.household_code.ilike(f"%{search}%") | 
            Household.address.ilike(f"%{search}%")
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
    households = result.scalars().all()
    
    # Build response with owner_name and resident_count
    items = []
    for h in households:
        # Get owner name
        owner_name = None
        if h.owner_id:
            owner = await db.get(Resident, h.owner_id)
            if owner:
                owner_name = owner.full_name
        
        # Get resident count
        count_result = await db.execute(
            select(sql_func.count()).select_from(Resident).where(Resident.household_id == h.id)
        )
        resident_count = count_result.scalar() or 0
        
        items.append({
            "id": h.id,
            "household_code": h.household_code,
            "owner_id": h.owner_id,
            "owner_name": owner_name,
            "address": h.address,
            "resident_count": resident_count
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": total_pages,
        "limit": limit
    }

@router.post("/split", dependencies=[Depends(PermissionChecker("household.split"))])
async def split_household(req: SplitHouseholdRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Start Transaction implicitly via db session
    async with db.begin():
        # 1. Fetch Old Household
        result = await db.execute(select(Household).where(Household.id == req.old_household_id))
        old_household = result.scalars().first()
        if not old_household:
            raise HTTPException(status_code=404, detail="Old household not found")

        # 2. Critical Check: Is new_owner_id currently the owner of old_household_id?
        if old_household.owner_id == req.new_owner_id:
            if not req.replacement_owner_id:
                raise HTTPException(
                    status_code=400, 
                    detail="The person moving out is the current owner. You must specify a replacement_owner_id for the old household."
                )
            
            # Update Old Household Owner
            # Check if replacement is in the old household AND NOT moving out
            if req.replacement_owner_id in req.moving_resident_ids:
                 raise HTTPException(status_code=400, detail="Replacement owner cannot be moving out.")
            
            # Verify replacement exists and is in old household
            res_check = await db.execute(select(Resident).where(Resident.id == req.replacement_owner_id, Resident.household_id == req.old_household_id))
            replacement = res_check.scalars().first()
            if not replacement:
                 raise HTTPException(status_code=400, detail="Replacement owner not valid member of old household.")

            old_household.owner_id = req.replacement_owner_id
            
            # Update relation to owner for replacement? (Optional logic, but good practice)
            replacement.relation_to_owner = "HEAD"
            db.add(old_household)
            db.add(replacement)
            
            # Log change
            log_owner_change = ChangeHistory(
                household_id=old_household.id,
                resident_id=replacement.id,
                change_type=ChangeType.MOVED_IN, # Or internal change
                old_data={"owner_id": req.new_owner_id},
                new_data={"owner_id": replacement.id, "reason": "Old owner moved out"},
                changed_by=current_user.id
            )
            db.add(log_owner_change)

        # 3. Create New Household
        # Verify new owner is existing resident
        res_new_owner_check = await db.execute(select(Resident).where(Resident.id == req.new_owner_id))
        new_owner = res_new_owner_check.scalars().first()
        if not new_owner:
            raise HTTPException(status_code=404, detail="New owner not found")

        new_household = Household(
            household_code=req.new_household_code,
            owner_id=req.new_owner_id,
            address=req.new_address
        )
        db.add(new_household)
        await db.flush() # Get ID

        # 4. Update residents table
        # Fetch all moving residents
        for r_id in req.moving_resident_ids:
            res_result = await db.execute(select(Resident).where(Resident.id == r_id))
            resident = res_result.scalars().first()
            if not resident:
                continue # or raise error
            
            if resident.household_id != req.old_household_id:
                 raise HTTPException(status_code=400, detail=f"Resident {r_id} does not belong to the source household.")

            # Log history
            history = ChangeHistory(
                household_id=req.old_household_id,
                resident_id=resident.id,
                change_type=ChangeType.SPLIT, # Moving out from old
                old_data={"household_id": req.old_household_id},
                new_data={"household_id": new_household.id},
                changed_by=current_user.id
            )
            db.add(history)

            # Update resident
            resident.household_id = new_household.id
            if resident.id == req.new_owner_id:
                resident.relation_to_owner = "HEAD"
            else:
                resident.relation_to_owner = "MEMBER" # Reset relation, user can update later
            
            db.add(resident)
            
        await db.commit()
        return {"status": "success", "new_household_id": new_household.id}

@router.get("/{id}/history", dependencies=[Depends(PermissionChecker("household.view"))])
async def get_household_history(id: int, db: AsyncSession = Depends(get_db)):
    """Get change history of a household"""
    from sqlalchemy.orm import selectinload
    
    # Verify household exists
    household = await db.get(Household, id)
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")
    
    # Fetch history records
    result = await db.execute(
        select(ChangeHistory)
        .where(ChangeHistory.household_id == id)
        .order_by(ChangeHistory.changed_at.desc())
        .limit(50)
    )
    histories = result.scalars().all()
    
    # Format response
    history_items = []
    for h in histories:
        # Get resident name
        resident = await db.get(Resident, h.resident_id) if h.resident_id else None
        resident_name = resident.full_name if resident else "Unknown"
        
        # Get user who made the change
        from app.models.auth_models import User
        changer = await db.get(User, h.changed_by) if h.changed_by else None
        changer_name = changer.username if changer else "System"
        
        history_items.append({
            "id": h.id,
            "change_type": h.change_type.value if hasattr(h.change_type, 'value') else str(h.change_type),
            "resident_name": resident_name,
            "old_data": h.old_data,
            "new_data": h.new_data,
            "changed_by": changer_name,
            "created_at": h.changed_at.isoformat() if h.changed_at else None
        })
    
    return {
        "household_id": id,
        "household_code": household.household_code,
        "history": history_items
    }

