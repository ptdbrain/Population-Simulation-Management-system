from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text, DateTime, Boolean, Date, func
from app.models.base import Base
import enum


class RuleType(str, enum.Enum):
    CCCD_14 = "CCCD_14"              # Trẻ em sắp 14 tuổi cần làm CCCD
    TEMP_RESIDENCE_EXPIRE = "TEMP_RESIDENCE_EXPIRE"  # Tạm trú sắp hết hạn
    TEMP_ABSENCE_LONG = "TEMP_ABSENCE_LONG"  # Tạm vắng quá lâu (>30 ngày)
    LIFE_EVENT = "LIFE_EVENT"        # Sự kiện cuộc sống (sinh con, kết hôn...)


class ReminderStatus(str, enum.Enum):
    PENDING = "PENDING"      # Chờ thông báo
    SENT = "SENT"           # Đã gửi
    ACKNOWLEDGED = "ACKNOWLEDGED"  # Người dùng đã xem
    DISMISSED = "DISMISSED"  # Bỏ qua


class ReminderRule(Base):
    """Quy tắc nhắc nhở - Admin cấu hình"""
    __tablename__ = 'reminder_rules'
    
    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(Enum(RuleType), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    days_before = Column(Integer, default=30)  # Nhắc trước bao nhiêu ngày
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Reminder(Base):
    """Nhắc nhở cụ thể cho từng cư dân"""
    __tablename__ = 'reminders'
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey('reminder_rules.id'), nullable=True)  # Null for manual reminders
    resident_id = Column(Integer, ForeignKey('residents.id'), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    due_date = Column(Date)  # Ngày hết hạn/cần thực hiện
    status = Column(Enum(ReminderStatus), default=ReminderStatus.PENDING)
    sent_at = Column(DateTime)
    acknowledged_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
