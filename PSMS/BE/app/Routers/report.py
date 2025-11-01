# app/routers/reports.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..deps import require_permission
from datetime import date

router = APIRouter(tags=["reports"])

@router.get("/api/report/population_by_gender")
def pop_by_gender(db: Session = Depends(get_db), _perm = Depends(require_permission("report.statistics"))):
    res = db.execute("SELECT gender, COUNT(*) as cnt FROM persons GROUP BY gender").fetchall()
    return [{"gender": r[0], "count": r[1]} for r in res]

@router.get("/api/report/complaints_by_status")
def complaints_by_status(db: Session = Depends(get_db), _perm = Depends(require_permission("report.statistics"))):
    res = db.execute("SELECT status, COUNT(*) FROM complaints GROUP BY status").fetchall()
    return [{"status": r[0], "count": r[1]} for r in res]
