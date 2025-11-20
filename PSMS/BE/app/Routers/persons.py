# app/routers/persons.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from ..db import get_db
from .. import models
from ..Schemas import PersonCreate, PersonOut, PersonHistoryOut
from ..deps import require_permission, get_current_user

router = APIRouter(tags=["persons"])

@router.post("/api/persons", response_model=PersonOut)
def create_person(payload: PersonCreate, db: Session = Depends(get_db), _perm = Depends(require_permission("person.create"))):
    p = models.Person(full_name=payload.full_name, 
                      birthdate=payload.birthdate, 
                      gender=payload.gender,
                      id_number=payload.id_number, 
                      current_household_id=payload.current_household_id,
                      relation_to_head=payload.relation_to_head) 
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@router.get("/api/persons", response_model=List[PersonOut])
def list_persons(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _perm = Depends(require_permission("person.view"))):
    items = db.query(models.Person).offset(skip).limit(limit).all()
    return items

@router.get("/api/persons/search", response_model=List[PersonOut])
def search_persons(
    keyword: str = Query(..., min_length=2),
    limit: int = 20,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("person.view")),
):
    q = (
        db.query(models.Person)
        .filter(
            or_(
                models.Person.full_name.ilike(f"%{keyword}%"),
                models.Person.id_number.ilike(f"%{keyword}%"),
            )
        )
        .limit(limit)
    )
    return q.all()

@router.get("/api/persons/{person_id}", response_model=PersonOut)
def get_person(person_id: int, db: Session = Depends(get_db), _perm = Depends(require_permission("person.view"))):
    p = db.query(models.Person).get(person_id)
    if not p:
        raise HTTPException(status_code=404, detail="Person not found")
    return p

@router.get("/api/persons/{person_id}/history", response_model=List[PersonHistoryOut])
def get_person_history(
    person_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("person.view")),
):
    return (
        db.query(models.PersonHistory)
        .filter(models.PersonHistory.person_id == person_id)
        .order_by(models.PersonHistory.performed_at.desc())
        .limit(limit)
        .all()
    )

@router.put("/api/persons/{person_id}")
def update_person(person_id: int, payload: PersonCreate, db: Session = Depends(get_db), _perm = Depends(require_permission("person.update")), current_user=Depends(get_current_user)):
    p = db.query(models.Person).get(person_id)
    if not p:
        raise HTTPException(status_code=404, detail="Person not found")
    p.full_name = payload.full_name
    p.birthdate = payload.birthdate
    p.gender = payload.gender
    p.id_number = payload.id_number
    p.current_household_id = payload.current_household_id
    p.relation_to_head = payload.relation_to_head
    db.add(p)
    db.commit()
    return {"status": "ok"}
