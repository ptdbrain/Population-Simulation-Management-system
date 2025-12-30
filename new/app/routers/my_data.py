"""
Resident self-service endpoints
Allows residents to view their own data (household, family, requests)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime

from app.database import get_db
from app.core.security import get_current_user
from app.models.residence_models import Resident, Household, ResidentStatus, Gender
from app.models.auth_models import User
from app.models.request_models import ResidentRequest

router = APIRouter(prefix="/my", tags=["My Data (Resident Self-Service)"])

# Response Models
class MyHouseholdResponse(BaseModel):
    id: int
    household_code: str
    address: str
    owner_name: Optional[str] = None
    member_count: int = 0
    
    class Config:
        orm_mode = True

class MyFamilyMemberResponse(BaseModel):
    id: int
    full_name: str
    dob: date
    gender: str
    cid: str
    relation_to_owner: str
    status: str
    
    class Config:
        orm_mode = True

class MyRequestResponse(BaseModel):
    id: int
    request_type: str
    title: str
    content: str
    status: str
    admin_note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

@router.get("/household", response_model=Optional[MyHouseholdResponse])
async def get_my_household(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current user's household information"""
    
    if not current_user.resident_id:
        raise HTTPException(status_code=404, detail="Bạn chưa được liên kết với nhân khẩu nào")
    
    # Get the resident record
    resident = await db.get(Resident, current_user.resident_id)
    if not resident:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin nhân khẩu")
    
    if not resident.household_id:
        raise HTTPException(status_code=404, detail="Bạn chưa thuộc hộ khẩu nào")
    
    # Get household with member count
    household = await db.get(Household, resident.household_id)
    if not household:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin hộ khẩu")
    
    # Count members
    result = await db.execute(
        select(Resident).where(Resident.household_id == household.id)
    )
    members = result.scalars().all()
    
    # Get owner name
    owner_name = None
    if household.owner_id:
        owner = await db.get(Resident, household.owner_id)
        if owner:
            owner_name = owner.full_name
    
    return MyHouseholdResponse(
        id=household.id,
        household_code=household.household_code,
        address=household.address,
        owner_name=owner_name,
        member_count=len(members)
    )

