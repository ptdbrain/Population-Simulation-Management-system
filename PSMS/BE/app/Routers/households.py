# app/routers/households.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from ..db import get_db
from .. import models
from ..Schemas import (
    HouseholdCreate,
    HouseholdOut,
    HouseholdSplit,
    HouseholdDetail,
    PersonOut,
    PersonHistoryOut,
)
from ..deps import require_permission, get_current_user

router = APIRouter(tags=["households"])


@router.post("/api/households", response_model=HouseholdOut)
def create_household(
    payload: HouseholdCreate,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("household.create")),
):
    if (
        db.query(models.Household)
        .filter(models.Household.household_number == payload.household_number)
        .first()
    ):
        raise HTTPException(status_code=400, detail="Household number exists")
    h = models.Household(
        household_number=payload.household_number,
        address=payload.address,
        head_person_id=payload.head_person_id,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


@router.get("/api/households", response_model=List[HouseholdOut])
def list_households(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("household.view")),
):
    return db.query(models.Household).offset(skip).limit(limit).all()


@router.get("/api/households/search", response_model=List[HouseholdOut])
def search_households(
    keyword: str = Query(..., min_length=2),
    limit: int = 20,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("household.view")),
):
    q = db.query(models.Household).filter(
        or_(
            models.Household.household_number.ilike(f"%{keyword}%"),
            models.Household.address.ilike(f"%{keyword}%"),
        )
    )
    return q.limit(limit).all()


@router.get("/api/households/{household_id}", response_model=HouseholdDetail)
def get_household(
    household_id: int,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("household.view")),
):
    h = db.query(models.Household).get(household_id)
    if not h:
        raise HTTPException(status_code=404, detail="Household not found")
    members = (
        db.query(models.Person)
        .filter(models.Person.current_household_id == household_id)
        .all()
    )
    return HouseholdDetail(
        id=h.id,
        household_number=h.household_number,
        address=h.address,
        head_person_id=h.head_person_id,
        created_at=h.created_at,
        members=members,
    )


@router.get("/api/households/{household_id}/members", response_model=List[PersonOut])
def get_household_members(
    household_id: int,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("household.view")),
):
    return (
        db.query(models.Person)
        .filter(models.Person.current_household_id == household_id)
        .all()
    )


@router.get("/api/households/{household_id}/history", response_model=List[PersonHistoryOut])
def household_history(
    household_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("household.view")),
):
    hist = (
        db.query(models.PersonHistory)
        .filter(
            (models.PersonHistory.from_household_id == household_id)
            | (models.PersonHistory.to_household_id == household_id)
        )
        .order_by(models.PersonHistory.performed_at.desc())
        .limit(limit)
        .all()
    )
    return hist


@router.post("/api/households/{household_id}/split")
def split_household(
    household_id: int,
    payload: HouseholdSplit,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("household.split")),
    current_user=Depends(get_current_user),
):
    src = db.query(models.Household).get(household_id)
    if not src:
        raise HTTPException(status_code=404, detail="Source household not found")
    if (
        db.query(models.Household)
        .filter(models.Household.household_number == payload.new_household_number)
        .first()
    ):
        raise HTTPException(status_code=400, detail="New household number already exists")
    if not payload.member_ids:
        raise HTTPException(status_code=400, detail="Select at least one member")
    new_h = models.Household(household_number=payload.new_household_number, address=payload.address)
    db.add(new_h)
    db.flush()
    persons = (
        db.query(models.Person)
        .filter(
            models.Person.id.in_(payload.member_ids),
            models.Person.current_household_id == household_id,
        )
        .all()
    )
    if len(persons) != len(payload.member_ids):
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Some members do not belong to source household"
        )
    head_person_id = payload.head_person_id or (persons[0].id if persons else None)
    if head_person_id and head_person_id not in [p.id for p in persons]:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Head person must be inside selected members"
        )
    if head_person_id:
        new_h.head_person_id = head_person_id
    for p in persons:
        old = p.current_household_id
        p.current_household_id = new_h.id
        db.add(p)
        hist = models.PersonHistory(
            person_id=p.id,
            action="house_split",
            from_household_id=old,
            to_household_id=new_h.id,
            performed_by=current_user.id,
            note=f"Split from {household_id}",
        )
        db.add(hist)
    if src.head_person_id in payload.member_ids:
        src.head_person_id = None
        db.add(src)
    db.commit()
    return {"status": "ok", "new_household_id": new_h.id}
