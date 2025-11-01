# app/routers/households.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..db import get_db
from .. import models
from ..Schemas import HouseholdCreate, HouseholdOut, HouseholdSplit
from ..deps import require_permission, get_current_user

router = APIRouter(tags=["households"])

@router.post("/api/households", response_model=HouseholdOut)
def create_household(payload: HouseholdCreate, db: Session = Depends(get_db), _perm = Depends(require_permission("household.create"))):
    if db.query(models.Household).filter(models.Household.household_number == payload.household_number).first():
        raise HTTPException(status_code=400, detail="Household number exists")
    h = models.Household(household_number=payload.household_number, address=payload.address)
    db.add(h)
    db.commit()
    db.refresh(h)
    return h

@router.get("/api/households", response_model=List[HouseholdOut])
def list_households(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _perm = Depends(require_permission("household.view"))):
    items = db.query(models.Household).offset(skip).limit(limit).all()
    return items

@router.post("/api/households/{household_id}/split")
def split_household(household_id: int, payload: HouseholdSplit, db: Session = Depends(get_db),
                    _perm = Depends(require_permission("household.split")), current_user = Depends(get_current_user)):
    src = db.query(models.Household).get(household_id)
    if not src:
        raise HTTPException(status_code=404, detail="Source household not found")
    if db.query(models.Household).filter(models.Household.household_number==payload.new_household_number).first():
        raise HTTPException(status_code=400, detail="New household number already exists")
    # create new household and move members
    new_h = models.Household(household_number=payload.new_household_number, address=payload.address)
    db.add(new_h)
    db.flush()
    persons = db.query(models.Person).filter(models.Person.id.in_(payload.member_ids), models.Person.current_household_id==household_id).all() # 
     
    if len(persons) != len(payload.member_ids):
        db.rollback()
        raise HTTPException(status_code=400, detail="Some members do not belong to source household")
    for p in persons:
        old = p.current_household_id
        p.current_household_id = new_h.id
        db.add(p)
        hist = models.PersonHistory(person_id=p.id, action="house_split", from_household_id=old, to_household_id=new_h.id, performed_by=current_user.id, note=f"Split from {household_id}")
        db.add(hist)
    db.commit()
    return {"status": "ok", "new_household_id": new_h.id}
