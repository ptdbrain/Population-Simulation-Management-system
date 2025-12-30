from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text, DateTime, func
from app.models.base import Base
import enum


class QuestionStatus(str, enum.Enum):
    PENDING = "PENDING"      # Đang chờ trả lời
    ANSWERED = "ANSWERED"    # Đã trả lời
    CLOSED = "CLOSED"        # Đã đóng


class TargetRole(str, enum.Enum):
    LEADER = "leader"        # Gửi cho tổ trưởng
    ADMIN = "admin"          # Gửi cho admin


class Question(Base):
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True, index=True)
    asker_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    target_role = Column(Enum(TargetRole), default=TargetRole.LEADER)
    status = Column(Enum(QuestionStatus), default=QuestionStatus.PENDING)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Answer(Base):
    __tablename__ = 'answers'
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    answerer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
