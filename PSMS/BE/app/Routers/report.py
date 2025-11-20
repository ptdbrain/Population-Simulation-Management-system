from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, text
from sqlalchemy.orm import Session

from .. import models
from ..Schemas import (
    PopulationSummary,
    AgeDistributionItem,
    TempRecordStatsOut,
    ComplaintStatsOut,
)
from ..db import get_db
from ..deps import require_permission

router = APIRouter(tags=["reports"])


@router.get("/api/report/population_summary", response_model=PopulationSummary)
def population_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("report.population")),
):
    total_households = db.query(func.count(models.Household.id)).scalar() or 0

    person_query = db.query(models.Person)
    if start_date:
        person_query = person_query.filter(models.Person.created_at >= start_date)
    if end_date:
        person_query = person_query.filter(models.Person.created_at <= end_date)
    total_persons = person_query.count()

    gender_rows = (
        db.query(models.Person.gender, func.count(models.Person.id))
        .group_by(models.Person.gender)
        .all()
    )
    by_gender = [
        {
            "gender": g.value if isinstance(g, models.GenderEnum) else g,
            "count": cnt,
        }
        for g, cnt in gender_rows
    ]

    temp_absence_pending = (
        db.query(func.count(models.TempAbsence.id))
        .filter(models.TempAbsence.status == models.StatusEnum.PENDING)
        .scalar()
        or 0
    )
    temp_residence_pending = (
        db.query(func.count(models.TempResidence.id))
        .filter(models.TempResidence.status == models.StatusEnum.PENDING)
        .scalar()
        or 0
    )
    complaints_pending = (
        db.query(func.count(models.Complaint.id))
        .filter(models.Complaint.status == models.StatusEnum.PENDING)
        .scalar()
        or 0
    )

    return PopulationSummary(
        total_households=total_households,
        total_persons=total_persons,
        by_gender=by_gender,
        temp_absence_pending=temp_absence_pending,
        temp_residence_pending=temp_residence_pending,
        complaints_pending=complaints_pending,
    )


@router.get("/api/report/age_distribution", response_model=List[AgeDistributionItem])
def age_distribution(
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("report.population")),
):
    age_expr = func.timestampdiff(text("YEAR"), models.Person.birthdate, func.curdate())
    age_group = case(
        (age_expr < 18, "0-17"),
        (age_expr.between(18, 35), "18-35"),
        (age_expr.between(36, 55), "36-55"),
        (age_expr.between(56, 75), "56-75"),
        else_="75+",
    )
    rows = db.query(age_group.label("age_group"), func.count(models.Person.id)).group_by("age_group").all()
    return [AgeDistributionItem(age_group=row.age_group, count=row[1]) for row in rows]


@router.get("/api/report/temp_stats", response_model=List[TempRecordStatsOut])
def temp_stats(
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("report.temp")),
):
    results: List[TempRecordStatsOut] = []
    for model, record_type in [(models.TempAbsence, "absence"), (models.TempResidence, "residence")]:
        rows = (
            db.query(model.status, func.count(model.id).label("count"))
            .group_by(model.status)
            .all()
        )
        for status, count in rows:
            label = status.value if isinstance(status, models.StatusEnum) else status
            results.append(TempRecordStatsOut(record_type=record_type, status=label, count=count))
    return results


@router.get("/api/report/complaints_by_status", response_model=List[ComplaintStatsOut])
def complaints_by_status(
    db: Session = Depends(get_db),
    _perm=Depends(require_permission("report.complaints")),
):
    rows = db.query(models.Complaint.status, func.count(models.Complaint.id)).group_by(models.Complaint.status).all()
    return [
        ComplaintStatsOut(
            status=status.value if isinstance(status, models.StatusEnum) else status,
            count=count,
        )
        for status, count in rows
    ]
