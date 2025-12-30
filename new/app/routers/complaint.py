from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import difflib

from app.database import get_db
from app.core.security import get_current_user, PermissionChecker
from app.models.complaint_models import Complaint, ComplaintStatus, ComplaintCategory
from app.models.auth_models import User

router = APIRouter(prefix="/complaints", tags=["Complaints"])

class ComplaintCreate(BaseModel):
    content: str
    category: ComplaintCategory

@router.post("/", response_model=dict)
async def create_complaint(complaint: ComplaintCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Fetch active complaints in same category within last 72h
    seventy_two_hours_ago = datetime.utcnow() - timedelta(hours=72)
    
    result = await db.execute(
        select(Complaint)
        .where(
            Complaint.status != ComplaintStatus.RESOLVED,
            Complaint.category == complaint.category,
            Complaint.created_at >= seventy_two_hours_ago
        )
    )
    active_complaints = result.scalars().all()
    
    match_found = None
    
    for existing in active_complaints:
        # Fuzzy Match 70%
        matcher = difflib.SequenceMatcher(None, existing.content, complaint.content)
        if matcher.ratio() >= 0.7:
            match_found = existing
            break
            
    if match_found:
        # Update existing
        match_found.duplication_count += 1
        
        # Append reporter to list (JSON)
        # Handle list init safely
        reporter_list = list(match_found.reporter_list) if match_found.reporter_list else []
        reporter_list.append({"user_id": current_user.id, "username": current_user.username, "at": datetime.utcnow().isoformat()})
        match_found.reporter_list = reporter_list
        
        db.add(match_found)
        await db.commit()
        return {"status": "deduplicated", "message": "Similar complaint found. Count incremented.", "complaint_id": match_found.id}
        
    else:
        # Create new
        new_complaint = Complaint(
            reporter_id=current_user.id,
            content=complaint.content,
            category=complaint.category,
            reporter_list=[{"user_id": current_user.id, "username": current_user.username, "at": datetime.utcnow().isoformat()}]
        )
        db.add(new_complaint)
        await db.commit()
        await db.refresh(new_complaint)
        return {"status": "created", "complaint_id": new_complaint.id}

@router.put("/{id}/status", dependencies=[Depends(PermissionChecker("complaint.update_status"))])
async def update_complaint_status(id: int, status: ComplaintStatus, resolution_note: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    complaint = await db.get(Complaint, id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    complaint.status = status
    if resolution_note:
        complaint.resolution_note = resolution_note
        
    db.add(complaint)
    await db.commit()
    return {"status": "success"}

class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    resolution_note: Optional[str] = None

@router.put("/{id}", dependencies=[Depends(PermissionChecker("complaint.update_status"))])
async def update_complaint(id: int, data: ComplaintUpdate, db: AsyncSession = Depends(get_db)):
    complaint = await db.get(Complaint, id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    if data.status:
        complaint.status = data.status
    if data.resolution_note:
        complaint.resolution_note = data.resolution_note
        
    db.add(complaint)
    await db.commit()
    return {"status": "success", "message": "Complaint updated"}

@router.get("/{id}")
async def get_complaint(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    complaint = await db.get(Complaint, id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@router.get("/")
async def get_complaints(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Complaint))
    return result.scalars().all()

# Response/Feedback from upper management
class ComplaintResponse(BaseModel):
    response_content: str
    new_status: Optional[ComplaintStatus] = None

@router.post("/{id}/respond", dependencies=[Depends(PermissionChecker("complaint.update_status"))])
async def respond_to_complaint(id: int, data: ComplaintResponse, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Leader adds response from upper management.
    This updates the resolution_note and can change status.
    Returns list of reporters to be notified.
    """
    complaint = await db.get(Complaint, id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    # Add response
    complaint.resolution_note = data.response_content
    if data.new_status:
        complaint.status = data.new_status
    else:
        complaint.status = ComplaintStatus.PROCESSING
    
    db.add(complaint)
    await db.commit()
    
    # Return reporters to notify
    return {
        "status": "success",
        "message": "Response added successfully",
        "reporters_to_notify": complaint.reporter_list or [],
        "complaint_id": id
    }


# Satisfaction Rating Schema
class RatingRequest(BaseModel):
    rating: int  # 1-5 stars
    comment: Optional[str] = None


@router.post("/{id}/rate")
async def rate_complaint(
    id: int, 
    data: RatingRequest, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Rate a resolved complaint (satisfaction rating 1-5 stars).
    Only the original reporter(s) can rate.
    Only resolved complaints can be rated.
    """
    complaint = await db.get(Complaint, id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    # Check if complaint is resolved
    if complaint.status != ComplaintStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Chỉ có thể đánh giá phản ánh đã được giải quyết")
    
    # Check if already rated
    if complaint.satisfaction_rating is not None:
        raise HTTPException(status_code=400, detail="Phản ánh này đã được đánh giá")
    
    # Check if user is a reporter
    is_reporter = False
    if complaint.reporter_id == current_user.id:
        is_reporter = True
    elif complaint.reporter_list:
        for r in complaint.reporter_list:
            if r.get('user_id') == current_user.id:
                is_reporter = True
                break
    
    if not is_reporter:
        raise HTTPException(status_code=403, detail="Chỉ người gửi phản ánh mới có thể đánh giá")
    
    # Validate rating
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Đánh giá phải từ 1 đến 5 sao")
    
    # Update complaint
    complaint.satisfaction_rating = data.rating
    complaint.rating_comment = data.comment
    complaint.rated_at = datetime.utcnow()
    
    db.add(complaint)
    await db.commit()
    
    return {
        "status": "success",
        "message": "Cảm ơn bạn đã đánh giá!",
        "rating": data.rating
    }

