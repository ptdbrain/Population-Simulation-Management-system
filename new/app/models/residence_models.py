from sqlalchemy import Column, Integer, String, Date, Enum, ForeignKey, JSON, DateTime, func
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base

class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class ResidentStatus(str, enum.Enum):
    PERMANENT = "PERMANENT"
    TEMPORARY_ABSENT = "TEMPORARY_ABSENT"
    TEMPORARY_RESIDENT = "TEMPORARY_RESIDENT"
    MOVED_OUT = "MOVED_OUT"

class ChangeType(str, enum.Enum):
    SPLIT = "SPLIT"
    MOVED_IN = "MOVED_IN"
    MOVED_OUT = "MOVED_OUT"

class Household(Base):
    __tablename__ = 'households'
    id = Column(Integer, primary_key=True, index=True)
    household_code = Column(String(50), unique=True, index=True)
    owner_id = Column(Integer, ForeignKey('residents.id', name='fk_household_owner', use_alter=True))
    address = Column(String(255))
    created_at = Column(DateTime, default=func.now())
    deleted_at = Column(DateTime, nullable=True)

    owner = relationship("Resident", foreign_keys=[owner_id], post_update=True)
    residents = relationship("Resident", foreign_keys="Resident.household_id", back_populates="household")

class Resident(Base):
    __tablename__ = 'residents'
    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey('households.id', name='fk_resident_household', use_alter=True), nullable=True)
    full_name = Column(String(150))
    dob = Column(Date)
    gender = Column(Enum(Gender))
    cid = Column(String(12), unique=True, index=True) # CCCD
    relation_to_owner = Column(String(50)) # HEAD, WIFE, SON...
    status = Column(Enum(ResidentStatus), default=ResidentStatus.PERMANENT)
    
    # Contact & Job Information
    phone = Column(String(15), nullable=True)  # Số điện thoại
    email = Column(String(100), nullable=True)  # Email
    occupation = Column(String(100), nullable=True)  # Nghề nghiệp / Công việc

    household = relationship("Household", foreign_keys=[household_id], back_populates="residents")

class ChangeHistory(Base):
    __tablename__ = 'change_history'
    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey('households.id'))
    resident_id = Column(Integer, ForeignKey('residents.id'))
    change_type = Column(Enum(ChangeType))
    old_data = Column(JSON, nullable=True)
    new_data = Column(JSON, nullable=True)
    changed_by = Column(Integer, ForeignKey('users.id'))
    changed_at = Column(DateTime, default=func.now())
