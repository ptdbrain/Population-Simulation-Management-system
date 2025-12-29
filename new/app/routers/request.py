"""
Request Router - API for resident requests that need Leader/Admin approval
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json

from app.database import get_db
from app.core.security import get_current_user
from app.models.auth_models import User
from app.models.request_models import ResidentRequest, RequestStatus, RequestType, ComplaintResponse
from app.models.complaint_models import Complaint
from app.services.request_service import RequestApprovalService

router = APIRouter(prefix="/requests", tags=["Requests"])


# ==========================================
# SCHEMAS
# ==========================================
class RequestCreate(BaseModel):
    request_type: str
    title: str
    description: Optional[str] = None
    request_data: Optional[str] = None  # JSON string
    household_id: Optional[int] = None
    resident_id: Optional[int] = None


class RequestUpdate(BaseModel):
    status: str  # APPROVED or REJECTED
    approval_note: Optional[str] = None


class RequestResponse(BaseModel):
    id: int
    request_type: str
    status: str
    title: str
    description: Optional[str]
    requester_id: int
    requester_name: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    approval_note: Optional[str] = None

    class Config:
        from_attributes = True


class ComplaintResponseCreate(BaseModel):
    complaint_id: int
    response_text: str


class ComplaintResponseOut(BaseModel):
    id: int
    complaint_id: int
    responder_id: int
    response_text: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# REQUEST ENDPOINTS
# ==========================================

@router.get("/", response_model=List[RequestResponse])
async def get_requests(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all requests (Admin/Leader see all, Resident sees own)"""
    query = select(ResidentRequest)
    
    # Filter by role
    if current_user.role and current_user.role.name.lower() == "resident":
        query = query.where(ResidentRequest.requester_id == current_user.id)
    
    # Filter by status
    if status_filter:
        query = query.where(ResidentRequest.status == status_filter)
    
    query = query.order_by(ResidentRequest.created_at.desc())
    result = await db.execute(query)
    requests = result.scalars().all()
    
    # Get requester names
    response_list = []
    for req in requests:
        user_result = await db.execute(select(User).where(User.id == req.requester_id))
        user = user_result.scalars().first()
        
        response_list.append(RequestResponse(
            id=req.id,
            request_type=req.request_type or "",
            status=req.status or "PENDING",
            title=req.title,
            description=req.description,
            requester_id=req.requester_id,
            requester_name=user.username if user else None,
            created_at=req.created_at,
            processed_at=req.processed_at,
            approval_note=req.approval_note
        ))
    
    return response_list


