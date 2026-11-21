import re
import json
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.contact import Contact, RelationshipType
from backend.models.message import Message, MessageDirection, MessageMood, MessageUrgency
from backend.ai.groq_client import groq_client
from backend.ai.prompts import REPLY_GENERATION_SYSTEM_PROMPT
from backend.ai.classifier import classify_message
from backend.ai.mood_detector import detect_mood
from backend.ai.style_learner import get_or_create_style_profile

logger = logging.getLogger(__name__)

# Regex to strictly strip any emoji characters from replies
EMOJI_REGEX = re.compile(
    r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]",
    flags=re.UNICODE,
)


def remove_emojis(text: str) -> str:
    """Ensure strict compliance with the no-emojis rule."""
    cleaned = EMOJI_REGEX.sub("", text)
    # Clean up double spaces caused by emoji removal
    return re.sub(r"\s+", " ", cleaned).strip()


async def generate_reply(
    user_id: int,
    incoming_text: str,
    contact: Contact,
    db: Session,
    platform_type: str = "general",
    custom_busy_note: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a contextual, personalized auto-reply tailored to the user's learned texting style."""
    # 1. Fetch user style profile
    profile = get_or_create_style_profile(user_id, db)

    # 2. Fetch recent conversation history with this contact
    recent_messages = (
        db.query(Message)
        .filter(
            Message.user_id == user_id,
            Message.contact_id == contact.id,
        )
        .order_by(desc(Message.timestamp))
        .limit(5)
        .all()
    )
    # Reverse to chronological order
    recent_messages = list(reversed(recent_messages))
    history_tuples = [
        {"direction": m.direction.value, "content": m.content}
        for m in recent_messages
        if m.content
    ]

    # 3. Classify message intent & mood
    sender_name = contact.display_name or contact.username or "Friend"
    classification = await classify_message(incoming_text, sender_name, history_tuples)
    mood_info = await detect_mood(incoming_text)

    # 4. Assemble prompt
    common_phrases = json.loads(profile.common_phrases) if profile.common_phrases else []
    openers = json.loads(profile.opener_patterns) if profile.opener_patterns else []
    closers = json.loads(profile.closer_patterns) if profile.closer_patterns else []

    user_style_desc = f"""
- Tone: {profile.tone} (Formality Score: {profile.formality_score:.2f} on 0-1 scale)
- Typical message length: ~{int(profile.avg_message_length)} words
- Favorite phrases: {", ".join(common_phrases[:4]) if common_phrases else "none"}
- Frequent openers: {", ".join(openers[:3]) if openers else "none"}
- Frequent closers: {", ".join(closers[:3]) if closers else "none"}
"""

    context_prompt = f"""
USER'S LEARNED TEXTING STYLE:
{user_style_desc}

SENDER INFORMATION:
- Name: {sender_name}
- Platform: {platform_type}
- Classified Relationship: {classification.get("relationship", "friend")}
- Sender Mood: {mood_info.get("mood", "neutral")}
- Message Urgency: {classification.get("urgency", "low")}

CONVERSATION CONTEXT:
"""
    if history_tuples:
        for m in history_tuples:
            speaker = "Me" if m["direction"] == "outgoing" else sender_name
            context_prompt += f"{speaker}: {m['content']}\n"
    else:
        context_prompt += "(No previous messages)\n"

    context_prompt += f"\nINCOMING MESSAGE TO REPLY TO:\n{sender_name}: \"{incoming_text}\"\n"

    if custom_busy_note:
        context_prompt += f"\nCURRENT BUSY NOTE / STATUS: \"{custom_busy_note}\"\n"

    context_prompt += "\nDraft the response now as a JSON object."

    try:
        response_json = await groq_client.generate_json(
            context_prompt,
            system_prompt=REPLY_GENERATION_SYSTEM_PROMPT,
            temperature=0.7,
        )

        reply_raw = response_json.get("reply", "")
        reply_clean = remove_emojis(reply_raw)

        # Fallback if AI returned empty string
        if not reply_clean:
            reply_clean = custom_busy_note or "Hey! I'm away from my screen right now, will get back to you shortly."

        confidence = int(response_json.get("confidence", 85))

        return {
            "reply": reply_clean,
            "confidence": confidence,
            "mood": mood_info.get("mood", "neutral"),
            "urgency": classification.get("urgency", "low"),
            "relationship": classification.get("relationship", "friend"),
            "reasoning": response_json.get("reasoning", "Style-matched contextual response"),
        }

    except Exception as e:
        logger.error(f"Error in reply generator: {e}")
        fallback_text = custom_busy_note or "Hey, currently tied up with work right now. Will text you back as soon as I can!"
        return {
            "reply": fallback_text,
            "confidence": 70,
            "mood": mood_info.get("mood", "neutral"),
            "urgency": classification.get("urgency", "low"),
            "relationship": "friend",
            "reasoning": "Fallback response due to generation error",
        }
