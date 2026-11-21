import logging
from typing import Optional, List, Dict, Any
from backend.ai.groq_client import groq_client
from backend.ai.prompts import CLASSIFICATION_SYSTEM_PROMPT
from backend.models.message import RelationshipType, MessageUrgency

logger = logging.getLogger(__name__)


async def classify_message(
    incoming_text: str,
    sender_name: str,
    recent_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Classify relationship, urgency, and intent of an incoming message."""
    prompt = f"Sender Name: {sender_name}\nIncoming Message: \"{incoming_text}\""

    if recent_history:
        formatted_history = "\n".join([f"- {m.get('direction', 'incoming')}: {m.get('content', '')}" for m in recent_history[-3:]])
        prompt += f"\nRecent Context:\n{formatted_history}"

    try:
        result = await groq_client.generate_json(prompt, system_prompt=CLASSIFICATION_SYSTEM_PROMPT)
        # Validate values against enums
        rel = result.get("relationship", "friend").lower()
        if rel not in ["friend", "acquaintance", "stranger"]:
            rel = "friend"

        urg = result.get("urgency", "low").lower()
        if urg not in ["low", "medium", "high", "emergency"]:
            urg = "low"

        return {
            "relationship": rel,
            "urgency": urg,
            "intent": result.get("intent", "statement"),
            "summary": result.get("summary", ""),
        }
    except Exception as e:
        logger.warning(f"AI classification failed, falling back to heuristics: {e}")
        # Rule-based fallback
        text_lower = incoming_text.lower()
        urgency = "low"
        if any(w in text_lower for w in ["emergency", "hospital", "urgent", "call me now", "asap"]):
            urgency = "emergency"
        elif any(w in text_lower for w in ["today", "where are you", "soon", "quick question"]):
            urgency = "medium"

        return {
            "relationship": "friend",
            "urgency": urgency,
            "intent": "question" if "?" in incoming_text else "statement",
            "summary": incoming_text[:60],
        }
