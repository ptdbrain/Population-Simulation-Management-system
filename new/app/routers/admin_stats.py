"""
Admin Statistics Router - Advanced statistics for admin users
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, extract, and_, case
from datetime import date, datetime, timedelta
from typing import Optional

from app.database import get_db
from app.core.security import PermissionChecker
from app.models.residence_models import Resident, Gender, Household, ResidentStatus, ChangeHistory, ChangeType
from app.models.complaint_models import Complaint, ComplaintStatus, ComplaintCategory
from app.models.temp_models import AbsentRequest, TempResidenceRegistration

router = APIRouter(prefix="/admin-stats", tags=["Admin Statistics"])

# Only admin can access these statistics
ADMIN_PERMISSION = Depends(PermissionChecker("report.statistics"))


@router.get("/population-trend", dependencies=[ADMIN_PERMISSION])
async def get_population_trend(
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get population trend by month for the selected year"""
    if year is None:
        year = date.today().year
    
    # Get all residents and count by month they were "active"
    # For simplicity, we'll count all current residents and show as static
    # In a real system, you'd track registration dates
    
    total_count = await db.scalar(select(func.count(Resident.id)))
    
    # Simulate monthly data (in production, you'd have created_at on Resident)
    months = []
    for month in range(1, 13):
        months.append({
            "month": month,
            "month_name": ["", "Th1", "Th2", "Th3", "Th4", "Th5", "Th6", 
                          "Th7", "Th8", "Th9", "Th10", "Th11", "Th12"][month],
            "count": total_count  # Static for now
        })
    
    return {
        "year": year,
        "data": months,
        "total": total_count
    }


@router.get("/household-size", dependencies=[ADMIN_PERMISSION])
async def get_household_size_distribution(db: AsyncSession = Depends(get_db)):
    """Get distribution of household sizes"""
    
    # Subquery to count residents per household
    subq = select(
        Resident.household_id,
        func.count(Resident.id).label('member_count')
    ).where(Resident.household_id.isnot(None)).group_by(Resident.household_id).subquery()
    
    # Get all household sizes
    result = await db.execute(
        select(subq.c.member_count, func.count().label('household_count'))
        .group_by(subq.c.member_count)
        .order_by(subq.c.member_count)
    )
    
    size_data = result.all()
    
    # Group into categories
    categories = {
        "1-2 người": 0,
        "3-4 người": 0,
        "5+ người": 0
    }
    
    for member_count, household_count in size_data:
        if member_count <= 2:
            categories["1-2 người"] += household_count
        elif member_count <= 4:
            categories["3-4 người"] += household_count
        else:
            categories["5+ người"] += household_count
    
    # Also count empty households
    empty_count = await db.scalar(
        select(func.count(Household.id)).where(
            and_(
                Household.deleted_at.is_(None),
                ~Household.id.in_(
                    select(Resident.household_id).where(Resident.household_id.isnot(None))
                )
            )
        )
    )
    
    return {
        "distribution": categories,
        "empty_households": empty_count or 0,
        "raw_data": [{"size": mc, "count": hc} for mc, hc in size_data]
    }


@router.get("/resident-status", dependencies=[ADMIN_PERMISSION])
async def get_resident_status_distribution(db: AsyncSession = Depends(get_db)):
    """Get distribution of residents by status"""
    
    stmt = select(
        Resident.status,
        func.count(Resident.id)
    ).group_by(Resident.status)
    
    result = await db.execute(stmt)
    data = result.all()
    
    status_labels = {
        "PERMANENT": "Thường trú",
        "TEMPORARY_ABSENT": "Tạm vắng",
        "TEMPORARY_RESIDENT": "Tạm trú",
        "MOVED_OUT": "Đã chuyển đi"
    }
    
    distribution = {}
    for status, count in data:
        status_key = status.value if hasattr(status, 'value') else str(status)
        distribution[status_labels.get(status_key, status_key)] = count
    
    return {"distribution": distribution}


@router.get("/resident-relation", dependencies=[ADMIN_PERMISSION])
async def get_resident_relation_distribution(db: AsyncSession = Depends(get_db)):
    """Get distribution of residents by relation to household owner"""
    
    stmt = select(
        Resident.relation_to_owner,
        func.count(Resident.id)
    ).group_by(Resident.relation_to_owner)
    
    result = await db.execute(stmt)
    data = result.all()
    
    relation_labels = {
        "HEAD": "Chủ hộ",
        "WIFE": "Vợ",
        "HUSBAND": "Chồng",
        "SON": "Con trai",
        "DAUGHTER": "Con gái",
        "PARENT": "Bố/Mẹ",
        "GRANDPARENT": "Ông/Bà",
        "SIBLING": "Anh/Chị/Em",
        "MEMBER": "Thành viên",
        None: "Chưa xác định"
    }
    
    distribution = {}
    for relation, count in data:
        label = relation_labels.get(relation, relation or "Khác")
        distribution[label] = count
    
    return {"distribution": distribution}


