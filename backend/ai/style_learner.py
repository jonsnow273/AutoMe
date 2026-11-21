import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.style_profile import StyleProfile
from backend.models.message import Message, MessageDirection
from backend.ai.groq_client import groq_client
from backend.ai.prompts import STYLE_ANALYSIS_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

DEFAULT_STYLE = {
    "avg_message_length": 8.5,
    "common_phrases": ["sounds good", "let me know", "all good", "sure thing"],
    "opener_patterns": ["hey", "yo", "hi"],
    "closer_patterns": ["talk soon", "see ya", "catch you later"],
    "tone": "casual",
    "formality_score": 0.35,
    "capitalization_style": "all_lowercase",
}


def get_or_create_style_profile(user_id: int, db: Session) -> StyleProfile:
    """Retrieve existing style profile or initialize a default one."""
    profile = db.query(StyleProfile).filter(StyleProfile.user_id == user_id).first()
    if not profile:
        profile = StyleProfile(
            user_id=user_id,
            avg_message_length=DEFAULT_STYLE["avg_message_length"],
            emoji_frequency=0.0,
            preferred_emojis=json.dumps([]),
            common_phrases=json.dumps(DEFAULT_STYLE["common_phrases"]),
            opener_patterns=json.dumps(DEFAULT_STYLE["opener_patterns"]),
            closer_patterns=json.dumps(DEFAULT_STYLE["closer_patterns"]),
            tone=DEFAULT_STYLE["tone"],
            formality_score=DEFAULT_STYLE["formality_score"],
            sample_size=0,
            last_analyzed=datetime.now(timezone.utc),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


async def learn_user_style(user_id: int, db: Session) -> StyleProfile:
    """Analyze the user's sent messages across all platforms and update their StyleProfile."""
    profile = get_or_create_style_profile(user_id, db)

    # Fetch up to 50 recent outgoing messages sent by the user
    messages = (
        db.query(Message)
        .filter(
            Message.user_id == user_id,
            Message.direction == MessageDirection.OUTGOING,
        )
        .order_by(desc(Message.timestamp))
        .limit(50)
        .all()
    )

    if len(messages) < 3:
        logger.info(f"User {user_id} has only {len(messages)} outgoing messages. Using baseline profile.")
        profile.sample_size = len(messages)
        db.commit()
        return profile

    sample_texts = [m.content.strip() for m in messages if m.content and len(m.content.strip()) > 1]
    prompt = f"User Outgoing Messages (Sample of {len(sample_texts)} messages):\n"
    prompt += "\n".join([f"- {txt}" for txt in sample_texts[:40]])

    try:
        analysis = await groq_client.generate_json(prompt, system_prompt=STYLE_ANALYSIS_SYSTEM_PROMPT)

        profile.avg_message_length = float(analysis.get("avg_message_length", 8.0))
        profile.common_phrases = json.dumps(analysis.get("common_phrases", DEFAULT_STYLE["common_phrases"]))
        profile.opener_patterns = json.dumps(analysis.get("opener_patterns", DEFAULT_STYLE["opener_patterns"]))
        profile.closer_patterns = json.dumps(analysis.get("closer_patterns", DEFAULT_STYLE["closer_patterns"]))
        profile.tone = str(analysis.get("tone", "casual"))
        profile.formality_score = float(analysis.get("formality_score", 0.35))
        profile.sample_size = len(sample_texts)
        profile.last_analyzed = datetime.now(timezone.utc)

        db.commit()
        db.refresh(profile)
        logger.info(f"Updated StyleProfile for user {user_id} based on {len(sample_texts)} messages.")
        return profile

    except Exception as e:
        logger.error(f"Error learning user style for user {user_id}: {e}")
        return profile
