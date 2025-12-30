from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, desc, func as sql_func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta

from app.database import get_db
from app.core.security import get_current_user
from app.models.reminder_models import ReminderRule, Reminder, RuleType, ReminderStatus
from app.models.auth_models import User, Role
from app.models.residence_models import Resident
from app.models.temp_models import TempResidenceRegistration, AbsentRequest

router = APIRouter(prefix="/reminders", tags=["Reminders"])


# Schemas
class ReminderRuleUpdate(BaseModel):
    days_before: Optional[int] = None
    is_active: Optional[bool] = None


class ReminderCreate(BaseModel):
    resident_id: int
    title: str
    message: str
    due_date: Optional[date] = None


class ReminderResponse(BaseModel):
    id: int
    title: str
    message: str
    due_date: Optional[date]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Helper: Ensure default rules exist
async def ensure_default_rules(db: AsyncSession):
    """Create default reminder rules if they don't exist"""
    default_rules = [
        {
            "rule_type": RuleType.CCCD_14,
            "name": "Nhắc làm CCCD lần đầu",
            "description": "Nhắc nhở trẻ em sắp đủ 14 tuổi cần làm CCCD",
            "days_before": 30
        },
        {
            "rule_type": RuleType.TEMP_RESIDENCE_EXPIRE,
            "name": "Tạm trú sắp hết hạn",
            "description": "Nhắc nhở người tạm trú sắp hết hạn đăng ký",
            "days_before": 15
        },
        {
            "rule_type": RuleType.TEMP_ABSENCE_LONG,
            "name": "Tạm vắng quá thời hạn",
            "description": "Cảnh báo khi tạm vắng quá 30 ngày",
            "days_before": 0
        },
        {
            "rule_type": RuleType.LIFE_EVENT,
            "name": "Cập nhật sự kiện cuộc sống",
            "description": "Nhắc cập nhật khi có sự kiện sinh, kết hôn...",
            "days_before": 0
        }
    ]
    
    for rule_data in default_rules:
        existing = await db.execute(
            select(ReminderRule).where(ReminderRule.rule_type == rule_data["rule_type"])
        )
        if not existing.scalar_one_or_none():
            rule = ReminderRule(**rule_data)
            db.add(rule)
    
    await db.commit()


# Endpoints

