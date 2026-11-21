import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.models.message import Message, MessageMood, MessageUrgency, RelationshipType
from backend.models.contact import Contact
from backend.models.style_profile import StyleProfile
from backend.ai.style_learner import get_or_create_style_profile, learn_user_style
from backend.ai.reply_generator import generate_reply

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


class StyleProfileResponse(BaseModel):
    tone: str
    formality_score: float
    avg_message_length: float
    common_phrases: List[str]
    opener_patterns: List[str]
    closer_patterns: List[str]
    sample_size: int
    last_analyzed: Optional[str]


class SuggestReplyRequest(BaseModel):
    message_id: Optional[int] = None
    contact_id: Optional[int] = None
    incoming_text: Optional[str] = None


class SuggestReplyResponse(BaseModel):
    reply: str
    confidence: int
    mood: str
    urgency: str
    relationship: str
    reasoning: Optional[str]


@router.get("/style-profile", response_model=StyleProfileResponse)
def get_style_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the current user's learned texting style profile."""
    profile = get_or_create_style_profile(current_user.id, db)
    return StyleProfileResponse(
        tone=profile.tone or "casual",
        formality_score=profile.formality_score or 0.35,
        avg_message_length=profile.avg_message_length or 8.0,
        common_phrases=json.loads(profile.common_phrases) if profile.common_phrases else [],
        opener_patterns=json.loads(profile.opener_patterns) if profile.opener_patterns else [],
        closer_patterns=json.loads(profile.closer_patterns) if profile.closer_patterns else [],
        sample_size=profile.sample_size or 0,
        last_analyzed=profile.last_analyzed.isoformat() if profile.last_analyzed else None,
    )


@router.post("/learn-style", response_model=StyleProfileResponse)
async def trigger_learn_style(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger AI analysis of sent messages to update user's StyleProfile."""
    profile = await learn_user_style(current_user.id, db)
    return StyleProfileResponse(
        tone=profile.tone or "casual",
        formality_score=profile.formality_score or 0.35,
        avg_message_length=profile.avg_message_length or 8.0,
        common_phrases=json.loads(profile.common_phrases) if profile.common_phrases else [],
        opener_patterns=json.loads(profile.opener_patterns) if profile.opener_patterns else [],
        closer_patterns=json.loads(profile.closer_patterns) if profile.closer_patterns else [],
        sample_size=profile.sample_size or 0,
        last_analyzed=profile.last_analyzed.isoformat() if profile.last_analyzed else None,
    )


@router.post("/suggest-reply", response_model=SuggestReplyResponse)
async def suggest_reply(
    data: SuggestReplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an on-demand AI reply suggestion for an incoming message or contact."""
    msg = None
    contact = None
    incoming_text = ""

    if data.message_id:
        msg = db.query(Message).filter(
            Message.id == data.message_id,
            Message.user_id == current_user.id
        ).first()
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")
        incoming_text = msg.content
        if msg.contact_id:
            contact = db.query(Contact).filter(Contact.id == msg.contact_id).first()

    if not contact and data.contact_id:
        contact = db.query(Contact).filter(
            Contact.id == data.contact_id,
            Contact.user_id == current_user.id
        ).first()

    if not incoming_text and data.incoming_text:
        incoming_text = data.incoming_text

    if not incoming_text:
        raise HTTPException(status_code=400, detail="No message content provided for suggestion")

    if not contact:
        contact = Contact(
            user_id=current_user.id,
            platform="unknown",
            platform_user_id="unknown",
            username="Friend",
            display_name="Friend",
        )

    result = await generate_reply(
        user_id=current_user.id,
        incoming_text=incoming_text,
        contact=contact,
        db=db,
        platform_type=msg.platform if msg else contact.platform,
    )

    # If linked to a message in the DB, store the suggested reply and classification
    if msg:
        msg.suggested_reply = result["reply"]
        msg.reply_confidence = result["confidence"]
        try:
            msg.mood = MessageMood(result["mood"])
        except Exception:
            pass
        try:
            msg.urgency = MessageUrgency(result["urgency"])
        except Exception:
            pass
        try:
            msg.relationship_type = RelationshipType(result["relationship"])
        except Exception:
            pass
        db.commit()

    return SuggestReplyResponse(
        reply=result["reply"],
        confidence=result["confidence"],
        mood=result["mood"],
        urgency=result["urgency"],
        relationship=result["relationship"],
        reasoning=result.get("reasoning"),
    )
