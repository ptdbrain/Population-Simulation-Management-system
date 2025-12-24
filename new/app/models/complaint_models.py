from sqlalchemy import Column, Integer, String, Enum, ForeignKey, JSON, Text, DateTime, func
from app.models.base import Base
import enum

class ComplaintCategory(str, enum.Enum):
    SECURITY = "SECURITY"
    HYGIENE = "HYGIENE"
    INFRASTRUCTURE = "INFRASTRUCTURE"

class ComplaintStatus(str, enum.Enum):
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    RESOLVED = "RESOLVED"

class Complaint(Base):
    __tablename__ = 'complaints'
    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey('users.id'))
    content = Column(Text)
    category = Column(Enum(ComplaintCategory))
    status = Column(Enum(ComplaintStatus), default=ComplaintStatus.NEW)
    duplication_count = Column(Integer, default=0)
    reporter_list = Column(JSON, default=list) # Stores list of who reported it
    resolution_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
