from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, extract
from app.database import get_db
from app.core.security import PermissionChecker
from app.models.residence_models import Resident, Gender, Household
from app.models.complaint_models import Complaint, ComplaintStatus
from app.models.temp_models import AbsentRequest, TempResidenceRegistration

router = APIRouter(prefix="/stats", tags=["Stats"])

@router.get("/summary")
async def get_summary_stats(db: AsyncSession = Depends(get_db)):
    """Get summary counts for dashboard KPI cards"""
    household_count = await db.scalar(select(func.count(Household.id)))
    person_count = await db.scalar(select(func.count(Resident.id)))
    absent_count = await db.scalar(select(func.count(AbsentRequest.id)))
    complaint_count = await db.scalar(select(func.count(Complaint.id)).where(Complaint.status != ComplaintStatus.RESOLVED))
    temp_res_count = await db.scalar(select(func.count(TempResidenceRegistration.id)))
    
    return {
        "total_households": household_count or 0,
        "total_persons": person_count or 0,
        "total_absent": absent_count or 0,
        "total_temp_residence": temp_res_count or 0,
        "pending_complaints": complaint_count or 0
    }

@router.get("/population", dependencies=[Depends(PermissionChecker("report.statistics"))])
async def get_population_stats(db: AsyncSession = Depends(get_db)):
    from datetime import date
    
    # Gender Stats
    gender_stmt = select(Resident.gender, func.count(Resident.id)).group_by(Resident.gender)
    gender_res = await db.execute(gender_stmt)
    gender_data = dict(gender_res.all())
    
    # Age Groups - Fetch all DOBs and calculate
    dob_stmt = select(Resident.dob)
    dob_res = await db.execute(dob_stmt)
    dobs = dob_res.scalars().all()
    
    today = date.today()
    age_groups = {"0-14": 0, "15-59": 0, "60+": 0}
    
    for dob in dobs:
        if dob:
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age <= 14:
                age_groups["0-14"] += 1
            elif age <= 59:
                age_groups["15-59"] += 1
            else:
                age_groups["60+"] += 1
    
    return {
        "gender_distribution": gender_data,
        "age_distribution": age_groups
    }

@router.get("/complaints-quarterly", dependencies=[Depends(PermissionChecker("report.statistics"))])
async def get_complaint_stats(year: int = None, db: AsyncSession = Depends(get_db)):
    from datetime import date
    if year is None:
        year = date.today().year
    
    # Group by Quarter and Status
    stmt = select(
        extract('quarter', Complaint.created_at).label('quarter'),
        Complaint.status,
        func.count(Complaint.id)
    ).where(extract('year', Complaint.created_at) == year)\
    .group_by('quarter', Complaint.status)
    
    result = await db.execute(stmt)
    
    # Return as array format for Chart.js
    data_list = []
    for q, s, c in result.all():
        data_list.append({
            "quarter": f"Q{int(q)}",
            "status": s.value if hasattr(s, 'value') else str(s),
            "count": c
        })
        
    return data_list