@router.get("/my")
async def get_my_reminders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách nhắc nhở của tôi."""
    if not current_user.resident_id:
        return []
    
    result = await db.execute(
        select(Reminder)
        .where(Reminder.resident_id == current_user.resident_id)
        .order_by(desc(Reminder.created_at))
    )
    reminders = result.scalars().all()
    
    return [{
        "id": r.id,
        "title": r.title,
        "message": r.message,
        "due_date": r.due_date.isoformat() if r.due_date else None,
        "status": r.status.value,
        "created_at": r.created_at.isoformat() if r.created_at else None
    } for r in reminders]


@router.put("/{id}/acknowledge")
async def acknowledge_reminder(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Đánh dấu đã xem nhắc nhở."""
    reminder = await db.get(Reminder, id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhắc nhở")
    
    if reminder.resident_id != current_user.resident_id:
        raise HTTPException(status_code=403, detail="Không có quyền")
    
    reminder.status = ReminderStatus.ACKNOWLEDGED
    reminder.acknowledged_at = datetime.now()
    db.add(reminder)
    await db.commit()
    
    return {"status": "success", "message": "Đã xác nhận đọc nhắc nhở"}


@router.get("/admin/rules")
async def get_reminder_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[Admin] Lấy danh sách quy tắc nhắc nhở."""
    # Check admin role
    role = await db.get(Role, current_user.role_id)
    if not role or role.name != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền")
    
    await ensure_default_rules(db)
    
    result = await db.execute(select(ReminderRule))
    rules = result.scalars().all()
    
    return [{
        "id": r.id,
        "rule_type": r.rule_type.value,
        "name": r.name,
        "description": r.description,
        "days_before": r.days_before,
        "is_active": r.is_active
    } for r in rules]


@router.put("/admin/rules/{id}")
async def update_reminder_rule(
    id: int,
    data: ReminderRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[Admin] Cập nhật quy tắc nhắc nhở."""
    role = await db.get(Role, current_user.role_id)
    if not role or role.name != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền")
    
    rule = await db.get(ReminderRule, id)
    if not rule:
        raise HTTPException(status_code=404, detail="Không tìm thấy quy tắc")
    
    if data.days_before is not None:
        rule.days_before = data.days_before
    if data.is_active is not None:
        rule.is_active = data.is_active
    
    db.add(rule)
    await db.commit()
    
    return {"status": "success", "message": "Đã cập nhật quy tắc"}


@router.post("/admin/generate")
async def generate_reminders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[Admin] Tạo nhắc nhở dựa trên quy tắc."""
    role = await db.get(Role, current_user.role_id)
    if not role or role.name != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền")
    
    await ensure_default_rules(db)
    
    created_count = 0
    today = date.today()
    
    # Get active rules
    rules_result = await db.execute(
        select(ReminderRule).where(ReminderRule.is_active == True)
    )
    rules = {r.rule_type: r for r in rules_result.scalars().all()}
    
    # 1. CCCD_14: Trẻ em sắp đủ 14 tuổi
    if RuleType.CCCD_14 in rules:
        rule = rules[RuleType.CCCD_14]
        target_date = today + timedelta(days=rule.days_before)
        cutoff_dob = target_date.replace(year=target_date.year - 14)
        
        result = await db.execute(
            select(Resident).where(
                and_(
                    Resident.dob != None,
                    Resident.dob <= cutoff_dob,
                    Resident.dob > cutoff_dob.replace(year=cutoff_dob.year - 1)
                )
            )
        )
        residents = result.scalars().all()
        
        for resident in residents:
            # Check if reminder already exists
            existing = await db.execute(
                select(Reminder).where(
                    and_(
                        Reminder.rule_id == rule.id,
                        Reminder.resident_id == resident.id,
                        Reminder.status.in_([ReminderStatus.PENDING, ReminderStatus.SENT])
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            birthday_14 = resident.dob.replace(year=resident.dob.year + 14)
            reminder = Reminder(
                rule_id=rule.id,
                resident_id=resident.id,
                title="Nhắc làm CCCD lần đầu",
                message=f"{resident.full_name} sắp đủ 14 tuổi ({birthday_14}). Cần làm CCCD lần đầu!",
                due_date=birthday_14,
                status=ReminderStatus.SENT,
                sent_at=datetime.now()
            )
            db.add(reminder)
            created_count += 1
    
    # 2. TEMP_RESIDENCE_EXPIRE: Tạm trú sắp hết hạn
    if RuleType.TEMP_RESIDENCE_EXPIRE in rules:
        rule = rules[RuleType.TEMP_RESIDENCE_EXPIRE]
        expiry_threshold = today + timedelta(days=rule.days_before)
        
        result = await db.execute(
            select(TempResidenceRegistration).where(
                and_(
                    TempResidenceRegistration.end_date != None,
                    TempResidenceRegistration.end_date <= expiry_threshold,
                    TempResidenceRegistration.end_date >= today,
                    TempResidenceRegistration.status == "APPROVED"
                )
            )
        )
        temp_residences = result.scalars().all()
        
        for tr in temp_residences:
            # Find resident by name match (simplified)
            existing = await db.execute(
                select(Reminder).where(
                    and_(
                        Reminder.rule_id == rule.id,
                        Reminder.title.contains(tr.full_name or ""),
                        Reminder.status.in_([ReminderStatus.PENDING, ReminderStatus.SENT])
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            # Find linked resident if any
            resident_result = await db.execute(
                select(Resident).where(Resident.full_name == tr.full_name).limit(1)
            )
            resident = resident_result.scalar_one_or_none()
            if not resident:
                continue
            
            reminder = Reminder(
                rule_id=rule.id,
                resident_id=resident.id,
                title="Tạm trú sắp hết hạn",
                message=f"Đăng ký tạm trú của {tr.full_name} sẽ hết hạn ngày {tr.end_date}. Vui lòng gia hạn!",
                due_date=tr.end_date,
                status=ReminderStatus.SENT,
                sent_at=datetime.now()
            )
            db.add(reminder)
            created_count += 1
    
    await db.commit()
    
    return {
        "status": "success",
        "message": f"Đã tạo {created_count} nhắc nhở mới"
    }


@router.get("/admin/all")
async def get_all_reminders(
    status: Optional[ReminderStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[Admin/Leader] Xem tất cả nhắc nhở."""
    role = await db.get(Role, current_user.role_id)
    if not role or role.name not in ["admin", "leader"]:
        raise HTTPException(status_code=403, detail="Không có quyền")
    
    query = select(Reminder)
    if status:
        query = query.where(Reminder.status == status)
    query = query.order_by(desc(Reminder.created_at))
    
    result = await db.execute(query)
    reminders = result.scalars().all()
    
    # Get resident names
    response = []
    for r in reminders:
        resident = await db.get(Resident, r.resident_id)
        response.append({
            "id": r.id,
            "resident_name": resident.full_name if resident else "N/A",
            "title": r.title,
            "message": r.message,
            "due_date": r.due_date.isoformat() if r.due_date else None,
            "status": r.status.value,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    
    return response


@router.post("/admin/create")
async def create_reminder(
    data: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[Admin] Tạo nhắc nhở thủ công."""
    role = await db.get(Role, current_user.role_id)
    if not role or role.name not in ["admin", "leader"]:
        raise HTTPException(status_code=403, detail="Không có quyền")
    
    # Verify resident exists
    resident = await db.get(Resident, data.resident_id)
    if not resident:
        raise HTTPException(status_code=404, detail="Không tìm thấy cư dân")
    
    reminder = Reminder(
        rule_id=None,  # Manual reminder
        resident_id=data.resident_id,
        title=data.title,
        message=data.message,
        due_date=data.due_date,
        status=ReminderStatus.SENT,
        sent_at=datetime.now()
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    
    return {
        "status": "success",
        "message": "Đã tạo nhắc nhở thành công",
        "id": reminder.id
    }