@router.post("/", response_model=RequestResponse)
async def create_request(
    request_data: RequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new request (any authenticated user)"""
    # Validate request_type is one of the allowed values
    allowed_types = ['NEW_HOUSEHOLD', 'JOIN_HOUSEHOLD', 'SPLIT_HOUSEHOLD', 'HOUSEHOLD_UPDATE', 
                     'PERSON_UPDATE', 'TEMP_RESIDENCE', 'TEMP_ABSENCE', 'OTHER']
    if request_data.request_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid request type: {request_data.request_type}")
    
    # Auto-populate resident_id and household_id from current_user if not provided
    resident_id = request_data.resident_id
    household_id = request_data.household_id
    
    # If resident_id not provided, get from current_user
    if not resident_id and current_user.resident_id:
        resident_id = current_user.resident_id
        
        # If household_id not provided, get from resident
        if not household_id:
            from app.models.residence_models import Resident
            res_result = await db.execute(select(Resident).where(Resident.id == resident_id))
            resident = res_result.scalars().first()
            if resident and resident.household_id:
                household_id = resident.household_id
    
    new_request = ResidentRequest(
        request_type=request_data.request_type,  # Store as string directly
        title=request_data.title,
        description=request_data.description,
        request_data=request_data.request_data,
        requester_id=current_user.id,
        household_id=household_id,
        resident_id=resident_id,
        status="PENDING"  # Store as string
    )
    
    db.add(new_request)
    await db.commit()
    await db.refresh(new_request)
    
    return RequestResponse(
        id=new_request.id,
        request_type=new_request.request_type,
        status=new_request.status,
        title=new_request.title,
        description=new_request.description,
        requester_id=new_request.requester_id,
        requester_name=current_user.username,
        created_at=new_request.created_at,
        processed_at=new_request.processed_at,
        approval_note=new_request.approval_note
    )


@router.put("/{request_id}")
async def process_request(
    request_id: int,
    update_data: RequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve or reject a request (Leader/Admin only)"""
    # Check permission
    if current_user.role and current_user.role.name.lower() == "resident":
        raise HTTPException(status_code=403, detail="Không có quyền duyệt yêu cầu")
    
    result = await db.execute(select(ResidentRequest).where(ResidentRequest.id == request_id))
    request = result.scalars().first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")
    
    if request.status != "PENDING":
        raise HTTPException(status_code=400, detail="Yêu cầu đã được xử lý")
    
    # Validate status is APPROVED or REJECTED
    if update_data.status not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail=f"Invalid status: {update_data.status}")
    
    # Update request status
    request.status = update_data.status
    request.approval_note = update_data.approval_note
    request.approved_by = current_user.id
    request.processed_at = datetime.utcnow()
    db.add(request)
    
    # If approved, execute the actual data changes
    if update_data.status == "APPROVED":
        try:
            result_message = None
            
            # Route to appropriate handler based on request type
            if request.request_type == "SPLIT_HOUSEHOLD":
                result = await RequestApprovalService.approve_split_household(
                    db=db,
                    request_data_json=request.request_data,
                    current_user=current_user,
                    household_id=request.household_id,
                    resident_id=request.resident_id
                )
                result_message = result.get('message', 'Đã tách hộ thành công')
                
            elif request.request_type == "JOIN_HOUSEHOLD":
                result = await RequestApprovalService.approve_join_household(
                    db=db,
                    request_data_json=request.request_data,
                    current_user=current_user,
                    household_id=request.household_id,
                    resident_id=request.resident_id
                )
                result_message = result.get('message', 'Đã thêm vào hộ thành công')
                
            elif request.request_type == "NEW_HOUSEHOLD":
                result = await RequestApprovalService.approve_new_household(
                    db=db,
                    request_data_json=request.request_data,
                    current_user=current_user,
                    household_id=request.household_id,
                    resident_id=request.resident_id
                )
                result_message = result.get('message', 'Đã tạo hộ mới thành công')
                
            elif request.request_type == "HOUSEHOLD_UPDATE":
                result = await RequestApprovalService.approve_household_update(
                    db=db,
                    request_data_json=request.request_data,
                    current_user=current_user,
                    household_id=request.household_id,
                    resident_id=request.resident_id
                )
                result_message = result.get('message', 'Đã cập nhật thông tin hộ')
                
            elif request.request_type == "PERSON_UPDATE":
                result = await RequestApprovalService.approve_person_update(
                    db=db,
                    request_data_json=request.request_data,
                    current_user=current_user,
                    household_id=request.household_id,
                    resident_id=request.resident_id
                )
                result_message = result.get('message', 'Đã cập nhật thông tin cá nhân')
                
            # TEMP_RESIDENCE and TEMP_ABSENCE are handled in separate endpoints
            # in temp_residence.py router, so we don't process them here
            elif request.request_type in ["TEMP_RESIDENCE", "TEMP_ABSENCE"]:
                # These are handled by separate endpoints
                result_message = "Loại yêu cầu này được xử lý bởi endpoint riêng"
            
            else:
                # For OTHER or unknown types, just update status without processing
                result_message = f"Yêu cầu loại '{request.request_type}' đã được duyệt (không có xử lý tự động)"
            
            await db.commit()
            
            return {
                "message": f"Yêu cầu đã được duyệt. {result_message or ''}"
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions from service layer
            await db.rollback()
            raise
        except Exception as e:
            # Rollback on any error
            await db.rollback()
            # Log the full error for debugging
            import traceback
            print(f"Error processing request {request_id}:")
            print(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Lỗi khi xử lý yêu cầu: {str(e)}"
            )
    else:
        # Just rejected, no data changes needed
        await db.commit()
        return {"message": "Yêu cầu đã được từ chối"}


@router.delete("/{request_id}")
async def delete_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a request (owner or Admin only)"""
    result = await db.execute(select(ResidentRequest).where(ResidentRequest.id == request_id))
    request = result.scalars().first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")
    
    # Check permission
    is_admin = current_user.role and current_user.role.name.lower() == "admin"
    is_owner = request.requester_id == current_user.id
    
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Không có quyền xóa yêu cầu này")
    
    await db.delete(request)
    await db.commit()
    
    return {"message": "Đã xóa yêu cầu"}


# ==========================================
# COMPLAINT RESPONSE ENDPOINTS
# ==========================================

@router.get("/complaint-responses/{complaint_id}", response_model=List[ComplaintResponseOut])
async def get_complaint_responses(
    complaint_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all responses for a complaint"""
    result = await db.execute(
        select(ComplaintResponse)
        .where(ComplaintResponse.complaint_id == complaint_id)
        .order_by(ComplaintResponse.created_at.asc())
    )
    return result.scalars().all()


@router.post("/complaint-responses", response_model=ComplaintResponseOut)
async def create_complaint_response(
    response_data: ComplaintResponseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Respond to a complaint (Leader/Admin only)"""
    # Check permission
    if current_user.role and current_user.role.name.lower() == "resident":
        raise HTTPException(status_code=403, detail="Không có quyền trả lời phản ánh")
    
    # Check complaint exists
    complaint_result = await db.execute(select(Complaint).where(Complaint.id == response_data.complaint_id))
    complaint = complaint_result.scalars().first()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Không tìm thấy phản ánh")
    
    new_response = ComplaintResponse(
        complaint_id=response_data.complaint_id,
        responder_id=current_user.id,
        response_text=response_data.response_text
    )
    
    db.add(new_response)
    await db.commit()
    await db.refresh(new_response)
    
    return new_response


@router.put("/complaints/{complaint_id}/resolve")
async def resolve_complaint(
    complaint_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a complaint as resolved (Leader/Admin only)"""
    # Check permission
    if current_user.role and current_user.role.name.lower() == "resident":
        raise HTTPException(status_code=403, detail="Không có quyền giải quyết phản ánh")
    
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalars().first()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Không tìm thấy phản ánh")
    
    complaint.status = "RESOLVED"
    await db.commit()
    
    return {"message": "Phản ánh đã được đánh dấu là đã giải quyết"}
