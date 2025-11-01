# scripts/seed.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.db import engine, Base, SessionLocal
from app import models, auth_jwt

# create tables (if using alembic, skip)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

roles = [ # danh sách roles mặc định
    ("admin","System administrator"),
    ("leader","Tổ trưởng"),
    ("citizen","Công dân")
]
for name,desc in roles:
    if not db.query(models.Role).filter_by(name=name).first(): # kiểm tra nếu vai trò đã tồn tại chưa
        db.add(models.Role(name=name, description=desc)) # thêm vai trò mới vào phiên làm việc với cơ sở dữ liệu
db.commit()

perms = [ # danh sách permissions mặc định
    ("user.manage","Manage users and roles"),
    ("household.view","View households"),
    ("household.create","Create households"),
    ("household.split","Split household"),
    ("person.view","View persons"),
    ("person.create","Create person"),
    ("person.update","Update person"),
    ("temp_absence.create","Create temp absence"),
    ("temp_absence.approve","Approve temp absence"),
    ("temp_residence.create","Create temp residence"),
    ("temp_residence.approve","Approve temp residence"),
    ("complaint.create","Create complaint"),
    ("complaint.view","View complaint"),
    ("complaint.update_status","Update complaint status"),
    ("report.statistics","View reports")
]
for code,desc in perms:
    if not db.query(models.Permission).filter_by(code=code).first(): # kiểm tra nếu permission đã tồn tại chưa
        db.add(models.Permission(code=code, description=desc)) # thêm permission mới vào phiên làm việc với cơ sở dữ liệu
db.commit()

# assign some perms to admin role
admin_role = db.query(models.Role).filter_by(name="admin").first() # lấy vai trò admin
all_perms = db.query(models.Permission).all()   # lấy tất cả permissions
for p in all_perms:
    if not db.query(models.RolePermission).filter_by(role_id=admin_role.id, permission_id=p.id).first():    # kiểm tra nếu vai trò đã có permission chưa
        db.add(models.RolePermission(role_id=admin_role.id, permission_id=p.id))    # thêm permission vào vai trò admin
db.commit() 

# create admin user
if not db.query(models.User).filter_by(username="admin").first():   # kiểm tra nếu người dùng admin đã tồn tại chưa
    u = models.User(username="admin", password_hash=auth_jwt.hash_password("admin123"), full_name="Administrator")  # tạo người dùng admin mới
    db.add(u)   # thêm người dùng admin vào phiên làm việc với cơ sở dữ liệu
    db.commit()  # cam kết thay đổi
    db.refresh(u)   # làm mới đối tượng người dùng để lấy ID đã tạo
    db.add(models.UserRole(user_id=u.id, role_id=admin_role.id))    # gán vai trò admin cho người dùng admin
    db.commit()
    print("Admin created with username=admin password=admin123")
else:
    print("Admin exists")

db.close()
