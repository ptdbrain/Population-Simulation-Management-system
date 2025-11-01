from sqlalchemy.orm import Session
from . import models, Schemas, auth_jwt

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, username: str, password: str, full_name=None, email=None, phone=None): # tạo người dùng mới với các thông tin cơ bản
    hashed = auth_jwt.hash_password(password) # băm mật khẩu
    user = models.User(username=username, password_hash=hashed, full_name=full_name, email=email, phone=phone) # tạo đối tượng người dùng
    db.add(user) # thêm vào phiên làm việc với cơ sở dữ liệu
    db.commit() # cam kết thay đổi
    db.refresh(user)    # làm mới đối tượng người dùng để lấy ID đã tạo
    return user

# roles/permissions management (basic)
def assign_role(db: Session, user_id: int, role_id: int):
    if not db.query(models.UserRole).filter(models.UserRole.user_id==user_id, models.UserRole.role_id==role_id).first(): # kiểm tra nếu người dùng đã có vai trò này chưa
        ur = models.UserRole(user_id=user_id, role_id=role_id)  # tạo đối tượng UserRole
        db.add(ur)  # thêm vào phiên làm việc với cơ sở dữ liệu
        db.commit() # cam kết thay đổi