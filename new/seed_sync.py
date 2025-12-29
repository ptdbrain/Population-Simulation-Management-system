"""
Sync Seed Script - Alternative for Windows asyncio issues
Uses synchronous SQLAlchemy to avoid event loop problems
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import date

# Get database URL from environment or .env
from dotenv import load_dotenv
load_dotenv()

# Convert async URL to sync URL
async_url = os.getenv('DATABASE_URL', 'mysql+aiomysql://root:password@localhost/residence_db')
sync_url = async_url.replace('mysql+aiomysql', 'mysql+pymysql')

print(f"Using sync URL: {sync_url}")

engine = create_engine(sync_url, echo=True)
Session = sessionmaker(bind=engine)

from app.models.base import Base
from app.models.auth_models import Role, Permission, User
from app.models.residence_models import Household, Resident, Gender, ResidentStatus
from app.models import temp_models, complaint_models, request_models
from app.core.security import get_password_hash

def seed():
    # Drop and recreate tables
    print("Dropping all tables...")
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        tables = ["role_permissions", "users", "change_history", "complaints", "complaint_responses", 
                  "resident_requests", "absent_requests", "temp_residence_registrations", 
                  "residents", "households", "roles", "permissions"]
        for table in tables:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table};"))
            except Exception as e:
                print(f"Could not drop {table}: {e}")
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    
    print("Creating all tables...")
    Base.metadata.create_all(engine)
    
    with Session() as db:
        # 1. Permissions
        perms = [
            Permission(code="household.split", description="Split household"),
            Permission(code="household.create", description="Create household"),
            Permission(code="household.view", description="View household"),
            Permission(code="person.create", description="Create person"),
            Permission(code="person.view", description="View person"),
            Permission(code="person.update", description="Update person"),
            Permission(code="complaint.create", description="Create complaint"),
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
        db.flush()

        # 2. Roles
        admin_role = Role(name="admin", description="System Admin", permissions=perms)
        leader_role = Role(
            name="leader", 
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
            name="resident", 
            description="Normal citizen",
            permissions=[p for p in perms if p.code in [
                "person.view", "complaint.create",
                "temp_absence.create", "temp_residence.create"
            ]]
        )
        db.add_all([admin_role, leader_role, resident_role])
        db.flush()
        
        # 3. Residents with 12-digit CCCD
        h1_head = Resident(full_name="Nguyen Van A", dob=date(1980, 1, 1), gender=Gender.MALE, cid="001234567001", relation_to_owner="HEAD", status=ResidentStatus.PERMANENT)
        h1_wife = Resident(full_name="Tran Thi B", dob=date(1982, 2, 2), gender=Gender.FEMALE, cid="001234567002", relation_to_owner="WIFE", status=ResidentStatus.PERMANENT)
        h1_child = Resident(full_name="Nguyen Van C", dob=date(2005, 3, 3), gender=Gender.MALE, cid="001234567003", relation_to_owner="CHILD", status=ResidentStatus.PERMANENT)
        h2_head = Resident(full_name="Le Van D", dob=date(1975, 4, 4), gender=Gender.MALE, cid="001234567004", relation_to_owner="HEAD", status=ResidentStatus.PERMANENT)
        
        db.add_all([h1_head, h1_wife, h1_child, h2_head])
        db.flush()

        # 4. Households
        h1 = Household(household_code="HK001", owner_id=h1_head.id, address="123 Street A")
        h2 = Household(household_code="HK002", owner_id=h2_head.id, address="456 Street B")
        db.add_all([h1, h2])
        db.flush()

        # Link residents to household
        h1_head.household_id = h1.id
        h1_wife.household_id = h1.id
        h1_child.household_id = h1.id
        h2_head.household_id = h2.id
        db.add_all([h1_head, h1_wife, h1_child, h2_head])

        # 5. Users
        u_admin = User(username="admin", password_hash=get_password_hash("admin123"), role_id=admin_role.id)
        u_leader = User(username="leader", password_hash=get_password_hash("leader123"), role_id=leader_role.id)
        u_resident = User(username="resident1", password_hash=get_password_hash("res123"), role_id=resident_role.id, resident_id=h1_head.id)
        
        db.add_all([u_admin, u_leader, u_resident])
        db.commit()
        
        print("=" * 50)
        print("Seeding complete!")
        print("=" * 50)
        print("Test accounts:")
        print("  admin / admin123 (Quản trị viên)")
        print("  leader / leader123 (Tổ trưởng)")
        print("  resident1 / res123 (Cư dân)")
        print("")
        print("Test CCCD for registration:")
        print("  001234567001 - Nguyen Van A")
        print("  001234567002 - Tran Thi B")
        print("  001234567003 - Nguyen Van C")
        print("  001234567004 - Le Van D")
        print("=" * 50)

if __name__ == "__main__":
    seed()
