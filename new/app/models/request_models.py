"""
Request Models - For resident-initiated requests that need Leader/Admin approval
"""
from sqlalchemy import Column, Integer, String, Date, Enum, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.models.base import Base
import enum


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RequestType(str, enum.Enum):
    # Household requests
    NEW_HOUSEHOLD = "NEW_HOUSEHOLD"         # Request to create a new household
    JOIN_HOUSEHOLD = "JOIN_HOUSEHOLD"       # Request to join an existing household   
    SPLIT_HOUSEHOLD = "SPLIT_HOUSEHOLD"     # Request to split from household
    HOUSEHOLD_UPDATE = "HOUSEHOLD_UPDATE"   # Request to update household info
    
    # Person requests
    PERSON_UPDATE = "PERSON_UPDATE"         # Request to update personal info
    
    # Temporary residence/absence
    TEMP_RESIDENCE = "TEMP_RESIDENCE"       # Temporary residence registration
    TEMP_ABSENCE = "TEMP_ABSENCE"           # Temporary absence registration
    
    # Other
    OTHER = "OTHER"                         # Other requests


class ResidentRequest(Base):
    """
    General request model for resident-initiated changes
    """
    __tablename__ = 'resident_requests'
    
    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String(50), nullable=False)  # Changed from Enum to String
    status = Column(String(20), default="PENDING")  # Changed from Enum to String
    
    # Who created the request
    requester_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Request details stored as text (JSON-like)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    request_data = Column(Text, nullable=True)  # JSON string of request details
    
    # Related entities (optional, for linking)
    household_id = Column(Integer, ForeignKey('households.id'), nullable=True)
    resident_id = Column(Integer, ForeignKey('residents.id'), nullable=True)
    
    # Approval info
    approved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    approval_note = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime, nullable=True)


class ComplaintResponse(Base):
    """
    Responses to complaints from Leader/Admin
    """
    __tablename__ = 'complaint_responses'
    
    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey('complaints.id'), nullable=False)
    responder_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    response_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
