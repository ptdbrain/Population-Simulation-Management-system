import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal, engine
from app.models.base import Base
from app.models.auth_models import Role, Permission, User
from app.models.residence_models import Household, Resident, Gender, ResidentStatus
# Ensure all models are imported so metadata is populated
from app.models import temp_models, complaint_models 
from app.core.security import get_password_hash
from datetime import date

async def seed():
    async with engine.begin() as conn:
        print("Cleaning up database...")
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        
        # Manually drop tables in case of naming conflicts with constraints
        tables = ["role_permissions", "users", "change_history", "complaints", "absent_requests", "temp_residences", "residents", "households", "roles", "permissions"]
        for table in tables:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table};"))
            
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        print("Recreating tables...")
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # 1. Permissions
        perms = [
            Permission(code="household.split", description="Split household"),
            Permission(code="household.create", description="Create household"),
            Permission(code="household.view", description="View household"),
            
            Permission(code="person.create", description="Create person"),
            Permission(code="person.view", description="View person"),
            Permission(code="person.update", description="Update person"),
            
            Permission(code="complaint.create", description="Create complaint"), # Citizen
            Permission(code="complaint.view", description="View complaint"),
            Permission(code="complaint.update_status", description="Update complaint status"),
            Permission(code="complaint.notify_reporter", description="Notify reporter"),
            
            Permission(code="temp_absence.create", description="Create absence req"),
            Permission(code="temp_absence.approve", description="Approve absence req"),
            Permission(code="temp_residence.create", description="Create temp res req"),
            Permission(code="temp_residence.approve", description="Approve temp res req"),
            
            Permission(code="report.statistics", description="View stats"),
            Permission(code="admin:super", description="Full access"),
            Permission(code="resident:view", description="Legacy View"),
        ]
        db.add_all(perms)
        await db.flush()

        # 2. Roles & Permissions Assignment
        admin_role = Role(
            name="Admin", 
            description="System Admin",
            permissions=perms
        )
        leader_role = Role(
            name="Leader", 
            description="To truong dan pho",
            permissions=[p for p in perms if p.code in [
                "household.split", "household.view", "household.create",
                "person.view", "person.update",
                "complaint.view", "complaint.update_status",
                "temp_absence.approve", "temp_residence.approve",
                "report.statistics"
            ]]
        )
        resident_role = Role(
            name="Resident", 
            description="Normal citizen",
            permissions=[p for p in perms if p.code in [
                "person.view",
                "complaint.create",
                "temp_absence.create",
                "temp_residence.create"
            ]]
        )
        db.add_all([admin_role, leader_role, resident_role])
        await db.flush()
        
        # 4. Residents
        # Household 1
        h1_head = Resident(full_name="Nguyen Van A", dob=date(1980, 1, 1), gender=Gender.MALE, cid="001", relation_to_owner="HEAD", status=ResidentStatus.PERMANENT)
        h1_wife = Resident(full_name="Tran Thi B", dob=date(1982, 2, 2), gender=Gender.FEMALE, cid="002", relation_to_owner="WIFE", status=ResidentStatus.PERMANENT)
        h1_child = Resident(full_name="Nguyen Van C", dob=date(2005, 3, 3), gender=Gender.MALE, cid="003", relation_to_owner="CHILD", status=ResidentStatus.PERMANENT)
        
        # Household 2
        h2_head = Resident(full_name="Le Van D", dob=date(1975, 4, 4), gender=Gender.MALE, cid="004", relation_to_owner="HEAD", status=ResidentStatus.PERMANENT)
        
        db.add_all([h1_head, h1_wife, h1_child, h2_head])
        await db.flush()

        # 5. Households
        h1 = Household(household_code="HK001", owner_id=h1_head.id, address="123 Street A")
        h2 = Household(household_code="HK002", owner_id=h2_head.id, address="456 Street B")
        db.add_all([h1, h2])
        await db.flush()

        # Link residents to household
        h1_head.household_id = h1.id
        h1_wife.household_id = h1.id
        h1_child.household_id = h1.id
        h2_head.household_id = h2.id
        db.add_all([h1_head, h1_wife, h1_child, h2_head])

        # 6. Users
        u_admin = User(username="admin", password_hash=get_password_hash("admin123"), role_id=admin_role.id)
        u_leader = User(username="leader", password_hash=get_password_hash("leader123"), role_id=leader_role.id)
        u_resident = User(username="resident1", password_hash=get_password_hash("res123"), role_id=resident_role.id, resident_id=h1_head.id)
        
        db.add_all([u_admin, u_leader, u_resident])
        
        await db.commit()
        print("Seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed())
