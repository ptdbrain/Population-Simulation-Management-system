from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.core.security import get_current_user
from app.models.question_models import Question, Answer, QuestionStatus, TargetRole
from app.models.auth_models import User

router = APIRouter(prefix="/questions", tags=["Q&A"])


# Schemas
class QuestionCreate(BaseModel):
    title: str
    content: str
    target_role: TargetRole = TargetRole.LEADER


class QuestionResponse(BaseModel):
    id: int
    asker_id: int
    asker_username: Optional[str] = None
    title: str
    content: str
    target_role: str
    status: str
    created_at: datetime
    answer_count: int = 0

    class Config:
        from_attributes = True


class AnswerCreate(BaseModel):
    content: str


class AnswerResponse(BaseModel):
    id: int
    question_id: int
    answerer_id: int
    answerer_username: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# Endpoints
@router.post("/", response_model=dict)
async def create_question(
    data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Người dân đặt câu hỏi cho tổ trưởng hoặc admin."""
    question = Question(
        asker_id=current_user.id,
        title=data.title,
        content=data.content,
        target_role=data.target_role
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    
    return {
        "status": "success",
        "message": "Câu hỏi đã được gửi thành công!",
        "question_id": question.id
    }


@router.get("/", response_model=List[QuestionResponse])
async def get_questions(
    status: Optional[QuestionStatus] = None,
    target_role: Optional[TargetRole] = None,
    my_questions: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy danh sách câu hỏi:
    - Người dân: my_questions=True để xem câu hỏi của mình
    - Tổ trưởng: target_role=leader để xem câu hỏi gửi cho tổ
    - Admin: Xem tất cả hoặc target_role=admin
    """
    from sqlalchemy import func as sql_func
    
    query = select(Question)
    
    # Get user role
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    # Lấy role name
    from app.models.auth_models import Role
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one_or_none()
    role_name = role.name if role else "resident"
    
    # Filter based on role and parameters
    if my_questions or role_name == "resident":
        # Residents only see their own questions
        query = query.where(Question.asker_id == current_user.id)
    elif role_name == "leader":
        # Leader sees questions targeted to them, or filter by specific role
        if target_role:
            query = query.where(Question.target_role == target_role)
        else:
            query = query.where(Question.target_role == TargetRole.LEADER)
    elif role_name == "admin":
        # Admin can filter by target_role, or see all
        if target_role:
            query = query.where(Question.target_role == target_role)
        # If no target_role specified, admin sees all questions
    
    if status:
        query = query.where(Question.status == status)
    
    query = query.order_by(desc(Question.created_at))
    
    result = await db.execute(query)
    questions = result.scalars().all()
    
    if not questions:
        return []
    
    # OPTIMIZED: Batch query for all asker usernames
    question_ids = [q.id for q in questions]
    asker_ids = list(set(q.asker_id for q in questions))
    
    # Get all users in one query
    users_result = await db.execute(
        select(User).where(User.id.in_(asker_ids))
    )
    users_map = {u.id: u.username for u in users_result.scalars().all()}
    
    # Get answer counts in one query using GROUP BY
    answer_counts_result = await db.execute(
        select(Answer.question_id, sql_func.count(Answer.id).label('count'))
        .where(Answer.question_id.in_(question_ids))
        .group_by(Answer.question_id)
    )
    answer_counts = {row[0]: row[1] for row in answer_counts_result.all()}
    
    # Build response
    response = []
    for q in questions:
        response.append(QuestionResponse(
            id=q.id,
            asker_id=q.asker_id,
            asker_username=users_map.get(q.asker_id, "Unknown"),
            title=q.title,
            content=q.content,
            target_role=q.target_role.value,
            status=q.status.value,
            created_at=q.created_at,
            answer_count=answer_counts.get(q.id, 0)
        ))
    
    return response


@router.get("/{id}")
async def get_question_detail(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xem chi tiết câu hỏi và các câu trả lời."""
    question = await db.get(Question, id)
    if not question:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi")
    
    # Get asker info
    asker = await db.get(User, question.asker_id)
    
    # Get answers
    result = await db.execute(
        select(Answer).where(Answer.question_id == id).order_by(Answer.created_at)
    )
    answers = result.scalars().all()
    
    answer_list = []
    for a in answers:
        answerer = await db.get(User, a.answerer_id)
        answer_list.append({
            "id": a.id,
            "answerer_id": a.answerer_id,
            "answerer_username": answerer.username if answerer else "Unknown",
            "content": a.content,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })
    
    return {
        "id": question.id,
        "asker_id": question.asker_id,
        "asker_username": asker.username if asker else "Unknown",
        "title": question.title,
        "content": question.content,
        "target_role": question.target_role.value,
        "status": question.status.value,
        "created_at": question.created_at.isoformat() if question.created_at else None,
        "answers": answer_list
    }


@router.post("/{id}/answers", response_model=dict)
async def add_answer(
    id: int,
    data: AnswerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tổ trưởng/Admin trả lời câu hỏi."""
    question = await db.get(Question, id)
    if not question:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi")
    
    # Check role - only leader/admin can answer
    from app.models.auth_models import Role
    result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = result.scalar_one_or_none()
    
    if not role or role.name == "resident":
        raise HTTPException(status_code=403, detail="Chỉ tổ trưởng hoặc admin mới có thể trả lời")
    
    # Create answer
    answer = Answer(
        question_id=id,
        answerer_id=current_user.id,
        content=data.content
    )
    db.add(answer)
    
    # Update question status
    question.status = QuestionStatus.ANSWERED
    db.add(question)
    
    await db.commit()
    await db.refresh(answer)
    
    return {
        "status": "success",
        "message": "Đã trả lời câu hỏi!",
        "answer_id": answer.id
    }


@router.put("/{id}/close", response_model=dict)
async def close_question(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Đóng câu hỏi (người hỏi hoặc admin)."""
    question = await db.get(Question, id)
    if not question:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi")
    
    # Check permission: asker or admin
    from app.models.auth_models import Role
    result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = result.scalar_one_or_none()
    
    if question.asker_id != current_user.id and (not role or role.name != "admin"):
        raise HTTPException(status_code=403, detail="Không có quyền đóng câu hỏi này")
    
    question.status = QuestionStatus.CLOSED
    db.add(question)
    await db.commit()
    
    return {"status": "success", "message": "Đã đóng câu hỏi"}