@router.get("/family", response_model=List[MyFamilyMemberResponse])
async def get_my_family(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all family members in the user's household"""
    
    if not current_user.resident_id:
        raise HTTPException(status_code=404, detail="Bạn chưa được liên kết với nhân khẩu nào")
    
    # Get the resident record
    resident = await db.get(Resident, current_user.resident_id)
    if not resident:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin nhân khẩu")
    
    if not resident.household_id:
        return []  # Return empty list if no household
    
    # Get all members in the same household
    result = await db.execute(
        select(Resident).where(Resident.household_id == resident.household_id)
    )
    members = result.scalars().all()
    
    return [
        MyFamilyMemberResponse(
            id=m.id,
            full_name=m.full_name,
            dob=m.dob,
            gender=m.gender.value if hasattr(m.gender, 'value') else str(m.gender),
            cid=m.cid,
            relation_to_owner=m.relation_to_owner,
            status=m.status.value if hasattr(m.status, 'value') else str(m.status)
        )
        for m in members
    ]

@router.get("/requests", response_model=List[MyRequestResponse])
async def get_my_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all requests submitted by the current user"""
    
    result = await db.execute(
        select(ResidentRequest)
        .where(ResidentRequest.requester_id == current_user.id)  # Fixed: use requester_id
        .order_by(ResidentRequest.created_at.desc())
    )
    requests = result.scalars().all()
    
    return [
        MyRequestResponse(
            id=r.id,
            request_type=r.request_type or "",  # String, no .value needed
            title=r.title,
            content=r.description or "",  # Fixed: use description
            status=r.status or "PENDING",  # String, no .value needed
            admin_note=r.approval_note,  # Fixed: use approval_note
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in requests
    ]

@router.get("/profile", response_model=Optional[MyFamilyMemberResponse])
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current user's resident profile"""
    
    if not current_user.resident_id:
        raise HTTPException(status_code=404, detail="Bạn chưa được liên kết với nhân khẩu nào")
    
    resident = await db.get(Resident, current_user.resident_id)
    if not resident:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin nhân khẩu")
    
    return MyFamilyMemberResponse(
        id=resident.id,
        full_name=resident.full_name,
        dob=resident.dob,
        gender=resident.gender.value if hasattr(resident.gender, 'value') else str(resident.gender),
        cid=resident.cid,
        relation_to_owner=resident.relation_to_owner,
        status=resident.status.value if hasattr(resident.status, 'value') else str(resident.status)
    )


# Response Model for History
class ChangeHistoryResponse(BaseModel):
    id: int
    change_type: str
    changed_at: datetime
    changed_by_username: Optional[str] = None
    details: Optional[str] = None
    
    class Config:
        orm_mode = True


@router.get("/history")
async def get_my_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get residence change history for the current user and their household"""
    from app.models.residence_models import ChangeHistory
    
    if not current_user.resident_id:
        return {"personal": [], "household": []}
    
    # Get the resident record
    resident = await db.get(Resident, current_user.resident_id)
    if not resident:
        return {"personal": [], "household": []}
    
    # Get personal history
    personal_query = select(ChangeHistory).where(
        ChangeHistory.resident_id == current_user.resident_id
    ).order_by(ChangeHistory.changed_at.desc())
    personal_result = await db.execute(personal_query)
    personal_history = personal_result.scalars().all()
    
    # Get household history
    household_history = []
    if resident.household_id:
        household_query = select(ChangeHistory).where(
            ChangeHistory.household_id == resident.household_id
        ).order_by(ChangeHistory.changed_at.desc())
        household_result = await db.execute(household_query)
        household_history = household_result.scalars().all()
    
    # Helper to format history
    async def format_history(history_items):
        result = []
        for h in history_items:
            # Get username of who made the change
            changed_by_name = None
            if h.changed_by:
                user = await db.get(User, h.changed_by)
                if user:
                    changed_by_name = user.username
            
            # Build details from old_data and new_data
            details = ""
            change_type_label = {
                "SPLIT": "Tách hộ",
                "MOVED_IN": "Nhập hộ",
                "MOVED_OUT": "Rời hộ"
            }.get(h.change_type.value if hasattr(h.change_type, 'value') else str(h.change_type), "Thay đổi")
            
            if h.old_data and h.new_data:
                details = f"Từ: {h.old_data} → Đến: {h.new_data}"
            elif h.new_data:
                details = str(h.new_data)
            
            result.append({
                "id": h.id,
                "change_type": change_type_label,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
                "changed_by": changed_by_name,
                "details": details
            })
        return result
    
    return {
        "personal": await format_history(personal_history),
        "household": await format_history(household_history)
    }


@router.get("/notifications")
async def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for the current user"""
    from app.models.notification_models import Notification
    
    result = await db.execute(
        select(Notification)
        .where(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifications = result.scalars().all()
    
    return [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "type": n.notification_type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "related_type": n.related_type,
            "related_id": n.related_id
        }
        for n in notifications
    ]


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read"""
    from app.models.notification_models import Notification
    
    notification = await db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if notification.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    notification.is_read = True
    notification.read_at = datetime.now()
    db.add(notification)
    await db.commit()
    
    return {"status": "success"}


@router.get("/announcements")
async def get_announcements(db: AsyncSession = Depends(get_db)):
    """Get active public announcements"""
    from app.models.notification_models import Announcement
    from sqlalchemy import or_
    
    # Get active announcements that haven't expired
    result = await db.execute(
        select(Announcement)
        .where(
            Announcement.is_active == True,
            or_(
                Announcement.expires_at.is_(None),
                Announcement.expires_at > datetime.now()
            )
        )
        .order_by(Announcement.created_at.desc())
        .limit(10)
    )
    announcements = result.scalars().all()
    
    return [
        {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in announcements
    ]


