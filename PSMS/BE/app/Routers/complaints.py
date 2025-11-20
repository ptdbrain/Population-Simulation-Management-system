# app/routers/complaints.py
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db import get_db
from .. import models
from ..Schemas import (
    ComplaintCreate,
    ComplaintOut,
    ComplaintStatusUpdate,
    ComplaintReportOut,
    QuarterlyComplaintStats,
)
from ..deps import get_current_user, require_permission

router = APIRouter(tags=["complaints"])

def _parse_status(value: Optional[str]) -> Optional[models.StatusEnum]:
    if value is None:
        return None
    try:
        return models.StatusEnum(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status value")


@router.post("/api/complaints", response_model=ComplaintOut)
def create_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _perm=Depends(require_permission("complaint.create")),
):
    if not payload.reporter_person_id:
        raise HTTPException(status_code=400, detail="Reporter person is required")
    content_norm = payload.content.strip().lower()
    existing = (
        db.query(models.Complaint)
        .filter(func.lower(models.Complaint.content) == content_norm, models.Complaint.category == payload.category)
        .first()
    )
    if existing:
        existing.duplicate_count = (existing.duplicate_count or 1) + 1
        db.add(existing)
        cr = models.ComplaintReport(complaint_id=existing.id, reporter_person_id=payload.reporter_person_id)
        db.add(cr)
        db.commit()
        db.refresh(existing)
        return existing

    c = models.Complaint(
        reporter_person_id=payload.reporter_person_id,
        content=payload.content,
        category=payload.category or "general",
        created_by=current_user.id,
        status=models.StatusEnum.NEW,
    )
    db.add(c)
    db.flush()
    cr = models.ComplaintReport(complaint_id=c.id, reporter_person_id=payload.reporter_person_id)
    db.add(cr)
    db.commit()
    db.refresh(c)
    return c


@router.get("/api/complaints", response_model=list[ComplaintOut])
def list_complaints(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    reporter_person_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("complaint.view")),
):
    q = db.query(models.Complaint)
    if status:
        status_enum = _parse_status(status)
        q = q.filter(models.Complaint.status == status_enum)
    if category:
        q = q.filter(models.Complaint.category == category)
    if keyword:
        like = f"%{keyword.lower()}%"
        q = q.filter(func.lower(models.Complaint.content).like(like))
    if reporter_person_id:
        q = q.filter(models.Complaint.reporter_person_id == reporter_person_id)
    if start_date:
        q = q.filter(models.Complaint.reported_at >= start_date)
    if end_date:
        q = q.filter(models.Complaint.reported_at <= end_date)
    items = q.order_by(models.Complaint.reported_at.desc()).offset(skip).limit(limit).all()
    return items

@router.put("/api/complaints/{cid}/status")
def update_status(
    cid: int,
    payload: ComplaintStatusUpdate,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("complaint.respond")),
    current_user=Depends(get_current_user),
):
    c = db.query(models.Complaint).get(cid)
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    new_status = _parse_status(payload.status)
    if new_status:
        c.status = new_status
    c.response_note = payload.response_note
    c.response_by = current_user.id
    c.response_at = datetime.utcnow()
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/api/complaints/{cid}/reports", response_model=List[ComplaintReportOut])
def list_complaint_reports(
    cid: int,
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("complaint.view")),
):
    complaint = db.query(models.Complaint).get(cid)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    reports = db.query(models.ComplaintReport).filter(models.ComplaintReport.complaint_id == cid).order_by(models.ComplaintReport.report_at.desc()).all()
    return reports

@router.get("/api/complaints/my", response_model=list[ComplaintOut])
def my_complaints(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return (
        db.query(models.Complaint)
        .filter(models.Complaint.created_by == current_user.id)
        .order_by(models.Complaint.reported_at.desc())
        .all()
    )


@router.get("/api/complaints/stats/quarterly", response_model=List[QuarterlyComplaintStats])
def complaint_quarterly_stats(
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("complaint.stats")),
):
    year_expr = func.extract("year", models.Complaint.created_at).label("year")
    quarter_expr = func.extract("quarter", models.Complaint.created_at).label("quarter")
    query = (
        db.query(
            year_expr,
            quarter_expr,
            models.Complaint.status,
            func.count(models.Complaint.id).label("count"),
        )
        .group_by(year_expr, quarter_expr, models.Complaint.status)
        .order_by(year_expr, quarter_expr)
    )
    if year:
        query = query.filter(func.extract("year", models.Complaint.created_at) == year)
    rows = query.all()
    return [
        QuarterlyComplaintStats(
            year=int(r.year),
            quarter=int(r.quarter),
            status=r.status.value if isinstance(r.status, models.StatusEnum) else r.status,
            count=r.count,
        )
        for r in rows
    ]
