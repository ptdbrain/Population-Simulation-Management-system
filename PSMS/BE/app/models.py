from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table, Enum, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .db import Base
import enum

class GenderEnum(enum.Enum):
    M = "Male"
    F = "Female"
    O = "Other"


class StatusEnum(enum.Enum):
    NEW = "new"
    PENDING = "pending"
    RESOLVED = "resolved"

class Role(Base):
    __tablename__ = "roles" # Tên bảng trong cơ sở dữ liệu
    id = Column(Integer, primary_key=True, index=True) # Khóa chính
    name = Column(String(50), unique=True, index=True, nullable=False) # Tên vai trò
    description = Column(String(255), nullable=True) # Mô tả vai trò

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)

class Household(Base):
    __tablename__ = "households"
    id = Column(Integer, primary_key=True)
    household_number = Column(String(100), unique=True, nullable=False)
    address = Column(String(255))
    created_at = Column(TIMESTAMP, default=func.now())

class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100))
    birthdate = Column(DateTime)
    gender = Column(Enum(GenderEnum))
    current_household_id = Column(Integer, ForeignKey("households.id"))
    relation_to_head = Column(String(100))
    created_at = Column(TIMESTAMP, default=func.now())


class PersonHistory(Base):
    __tablename__ = "person_histories"
    id = Column(Integer, primary_key=True) # int tự tăng
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    action = Column(String(50), nullable=False)
    from_household_id = Column(Integer, ForeignKey("households.id"), nullable=True)
    to_household_id = Column(Integer, ForeignKey("households.id"), nullable=True)
    note = Column(String(255), nullable=True)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    performed_at = Column(TIMESTAMP, default=func.now())


class TempAbsence(Base):
    __tablename__ = "temp_absences"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    from_date = Column(DateTime, nullable=False)
    to_date = Column(DateTime, nullable=False)
    reason = Column(String(255), nullable=False)
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.NEW)
    registered_by = Column(Integer, ForeignKey("users.id"), nullable=False)

class TempResidence(Base):
    __tablename__ = "temp_residences"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    from_date = Column(DateTime, nullable=False)
    to_date = Column(DateTime, nullable=False)
    host_household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    reason = Column(String(255), nullable=False)
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.NEW)
    registered_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    registered_at = Column(TIMESTAMP, default=func.now()) 

class Complaint(Base): 
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True, index=True)
    reporter_person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    content = Column(String(1000), nullable=False)
    category = Column(String(100), nullable=False)
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.NEW)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)    
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    duplicate_count = Column(Integer, default=1)

class ComplaintReport(Base):
    __tablename__ = "complaint_reports"
    id = Column(Integer, primary_key=True)
    report_at = Column(TIMESTAMP, default=func.now())
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    reporter_person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    report_at = Column(TIMESTAMP, default=func.now())

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(String(1000), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.now())

# Refresh token model
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False)  # hash of token stored
    created_at = Column(TIMESTAMP, server_default=func.now())
    expires_at = Column(TIMESTAMP, nullable=False)
    revoked = Column(Boolean, default=False)
    device_info = Column(String(255))  # optional: browser/user-agent/ip
