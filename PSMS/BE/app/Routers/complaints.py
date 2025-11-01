# app/routers/complaints.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..db import get_db
from .. import models
from ..Schemas import ComplaintCreate, ComplaintOut
from ..deps import get_current_user, require_permission

router = APIRouter(tags=["complaints"])

@router.post("/api/complaints")
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    content_norm = payload.content.strip().lower()
    existing = db.query(models.Complaint).filter(func.lower(models.Complaint.content)==content_norm).first()
    if existing:
        existing.duplicates_count = (existing.duplicates_count or 1) + 1
        db.add(existing)
        cr = models.ComplaintReport(complaint_id=existing.id, reporter_person_id=payload.reporter_person_id)
        db.add(cr)
        db.commit()
        return {"complaint_id": existing.id, "note": "merged as duplicate"}
    else:
        c = models.Complaint(reporter_person_id=payload.reporter_person_id, content=payload.content, category=payload.category, created_by=current_user.id)
        db.add(c)
        db.flush()
        cr = models.ComplaintReport(complaint_id=c.id, reporter_person_id=payload.reporter_person_id)
        db.add(cr)
        db.commit()
        return {"complaint_id": c.id}

@router.get("/api/complaints", response_model=list[ComplaintOut])
def list_complaints(skip:int=0, limit:int=100, db: Session=Depends(get_db), _perm = Depends(require_permission("complaint.view"))):
    items = db.query(models.Complaint).offset(skip).limit(limit).all()
    return items

@router.put("/api/complaints/{cid}/status")
def update_status(cid: int, status: str, db: Session = Depends(get_db), _perm = Depends(require_permission("complaint.update_status")), current_user=Depends(get_current_user)):
    c = db.query(models.Complaint).get(cid)
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    c.status = status
    db.add(c)
    db.commit()
    # optional: create Notification to reporter
    if c.reporter_person_id:
        # find user id from person? skipping mapping — you can implement relation person->user if needed
        pass
    return {"status":"ok"}
