"""
Notification Models - For system notifications to users
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
from app.models.base import Base


class NotificationType:
    """Notification type constants"""
    INFO = "INFO"           # General information
    REMINDER = "REMINDER"   # Reminders (e.g., procedures to complete)
    REQUEST = "REQUEST"     # Request status updates
    COMPLAINT = "COMPLAINT" # Complaint status updates
    SYSTEM = "SYSTEM"       # System announcements


class Notification(Base):
    """
    Notification model for sending notifications to users
    """
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Who receives the notification
    recipient_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Notification content
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    notification_type = Column(String(50), default=NotificationType.INFO)
    
    # Related entities (for navigation)
    related_type = Column(String(50), nullable=True)  # 'complaint', 'request', etc.
    related_id = Column(Integer, nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False)
    
    # Who created it (for admin/leader notifications)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    read_at = Column(DateTime, nullable=True)


class Announcement(Base):
    """
    Public announcements visible to all residents
    """
    __tablename__ = 'announcements'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)
