from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, case
from typing import Optional, List
from pydantic import BaseModel

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.models.contact import Contact
from backend.models.message import Message, MessageDirection

router = APIRouter(prefix="/contacts", tags=["Contacts"])


# ─── Schemas ────────────────────────────────────────────────────────────────

class ContactResponse(BaseModel):
    id: int
    platform: str
    platform_user_id: str
    username: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    relationship_type: Optional[str]
    last_interaction: Optional[str]
    message_count: int
    unread_count: int
    last_message_preview: Optional[str]
    last_message_time: Optional[str]

    class Config:
        from_attributes = True


class ContactsListResponse(BaseModel):
    contacts: List[ContactResponse]
    total: int


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("", response_model=ContactsListResponse)
def list_contacts(
    platform: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all contacts with last message preview and unread count."""
    # Subquery for unread counts per contact
    unread_subq = db.query(
        Message.contact_id,
        func.count(Message.id).label("unread_count")
    ).filter(
        Message.user_id == current_user.id,
        Message.direction == MessageDirection.INCOMING,
        Message.is_read == False
    ).group_by(Message.contact_id).subquery()

    # Subquery for last message per contact
    last_msg_subq = db.query(
        Message.contact_id,
        func.max(Message.timestamp).label("last_time"),
        func.max(Message.id).label("last_id")
    ).filter(
        Message.user_id == current_user.id
    ).group_by(Message.contact_id).subquery()

    # Main query
    query = db.query(
        Contact,
        unread_subq.c.unread_count,
        last_msg_subq.c.last_time,
        Message.content.label("last_content")
    ).outerjoin(
        unread_subq, Contact.id == unread_subq.c.contact_id
    ).outerjoin(
        last_msg_subq, Contact.id == last_msg_subq.c.contact_id
    ).outerjoin(
        Message, Message.id == last_msg_subq.c.last_id
    ).filter(Contact.user_id == current_user.id)

    if platform:
        query = query.filter(Contact.platform == platform)
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Contact.username).like(search_term),
                func.lower(Contact.display_name).like(search_term),
            )
        )

    # Order by last interaction desc (most recent first)
    query = query.order_by(desc(last_msg_subq.c.last_time))

    contacts_data = query.all()

    result = []
    for contact, unread_count, last_time, last_content in contacts_data:
        result.append(ContactResponse(
            id=contact.id,
            platform=contact.platform,
            platform_user_id=contact.platform_user_id,
            username=contact.username,
            display_name=contact.display_name,
            avatar_url=contact.avatar_url,
            relationship_type=contact.relationship_type.value if contact.relationship_type else None,
            last_interaction=contact.last_interaction.isoformat() if contact.last_interaction else None,
            message_count=contact.message_count,
            unread_count=unread_count or 0,
            last_message_preview=last_content[:100] if last_content else None,
            last_message_time=last_time.isoformat() if last_time else None,
        ))

    return ContactsListResponse(contacts=result, total=len(result))


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single contact with details."""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.user_id == current_user.id
    ).first()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Get unread count
    unread_count = db.query(func.count(Message.id)).filter(
        Message.contact_id == contact_id,
        Message.direction == MessageDirection.INCOMING,
        Message.is_read == False
    ).scalar() or 0

    # Get last message
    last_msg = db.query(Message).filter(
        Message.contact_id == contact_id
    ).order_by(desc(Message.timestamp)).first()

    return ContactResponse(
        id=contact.id,
        platform=contact.platform,
        platform_user_id=contact.platform_user_id,
        username=contact.username,
        display_name=contact.display_name,
        avatar_url=contact.avatar_url,
        relationship_type=contact.relationship_type.value if contact.relationship_type else None,
        last_interaction=contact.last_interaction.isoformat() if contact.last_interaction else None,
        message_count=contact.message_count,
        unread_count=unread_count,
        last_message_preview=last_msg.content[:100] if last_msg else None,
        last_message_time=last_msg.timestamp.isoformat() if last_msg else None,
    )