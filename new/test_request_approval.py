"""
Test script for request approval workflow
This script demonstrates how to create and approve requests
"""
import asyncio
import sys
from datetime import date
import json

# Add parent directory to path
sys.path.append('.')

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db, engine
from app.models.residence_models import Household, Resident, ChangeHistory
from app.models.request_models import ResidentRequest
from app.models.auth_models import User
from app.services.request_service import RequestApprovalService


async def test_split_household():
    """Test SPLIT_HOUSEHOLD request approval"""
    print("\n=== Testing SPLIT_HOUSEHOLD ===")
    
    async with AsyncSession(engine) as db:
        # Find a household with multiple residents
        result = await db.execute(
            select(Household)
            .join(Resident, Household.id == Resident.household_id)
            .limit(1)
        )
        household = result.scalars().first()
        
        if not household:
            print("❌ No household found for testing")
            return
        
        # Get residents in this household
        residents_result = await db.execute(
            select(Resident).where(Resident.household_id == household.id)
        )
        residents = residents_result.scalars().all()
        
        if len(residents) < 2:
            print(f"❌ Household {household.household_code} has only {len(residents)} resident(s), need at least 2")
            return
        
        print(f"✓ Found household: {household.household_code} with {len(residents)} residents")
        
        # Select one resident to move out (not the owner)
        moving_resident = None
        remaining_resident = None
        
        for r in residents:
            if r.id != household.owner_id:
                moving_resident = r
            else:
                remaining_resident = r
        
        if not moving_resident:
            print("❌ All residents are owners, cannot split")
            return
        
        print(f"✓ Moving resident: {moving_resident.full_name}")
        
        # Create request data
        request_data = {
            "old_household_id": household.id,
            "new_owner_id": moving_resident.id,
            "moving_resident_ids": [moving_resident.id],
            "new_address": "123 Test Street, New Location",
            "new_household_code": f"HH-TEST-{household.id}-SPLIT"
        }
        
        # Get an admin user
        admin_result = await db.execute(select(User).limit(1))
        admin = admin_result.scalars().first()
        
        if not admin:
            print("❌ No user found for testing")
            return
        
        # Create request
        new_request = ResidentRequest(
            request_type="SPLIT_HOUSEHOLD",
            title="Yêu cầu tách hộ khẩu test",
            description="Test split household automation",
            request_data=json.dumps(request_data),
            requester_id=admin.id,
            household_id=household.id,
            resident_id=moving_resident.id,
            status="PENDING"
        )
        
        db.add(new_request)
        await db.commit()
        await db.refresh(new_request)
        
        print(f"✓ Created request ID: {new_request.id}")
        
        # Count households before
        count_before = await db.execute(select(Household))
        households_before = len(count_before.scalars().all())
        
        # Approve the request
        try:
            async with db.begin():
                new_request.status = "APPROVED"
                new_request.approved_by = admin.id
                db.add(new_request)
                
                result = await RequestApprovalService.approve_split_household(
                    db=db,
                    request_data_json=new_request.request_data,
                    current_user=admin,
                    household_id=new_request.household_id,
                    resident_id=new_request.resident_id
                )
                
                await db.commit()
                print(f"✓ Request approved: {result['message']}")
        except Exception as e:
            print(f"❌ Error approving request: {e}")
            await db.rollback()
            return
        
        # Verify results
        count_after = await db.execute(select(Household))
        households_after = len(count_after.scalars().all())
        
        print(f"✓ Households before: {households_before}, after: {households_after}")
        
        if households_after == households_before + 1:
            print("✅ SPLIT_HOUSEHOLD test PASSED")
        else:
            print("❌ SPLIT_HOUSEHOLD test FAILED")


async def test_join_household():
    """Test JOIN_HOUSEHOLD request approval"""
    print("\n=== Testing JOIN_HOUSEHOLD ===")
    
    async with AsyncSession(engine) as db:
        # Find a resident without a household or in a different household
        resident_result = await db.execute(select(Resident).limit(1))
        resident = resident_result.scalars().first()
        
        # Find a different household
        household_result = await db.execute(select(Household).limit(1))
        target_household = household_result.scalars().first()
        
        if not resident or not target_household:
            print("❌ Not enough data for testing")
            return
        
        print(f"✓ Resident: {resident.full_name}, Target Household: {target_household.household_code}")
        
        old_household_id = resident.household_id
        
        # Create request
        request_data = {
            "resident_id": resident.id,
            "target_household_id": target_household.id,
            "relation_to_owner": "MEMBER"
        }
        
        admin_result = await db.execute(select(User).limit(1))
        admin = admin_result.scalars().first()
        
        new_request = ResidentRequest(
            request_type="JOIN_HOUSEHOLD",
            title="Yêu cầu vào hộ test",
            description="Test join household automation",
            request_data=json.dumps(request_data),
            requester_id=admin.id,
            household_id=target_household.id,
            resident_id=resident.id,
            status="PENDING"
        )
        
        db.add(new_request)
        await db.commit()
        await db.refresh(new_request)
        
        print(f"✓ Created request ID: {new_request.id}")
        
        # Approve the request
        try:
            async with db.begin():
                new_request.status = "APPROVED"
                new_request.approved_by = admin.id
                db.add(new_request)
                
                result = await RequestApprovalService.approve_join_household(
                    db=db,
                    request_data_json=new_request.request_data,
                    current_user=admin,
                    household_id=new_request.household_id,
                    resident_id=new_request.resident_id
                )
                
                await db.commit()
                print(f"✓ Request approved: {result['message']}")
        except Exception as e:
            print(f"❌ Error approving request: {e}")
            await db.rollback()
            return
        
        # Verify resident household changed
        await db.refresh(resident)
        
        if resident.household_id == target_household.id:
            print(f"✅ JOIN_HOUSEHOLD test PASSED - Resident moved from {old_household_id} to {target_household.id}")
        else:
            print(f"❌ JOIN_HOUSEHOLD test FAILED - Resident still in household {resident.household_id}")


async def main():
    """Run all tests"""
    print("Starting Request Approval Tests...")
    print("=" * 50)
    
    await test_split_household()
    await test_join_household()
    
    print("\n" + "=" * 50)
    print("Tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
