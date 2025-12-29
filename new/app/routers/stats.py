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

@router.get("/temp-status", dependencies=[Depends(PermissionChecker("report.statistics"))])
async def get_temp_status_stats(db: AsyncSession = Depends(get_db)):
    """Statistics for temporary absence and residence"""
    from datetime import date
    from app.models.temp_models import RequestStatus
    
    today = date.today()
    
    # Absent requests by status
    absent_pending = await db.scalar(
        select(func.count(AbsentRequest.id)).where(AbsentRequest.status == RequestStatus.PENDING)
    )
    absent_approved = await db.scalar(
        select(func.count(AbsentRequest.id)).where(AbsentRequest.status == RequestStatus.APPROVED)
    )
    
    # Temp residence by status
    temp_pending = await db.scalar(
        select(func.count(TempResidenceRegistration.id)).where(TempResidenceRegistration.status == RequestStatus.PENDING)
    )
    temp_approved = await db.scalar(
        select(func.count(TempResidenceRegistration.id)).where(TempResidenceRegistration.status == RequestStatus.APPROVED)
    )
    
    # Active today (within date range)
    from sqlalchemy import and_
    
    active_absent = await db.scalar(
        select(func.count(AbsentRequest.id)).where(
            and_(
                AbsentRequest.status == RequestStatus.APPROVED,
                AbsentRequest.start_date <= today,
                AbsentRequest.end_date >= today
            )
        )
    )
    
    active_temp_res = await db.scalar(
        select(func.count(TempResidenceRegistration.id)).where(
            and_(
                TempResidenceRegistration.status == RequestStatus.APPROVED,
                TempResidenceRegistration.start_date <= today,
                TempResidenceRegistration.end_date >= today
            )
        )
    )
    
    return {
        "absent": {
            "pending": absent_pending or 0,
            "approved": absent_approved or 0,
            "active_today": active_absent or 0
        },
        "temp_residence": {
            "pending": temp_pending or 0,
            "approved": temp_approved or 0,
            "active_today": active_temp_res or 0
        }
    }

@router.get("/search")
async def global_search(q: str, db: AsyncSession = Depends(get_db)):
    """Global search across persons and households"""
    from sqlalchemy import or_
    
    results = {
        "persons": [],
        "households": []
    }
    
    if not q or len(q) < 2:
        return results
    
    search_term = f"%{q}%"
    
    # Search persons
    persons_stmt = select(Resident).where(
        or_(
            Resident.full_name.ilike(search_term),
            Resident.cid.ilike(search_term)
        )
    ).limit(10)
    persons_res = await db.execute(persons_stmt)
    for p in persons_res.scalars().all():
        results["persons"].append({
            "id": p.id,
            "full_name": p.full_name,
            "cid": p.cid,
            "household_id": p.household_id
        })
    
    # Search households
    households_stmt = select(Household).where(
        or_(
            Household.household_code.ilike(search_term),
            Household.address.ilike(search_term)
        )
    ).limit(10)
    hh_res = await db.execute(households_stmt)
    for h in hh_res.scalars().all():
        results["households"].append({
            "id": h.id,
            "household_code": h.household_code,
            "address": h.address
        })
    
    return results

