"""
Request Approval Service - Handles automatic data updates when requests are approved
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from datetime import datetime
import json
from typing import Dict, Any, Optional

from app.models.residence_models import Household, Resident, ChangeHistory, ChangeType
from app.models.auth_models import User


class RequestApprovalService:
    """Service for processing approved requests and updating related data"""
    
    @staticmethod
    async def approve_split_household(
        db: AsyncSession, 
        request_data_json: str, 
        current_user: User,
        household_id: Optional[int] = None,
        resident_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Handle SPLIT_HOUSEHOLD request approval
        
        Expected request_data format:
        {
            "old_household_id": int,
            "new_owner_id": int,
            "moving_resident_ids": [int, ...],
            "new_address": str,
            "new_household_code": str,
            "replacement_owner_id": int (optional)
        }
        """
        try:
            data = json.loads(request_data_json) if request_data_json else {}
        except json.JSONDecodeError:
            data = {}
        
        # Use household_id from request object if not in data
        old_household_id = data.get('old_household_id') or household_id
        new_owner_id = data.get('new_owner_id') or resident_id
        moving_resident_ids = data.get('moving_resident_ids', [])
        new_address = data.get('new_address')
        new_household_code = data.get('new_household_code')
        replacement_owner_id = data.get('replacement_owner_id')
        
        # If new_owner_id and no moving_resident_ids, use new_owner_id as moving resident
        if new_owner_id and not moving_resident_ids:
            moving_resident_ids = [new_owner_id]
        
        # Check if we have minimum required data to process
        if not old_household_id:
            # Cannot process without old household
            return {
                "status": "skipped",
                "message": "Yêu cầu đã duyệt. Vui lòng thực hiện tách hộ thủ công (thiếu thông tin old_household_id)"
            }
        
        if not all([new_owner_id, new_address, new_household_code]):
            # Missing required fields - just approve without auto-processing
            return {
                "status": "skipped", 
                "message": "Yêu cầu đã duyệt. Vui lòng thực hiện tách hộ thủ công (thiếu thông tin chi tiết)"
            }
        
        # 1. Fetch Old Household
        result = await db.execute(select(Household).where(Household.id == old_household_id))
        old_household = result.scalars().first()
        if not old_household:
            raise HTTPException(status_code=404, detail="Old household not found")
        
        # 2. Critical Check: Is new_owner_id currently the owner of old_household_id?
        if old_household.owner_id == new_owner_id:
            if not replacement_owner_id:
                raise HTTPException(
                    status_code=400,
                    detail="The person moving out is the current owner. You must specify a replacement_owner_id."
                )
            
            # Check if replacement is moving out
            if replacement_owner_id in moving_resident_ids:
                raise HTTPException(status_code=400, detail="Replacement owner cannot be moving out.")
            
            # Verify replacement exists and is in old household
            res_check = await db.execute(
                select(Resident).where(
                    Resident.id == replacement_owner_id,
                    Resident.household_id == old_household_id
                )
            )
            replacement = res_check.scalars().first()
            if not replacement:
                raise HTTPException(
                    status_code=400,
                    detail="Replacement owner not valid member of old household."
                )
            
            # Update old household owner
            old_household.owner_id = replacement_owner_id
            replacement.relation_to_owner = "HEAD"
            db.add(old_household)
            db.add(replacement)
            
            # Log owner change
            log_owner_change = ChangeHistory(
                household_id=old_household.id,
                resident_id=replacement.id,
                change_type=ChangeType.MOVED_IN,
                old_data={"owner_id": new_owner_id},
                new_data={"owner_id": replacement.id, "reason": "Old owner moved out"},
                changed_by=current_user.id
            )
            db.add(log_owner_change)
        
        # 3. Verify new owner exists
        res_new_owner_check = await db.execute(select(Resident).where(Resident.id == new_owner_id))
        new_owner = res_new_owner_check.scalars().first()
        if not new_owner:
            raise HTTPException(status_code=404, detail="New owner not found")
        
        # 4. Check if household code already exists
        existing_code = await db.execute(
            select(Household).where(Household.household_code == new_household_code)
        )
        if existing_code.scalars().first():
            raise HTTPException(status_code=400, detail=f"Household code {new_household_code} already exists")
        
        # 5. Create New Household
        new_household = Household(
            household_code=new_household_code,
            owner_id=new_owner_id,
            address=new_address
        )
        db.add(new_household)
        await db.flush()  # Get ID
        
        # 6. Update residents
        for r_id in moving_resident_ids:
            res_result = await db.execute(select(Resident).where(Resident.id == r_id))
            resident = res_result.scalars().first()
            if not resident:
                continue
            
            if resident.household_id != old_household_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Resident {r_id} does not belong to the source household."
                )
            
            # Log history
            history = ChangeHistory(
                household_id=old_household_id,
                resident_id=resident.id,
                change_type=ChangeType.SPLIT,
                old_data={"household_id": old_household_id},
                new_data={"household_id": new_household.id},
                changed_by=current_user.id
            )
            db.add(history)
            
            # Update resident
            resident.household_id = new_household.id
            if resident.id == new_owner_id:
                resident.relation_to_owner = "HEAD"
            else:
                resident.relation_to_owner = "MEMBER"
            
            db.add(resident)
        
        return {
            "status": "success",
            "new_household_id": new_household.id,
            "message": f"Đã tách hộ thành công. Hộ mới ID: {new_household.id}"
        }
    
    @staticmethod
    async def approve_join_household(
        db: AsyncSession,
        request_data_json: str,
        current_user: User,
        household_id: Optional[int] = None,
        resident_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Handle JOIN_HOUSEHOLD request approval
        
        Expected request_data format:
        {
            "resident_id": int,
            "target_household_id": int,
            "relation_to_owner": str
        }
        """
        try:
            data = json.loads(request_data_json) if request_data_json else {}
        except json.JSONDecodeError:
            data = {}
        
        res_id = data.get('resident_id') or resident_id
        target_household_id = data.get('target_household_id') or household_id
        relation = data.get('relation_to_owner', 'MEMBER')
        
        if not res_id or not target_household_id:
            return {
                "status": "skipped",
                "message": "Yêu cầu đã duyệt. Vui lòng thực hiện thủ công (thiếu resident_id hoặc target_household_id)"
            }
        
        # Verify resident exists
        res_result = await db.execute(select(Resident).where(Resident.id == res_id))
        resident = res_result.scalars().first()
        if not resident:
            raise HTTPException(status_code=404, detail="Resident not found")
        
        # Verify target household exists
        hh_result = await db.execute(select(Household).where(Household.id == target_household_id))
        target_household = hh_result.scalars().first()
        if not target_household:
            raise HTTPException(status_code=404, detail="Target household not found")
        
        old_household_id = resident.household_id
        
        # Log history
        history = ChangeHistory(
            household_id=target_household_id,
            resident_id=resident.id,
            change_type=ChangeType.MOVED_IN,
            old_data={"household_id": old_household_id},
            new_data={"household_id": target_household_id, "relation": relation},
            changed_by=current_user.id
        )
        db.add(history)
        
        # Update resident
        resident.household_id = target_household_id
        resident.relation_to_owner = relation
        db.add(resident)
        
        return {
            "status": "success",
            "message": f"Đã thêm {resident.full_name} vào hộ {target_household.household_code}"
        }
    
    @staticmethod
    async def approve_new_household(
        db: AsyncSession,
        request_data_json: str,
        current_user: User,
        household_id: Optional[int] = None,
        resident_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Handle NEW_HOUSEHOLD request approval
        
        Expected request_data format:
        {
            "household_code": str,
            "owner_id": int,
            "address": str
        }
        """
        try:
            data = json.loads(request_data_json) if request_data_json else {}
        except json.JSONDecodeError:
            data = {}
        
        household_code = data.get('household_code')
        owner_id = data.get('owner_id') or resident_id
        address = data.get('address')
        
        if not all([household_code, owner_id, address]):
            return {
                "status": "skipped",
                "message": "Yêu cầu đã duyệt. Vui lòng tạo hộ thủ công (thiếu household_code, owner_id, hoặc address)"
            }
        
        # Verify owner exists
        owner_result = await db.execute(select(Resident).where(Resident.id == owner_id))
        owner = owner_result.scalars().first()
        if not owner:
            raise HTTPException(status_code=404, detail="Owner resident not found")
        
        # Check if household code already exists
        existing = await db.execute(
            select(Household).where(Household.household_code == household_code)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Household code already exists")
        
        # Create new household
        new_hh = Household(
            household_code=household_code,
            owner_id=owner_id,
            address=address
        )
        db.add(new_hh)
        await db.flush()
        
        # Update owner's household_id and relation
        old_household_id = owner.household_id
        owner.household_id = new_hh.id
        owner.relation_to_owner = "HEAD"
        db.add(owner)
        
        # Log history
        history = ChangeHistory(
            household_id=new_hh.id,
            resident_id=owner.id,
            change_type=ChangeType.MOVED_IN,
            old_data={"household_id": old_household_id},
            new_data={"household_id": new_hh.id, "reason": "Created new household"},
            changed_by=current_user.id
        )
        db.add(history)
        
        return {
            "status": "success",
            "household_id": new_hh.id,
            "message": f"Đã tạo hộ mới: {household_code}"
        }
    
    @staticmethod
    async def approve_household_update(
        db: AsyncSession,
        request_data_json: str,
        current_user: User,
        household_id: Optional[int] = None,
        resident_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Handle HOUSEHOLD_UPDATE request approval
        
        Expected request_data format:
        {
            "household_id": int,
            "address": str (optional),
            "household_code": str (optional),
            "owner_id": int (optional)
        }
        """
        try:
            data = json.loads(request_data_json) if request_data_json else {}
        except json.JSONDecodeError:
            data = {}
        
        hh_id = data.get('household_id') or household_id
        if not hh_id:
            return {
                "status": "skipped",
                "message": "Yêu cầu đã duyệt. Vui lòng cập nhật thủ công (thiếu household_id)"
            }
        
        # Fetch household
        hh_result = await db.execute(select(Household).where(Household.id == hh_id))
        household = hh_result.scalars().first()
        if not household:
            raise HTTPException(status_code=404, detail="Household not found")
        
        # Store old data for logging
        old_data = {
            "address": household.address,
            "household_code": household.household_code,
            "owner_id": household.owner_id
        }
        
        # Update fields if provided
        if 'address' in data:
            household.address = data['address']
        
        if 'household_code' in data:
            # Check if new code already exists
            existing = await db.execute(
                select(Household).where(
                    Household.household_code == data['household_code'],
                    Household.id != hh_id
                )
            )
            if existing.scalars().first():
                raise HTTPException(status_code=400, detail="Household code already exists")
            household.household_code = data['household_code']
        
        if 'owner_id' in data:
            new_owner_id = data['owner_id']
            # Verify new owner exists and belongs to household
            owner_result = await db.execute(
                select(Resident).where(
                    Resident.id == new_owner_id,
                    Resident.household_id == hh_id
                )
            )
            new_owner = owner_result.scalars().first()
            if not new_owner:
                raise HTTPException(
                    status_code=400,
                    detail="New owner must be a member of this household"
                )
            household.owner_id = new_owner_id
            new_owner.relation_to_owner = "HEAD"
            db.add(new_owner)
        
        db.add(household)
        
        # Log history
        new_data = {
            "address": household.address,
            "household_code": household.household_code,
            "owner_id": household.owner_id
        }
        history = ChangeHistory(
            household_id=hh_id,
            resident_id=household.owner_id,
            change_type=ChangeType.MOVED_IN,  # Using closest available type
            old_data=old_data,
            new_data=new_data,
            changed_by=current_user.id
        )
        db.add(history)
        
        return {
            "status": "success",
            "message": "Đã cập nhật thông tin hộ"
        }
    
    @staticmethod
    async def approve_person_update(
        db: AsyncSession,
        request_data_json: str,
        current_user: User,
        household_id: Optional[int] = None,
        resident_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Handle PERSON_UPDATE request approval
        
        Expected request_data format:
        {
            "resident_id": int,
            "full_name": str (optional),
            "dob": str (optional),
            "gender": str (optional),
            "cid": str (optional),
            "relation_to_owner": str (optional),
            "status": str (optional)
        }
        """
        try:
            data = json.loads(request_data_json) if request_data_json else {}
        except json.JSONDecodeError:
            data = {}
        
        res_id = data.get('resident_id') or resident_id
        if not res_id:
            return {
                "status": "skipped",
                "message": "Yêu cầu đã duyệt. Vui lòng cập nhật thủ công (thiếu resident_id)"
            }
        
        # Fetch resident
        res_result = await db.execute(select(Resident).where(Resident.id == res_id))
        resident = res_result.scalars().first()
        if not resident:
            raise HTTPException(status_code=404, detail="Resident not found")
        
        # Store old data
        old_data = {
            "full_name": resident.full_name,
            "dob": str(resident.dob) if resident.dob else None,
            "gender": resident.gender.value if hasattr(resident.gender, 'value') else str(resident.gender),
            "cid": resident.cid,
            "relation_to_owner": resident.relation_to_owner,
            "status": resident.status.value if hasattr(resident.status, 'value') else str(resident.status)
        }
        
        # Update fields if provided
        updatable_fields = ['full_name', 'relation_to_owner']
        for field in updatable_fields:
            if field in data:
                setattr(resident, field, data[field])
        
        # Handle special fields
        if 'dob' in data:
            from datetime import date as date_type
            if isinstance(data['dob'], str):
                resident.dob = date_type.fromisoformat(data['dob'])
            else:
                resident.dob = data['dob']
        
        if 'gender' in data:
            from app.models.residence_models import Gender
            resident.gender = Gender(data['gender'])
        
        if 'status' in data:
            from app.models.residence_models import ResidentStatus
            resident.status = ResidentStatus(data['status'])
        
        if 'cid' in data:
            # Check if CID already exists
            existing = await db.execute(
                select(Resident).where(
                    Resident.cid == data['cid'],
                    Resident.id != res_id
                )
            )
            if existing.scalars().first():
                raise HTTPException(status_code=400, detail="Citizen ID already exists")
            resident.cid = data['cid']
        
        db.add(resident)
        
        # Log history
        new_data = {
            "full_name": resident.full_name,
            "dob": str(resident.dob) if resident.dob else None,
            "gender": resident.gender.value if hasattr(resident.gender, 'value') else str(resident.gender),
            "cid": resident.cid,
            "relation_to_owner": resident.relation_to_owner,
            "status": resident.status.value if hasattr(resident.status, 'value') else str(resident.status)
        }
        
        if resident.household_id:
            history = ChangeHistory(
                household_id=resident.household_id,
                resident_id=resident.id,
                change_type=ChangeType.MOVED_IN,  # Using closest available type
                old_data=old_data,
                new_data=new_data,
                changed_by=current_user.id
            )
            db.add(history)
        
        return {
            "status": "success",
            "message": f"Đã cập nhật thông tin {resident.full_name}"
        }
