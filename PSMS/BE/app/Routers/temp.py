from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..Schemas import (
    TempAbsenceCreate,
    TempResidenceCreate,
    TempAbsenceOut,
    TempResidenceOut,
    TempRecordStatusUpdate,
)
from ..deps import require_permission, get_current_user

router = APIRouter(tags=["temp"])


def _parse_status(value: str) -> models.StatusEnum:
    try:
        return models.StatusEnum(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status value")


def _validate_dates(from_date, to_date):
    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date must be before to_date")


@router.post("/api/temp_absences", response_model=TempAbsenceOut)
def create_temp_absence(
    payload: TempAbsenceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("temp_absence.create")),
):
    _validate_dates(payload.from_date, payload.to_date)
    ta = models.TempAbsence(
        person_id=payload.person_id,
        from_date=payload.from_date,
        to_date=payload.to_date,
        reason=payload.reason,
        registered_by=current_user.id,
        status=models.StatusEnum.NEW,
    )
    db.add(ta)
    db.commit()
    db.refresh(ta)
    return ta


@router.get("/api/temp_absences", response_model=list[TempAbsenceOut])
def list_temp_absences(
    status: str | None = Query(None),
    person_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("temp_absence.view")),
):
    q = db.query(models.TempAbsence)
    if status:
        q = q.filter(models.TempAbsence.status == _parse_status(status))
    if person_id:
        q = q.filter(models.TempAbsence.person_id == person_id)
    if start_date:
        q = q.filter(models.TempAbsence.from_date >= start_date)
    if end_date:
        q = q.filter(models.TempAbsence.to_date <= end_date)
    return q.order_by(models.TempAbsence.created_at.desc()).offset(skip).limit(limit).all()


@router.put("/api/temp_absences/{record_id}/status", response_model=TempAbsenceOut)
def update_temp_absence_status(
    record_id: int,
    payload: TempRecordStatusUpdate,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("temp_absence.approve")),
    current_user=Depends(get_current_user),
):
    ta = db.query(models.TempAbsence).get(record_id)
    if not ta:
        raise HTTPException(status_code=404, detail="Record not found")
    new_status = _parse_status(payload.status)
    ta.status = new_status
    if new_status == models.StatusEnum.RESOLVED:
        ta.approved_by = current_user.id
        ta.approved_at = datetime.utcnow()
    ta.updated_at = datetime.utcnow()
    db.add(ta)
    db.commit()
    db.refresh(ta)
    return ta


@router.post("/api/temp_residences", response_model=TempResidenceOut)
def create_temp_residence(
    payload: TempResidenceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("temp_residence.create")),
):
    _validate_dates(payload.from_date, payload.to_date)
    tr = models.TempResidence(
        person_id=payload.person_id,
        from_date=payload.from_date,
        to_date=payload.to_date,
        reason=payload.reason,
        host_household_id=payload.host_household_id,
        registered_by=current_user.id,
        status=models.StatusEnum.NEW,
    )
    db.add(tr)
    db.commit()
    db.refresh(tr)
    return tr


@router.get("/api/temp_residences", response_model=list[TempResidenceOut])
def list_temp_residences(
    status: str | None = Query(None),
    person_id: int | None = None,
    host_household_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("temp_residence.view")),
):
    q = db.query(models.TempResidence)
    if status:
        q = q.filter(models.TempResidence.status == _parse_status(status))
    if person_id:
        q = q.filter(models.TempResidence.person_id == person_id)
    if host_household_id:
        q = q.filter(models.TempResidence.host_household_id == host_household_id)
    return q.order_by(models.TempResidence.registered_at.desc()).offset(skip).limit(limit).all()


@router.put("/api/temp_residences/{record_id}/status", response_model=TempResidenceOut)
def update_temp_residence_status(
    record_id: int,
    payload: TempRecordStatusUpdate,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("temp_residence.approve")),
    current_user=Depends(get_current_user),
):
    tr = db.query(models.TempResidence).get(record_id)
    if not tr:
        raise HTTPException(status_code=404, detail="Record not found")
    new_status = _parse_status(payload.status)
    tr.status = new_status
    if new_status == models.StatusEnum.RESOLVED:
        tr.approved_by = current_user.id
        tr.approved_at = datetime.utcnow()
    tr.updated_at = datetime.utcnow()
    db.add(tr)
    db.commit()
    db.refresh(tr)
    return tr
