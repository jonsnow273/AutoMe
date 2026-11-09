from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.models.message import Message, MessageDirection, MessageMood, MessageUrgency, RelationshipType
from backend.models.contact import Contact
from backend.models.platform import Platform, PlatformType
from backend.connectors.session_manager import send_discord_dm

router = APIRouter(prefix="/messages", tags=["Messages"])


# ─── Schemas ────────────────────────────────────────────────────────────────

class ContactSummary(BaseModel):
    id: int
    platform: str
    platform_user_id: str
    username: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    relationship_type: Optional[str]
    last_interaction: Optional[str]
    unread_count: int = 0

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    platform: str
    platform_message_id: str
    contact_id: Optional[int]
    content: str
    direction: str
    timestamp: str
    is_read: bool
    mood: Optional[str]
    urgency: Optional[str]
    relationship_type: Optional[str]
    suggested_reply: Optional[str]
    reply_confidence: Optional[int]

    class Config:
        from_attributes = True


class MessagesListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class MarkReadRequest(BaseModel):
    message_ids: List[int]


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("", response_model=MessagesListResponse)
def list_messages(
    platform: Optional[str] = Query(None),
    contact_id: Optional[int] = Query(None),
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List messages with filters and pagination."""
    query = db.query(Message).filter(Message.user_id == current_user.id)

    if platform:
        query = query.filter(Message.platform == platform)
    if contact_id:
        query = query.filter(Message.contact_id == contact_id)
    if unread_only:
        query = query.filter(Message.is_read == False)

    # Order by timestamp desc (newest first)
    query = query.order_by(desc(Message.timestamp))

    total = query.count()
    messages = query.offset((page - 1) * page_size).limit(page_size).all()

    return MessagesListResponse(
        messages=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,
    )


@router.get("/conversation/{contact_id}", response_model=MessagesListResponse)
def get_conversation(
    contact_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get messages for a specific contact (conversation view)."""
    # Verify contact belongs to user
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.user_id == current_user.id
    ).first()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    query = db.query(Message).filter(
        Message.user_id == current_user.id,
        Message.contact_id == contact_id
    ).order_by(desc(Message.timestamp))

    total = query.count()
    messages = query.offset((page - 1) * page_size).limit(page_size).all()

    # Mark as read (incoming messages only)
    db.query(Message).filter(
        Message.user_id == current_user.id,
        Message.contact_id == contact_id,
        Message.direction == MessageDirection.INCOMING,
        Message.is_read == False
    ).update({"is_read": True})
    db.commit()

    return MessagesListResponse(
        messages=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,
    )


@router.post("/{message_id}/read", status_code=204)
def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single message as read."""
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.user_id == current_user.id
    ).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    message.is_read = True
    db.commit()


@router.post("/read/batch", status_code=204)
def mark_messages_read(
    data: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark multiple messages as read."""
    db.query(Message).filter(
        Message.id.in_(data.message_ids),
        Message.user_id == current_user.id
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()


@router.get("/unread/count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get total unread message count for badge."""
    count = db.query(func.count(Message.id)).filter(
        Message.user_id == current_user.id,
        Message.direction == MessageDirection.INCOMING,
        Message.is_read == False
    ).scalar()

    return {"unread_count": count or 0}


class SendMessageRequest(BaseModel):
    contact_id: int
    content: str


@router.post("/send", status_code=201)
async def send_message(
    data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message to a contact via their platform."""
    # Verify contact belongs to user
    contact = db.query(Contact).filter(
        Contact.id == data.contact_id,
        Contact.user_id == current_user.id
    ).first()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Get user's platform for this contact
    platform = db.query(Platform).filter(
        Platform.user_id == current_user.id,
        Platform.platform_type == contact.platform,
        Platform.is_connected == True
    ).first()

    if not platform:
        raise HTTPException(status_code=400, detail=f"{contact.platform} not connected")

    # Send via platform-specific method
    success = False
    if contact.platform == "discord":
        success = await send_discord_dm(current_user.id, contact.platform_user_id, data.content)
    else:
        raise HTTPException(status_code=400, detail=f"Sending not implemented for {contact.platform}")

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send message")

    # Save outgoing message to DB
    db_message = Message(
        user_id=current_user.id,
        platform=contact.platform,
        platform_message_id=f"out_{int(datetime.utcnow().timestamp() * 1000)}",
        contact_id=contact.id,
        content=data.content,
        direction=MessageDirection.OUTGOING,
        is_read=True,  # Outgoing messages are "read" by definition
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    return {"status": "sent", "message_id": db_message.id}


# Internal endpoint for Discord bot to notify new messages
@router.post("/internal/receive", status_code=202)
async def internal_receive_message(
    payload: dict,
    # No auth — validated by X-Internal-Key header in production
):
    """Internal endpoint for bot processes to push new messages.
    The bot saves to DB directly, this just acknowledges receipt.
    In production with Socket.IO, you'd emit event here."""
    return {"status": "received"}