from sqlalchemy import Column, Integer, String, Date, Enum, ForeignKey
from app.models.base import Base
import enum

class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class AbsentRequest(Base):
    __tablename__ = 'absent_requests'
    id = Column(Integer, primary_key=True, index=True)
    resident_id = Column(Integer, ForeignKey('residents.id'))
    start_date = Column(Date)
    end_date = Column(Date)
    reason = Column(String(255))
    destination = Column(String(255))
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    approved_by = Column(Integer, ForeignKey('users.id'), nullable=True)

class TempResidenceRegistration(Base):
    __tablename__ = 'temp_residence_registrations'
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150))
    dob = Column(Date)
    gender = Column(String(10), default="MALE")  # MALE or FEMALE
    origin_address = Column(String(255))
    host_household_id = Column(Integer, ForeignKey('households.id'))
    start_date = Column(Date)
    end_date = Column(Date)
    reason = Column(String(255))
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    approved_by = Column(Integer, ForeignKey('users.id'), nullable=True)

