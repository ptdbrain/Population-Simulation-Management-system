# app/routers/temp.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models
from ..Schemas import TempAbsenceCreate, TempResidenceCreate
from ..deps import require_permission, get_current_user

router = APIRouter(tags=["temp"])

@router.post("/api/temp_absences")
def create_temp_absence(payload: TempAbsenceCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # citizen or leader can create
    ta = models.TempAbsence(person_id=payload.person_id, from_date=payload.from_date, to_date=payload.to_date, reason=payload.reason, registered_by=current_user.id)
    db.add(ta)
    db.commit()
    db.refresh(ta)
    return {"id": ta.id, "status": ta.status}

@router.post("/api/temp_absences/{id}/approve")
def approve_temp_absence(id: int, db: Session = Depends(get_db), _perm = Depends(require_permission("temp_absence.approve")), current_user=Depends(get_current_user)):
    ta = db.query(models.TempAbsence).get(id)
    if not ta:
        raise HTTPException(status_code=404, detail="Not found")
    ta.status = "approved"
    db.add(ta)
    db.commit()
    return {"status": "ok"}

@router.post("/api/temp_residences")
def create_temp_res(payload: TempResidenceCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    tr = models.TempResidence(person_id=payload.person_id, from_date=payload.from_date, to_date=payload.to_date,
                              host_household_id=payload.host_household_id, reason=payload.reason, registered_by=current_user.id)
    db.add(tr)
    db.commit()
    db.refresh(tr)
    return {"id": tr.id, "status": tr.status}

@router.post("/api/temp_residences/{id}/approve")
def approve_temp_res(id: int, db: Session = Depends(get_db), _perm = Depends(require_permission("temp_residence.approve")), current_user=Depends(get_current_user)):
    tr = db.query(models.TempResidence).get(id)
    if not tr:
        raise HTTPException(status_code=404, detail="Not found")
    tr.status = "approved"
    db.add(tr)
    db.commit()
    return {"status": "ok"}
