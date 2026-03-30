"""Chat API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage, MessageRole
from app.schemas.chat import ChatSessionCreate, ChatSessionResponse, ChatMessageCreate, ChatMessageResponse
from app.dependencies import get_current_user

router = APIRouter()


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """List chat sessions, newest first."""
    query = select(ChatSession).order_by(ChatSession.updated_at.desc())
    if user:
        query = query.where(ChatSession.user_id == user.id)
    result = await db.execute(query.limit(50))
    return result.scalars().all()


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    request: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """Create a new chat session."""
    session = ChatSession(
        title=request.title,
        user_id=user.id if user else None,
        tenant_id=user.tenant_id if user else None,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all messages for a chat session."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return result.scalars().all()


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def create_message(
    session_id: str,
    request: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Send a message in a chat session."""
    # Verify session exists
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Save user message
    message = ChatMessage(
        session_id=session_id,
        role=MessageRole.USER,
        content=request.content,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)

    # Update session title if it's the first message
    if session.title == "New Chat":
        session.title = request.content[:100]

    return message


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session and its messages."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Delete messages first
    messages = await db.execute(select(ChatMessage).where(ChatMessage.session_id == session_id))
    for msg in messages.scalars().all():
        await db.delete(msg)

    await db.delete(session)
    return {"status": "deleted"}