@router.get("/complaints-category", dependencies=[ADMIN_PERMISSION])
async def get_complaints_by_category(
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get complaints distribution by category"""
    if year is None:
        year = date.today().year
    
    stmt = select(
        Complaint.category,
        func.count(Complaint.id)
    ).where(
        extract('year', Complaint.created_at) == year
    ).group_by(Complaint.category)
    
    result = await db.execute(stmt)
    data = result.all()
    
    category_labels = {
        "SECURITY": "An ninh & An toàn",
        "HYGIENE": "Vệ sinh & Môi trường",
        "INFRASTRUCTURE": "Cơ sở hạ tầng"
    }
    
    distribution = {}
    for category, count in data:
        cat_key = category.value if hasattr(category, 'value') else str(category)
        distribution[category_labels.get(cat_key, cat_key)] = count
    
    # Also get status breakdown per category
    status_stmt = select(
        Complaint.category,
        Complaint.status,
        func.count(Complaint.id)
    ).where(
        extract('year', Complaint.created_at) == year
    ).group_by(Complaint.category, Complaint.status)
    
    status_result = await db.execute(status_stmt)
    status_data = status_result.all()
    
    breakdown = {}
    for category, status, count in status_data:
        cat_key = category.value if hasattr(category, 'value') else str(category)
        cat_label = category_labels.get(cat_key, cat_key)
        status_key = status.value if hasattr(status, 'value') else str(status)
        
        if cat_label not in breakdown:
            breakdown[cat_label] = {"NEW": 0, "PROCESSING": 0, "RESOLVED": 0}
        breakdown[cat_label][status_key] = count
    
    return {
        "year": year,
        "distribution": distribution,
        "status_breakdown": breakdown
    }


@router.get("/complaints-resolution", dependencies=[ADMIN_PERMISSION])
async def get_complaints_resolution_stats(
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get complaints resolution statistics"""
    if year is None:
        year = date.today().year
    
    # Total complaints
    total = await db.scalar(
        select(func.count(Complaint.id)).where(
            extract('year', Complaint.created_at) == year
        )
    )
    
    # Resolved complaints
    resolved = await db.scalar(
        select(func.count(Complaint.id)).where(
            and_(
                extract('year', Complaint.created_at) == year,
                Complaint.status == ComplaintStatus.RESOLVED
            )
        )
    )
    
    # Processing complaints
    processing = await db.scalar(
        select(func.count(Complaint.id)).where(
            and_(
                extract('year', Complaint.created_at) == year,
                Complaint.status == ComplaintStatus.PROCESSING
            )
        )
    )
    
    # New complaints
    new_count = await db.scalar(
        select(func.count(Complaint.id)).where(
            and_(
                extract('year', Complaint.created_at) == year,
                Complaint.status == ComplaintStatus.NEW
            )
        )
    )
    
    resolution_rate = (resolved / total * 100) if total > 0 else 0
    
    return {
        "year": year,
        "total": total or 0,
        "resolved": resolved or 0,
        "processing": processing or 0,
        "new": new_count or 0,
        "resolution_rate": round(resolution_rate, 1)
    }


@router.get("/change-history", dependencies=[ADMIN_PERMISSION])
async def get_change_history_stats(
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get statistics on household/resident changes"""
    if year is None:
        year = date.today().year
    
    # Count by change type
    stmt = select(
        ChangeHistory.change_type,
        func.count(ChangeHistory.id)
    ).where(
        extract('year', ChangeHistory.changed_at) == year
    ).group_by(ChangeHistory.change_type)
    
    result = await db.execute(stmt)
    data = result.all()
    
    type_labels = {
        "SPLIT": "Tách hộ",
        "MOVED_IN": "Nhập hộ",
        "MOVED_OUT": "Rời hộ"
    }
    
    distribution = {}
    for change_type, count in data:
        type_key = change_type.value if hasattr(change_type, 'value') else str(change_type)
        distribution[type_labels.get(type_key, type_key)] = count
    
    # Get monthly breakdown
    monthly_stmt = select(
        extract('month', ChangeHistory.changed_at).label('month'),
        func.count(ChangeHistory.id)
    ).where(
        extract('year', ChangeHistory.changed_at) == year
    ).group_by('month').order_by('month')
    
    monthly_result = await db.execute(monthly_stmt)
    monthly_data = monthly_result.all()
    
    monthly = {int(month): count for month, count in monthly_data}
    
    return {
        "year": year,
        "by_type": distribution,
        "monthly": monthly,
        "total": sum(distribution.values())
    }


@router.get("/summary-advanced", dependencies=[ADMIN_PERMISSION])
async def get_advanced_summary(db: AsyncSession = Depends(get_db)):
    """Get advanced summary statistics for admin dashboard"""
    today = date.today()
    
    # Households with most members
    subq = select(
        Resident.household_id,
        func.count(Resident.id).label('member_count')
    ).where(Resident.household_id.isnot(None)).group_by(Resident.household_id).subquery()
    
    top_households_stmt = select(
        Household.household_code,
        Household.address,
        subq.c.member_count
    ).join(subq, Household.id == subq.c.household_id).order_by(
        subq.c.member_count.desc()
    ).limit(5)
    
    top_result = await db.execute(top_households_stmt)
    top_households = [
        {"code": code, "address": addr, "members": count}
        for code, addr, count in top_result.all()
    ]
    
    # Average household size
    avg_result = await db.execute(
        select(func.avg(subq.c.member_count))
    )
    avg_size = avg_result.scalar() or 0
    
    # Gender ratio
    male_count = await db.scalar(
        select(func.count(Resident.id)).where(Resident.gender == Gender.MALE)
    )
    female_count = await db.scalar(
        select(func.count(Resident.id)).where(Resident.gender == Gender.FEMALE)
    )
    
    gender_ratio = round(male_count / female_count, 2) if female_count > 0 else 0
    
    return {
        "top_households": top_households,
        "average_household_size": round(avg_size, 1),
        "gender_ratio": gender_ratio,
        "male_count": male_count or 0,
        "female_count": female_count or 0
    }
