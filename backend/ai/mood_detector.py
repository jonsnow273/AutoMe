import logging
from typing import Dict, Any
from backend.ai.groq_client import groq_client
from backend.ai.prompts import MOOD_DETECTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def detect_mood(incoming_text: str) -> Dict[str, Any]:
    """Analyze the sender's emotional mood from their message."""
    prompt = f"Message to analyze: \"{incoming_text}\""

    try:
        result = await groq_client.generate_json(prompt, system_prompt=MOOD_DETECTION_SYSTEM_PROMPT)
        mood = result.get("mood", "neutral").lower()
        if mood not in ["positive", "neutral", "negative", "urgent"]:
            mood = "neutral"

        return {
            "mood": mood,
            "confidence": float(result.get("confidence", 0.8)),
            "notes": result.get("notes", ""),
        }
    except Exception as e:
        logger.warning(f"Mood detection failed, falling back to heuristics: {e}")
        text_lower = incoming_text.lower()
        if any(w in text_lower for w in ["great", "awesome", "haha", "lol", "nice", "love", "thanks"]):
            mood = "positive"
        elif any(w in text_lower for w in ["bad", "angry", "hate", "terrible", "sad", "disappointed", "annoyed"]):
            mood = "negative"
        elif any(w in text_lower for w in ["urgent", "help", "hurry", "asap"]):
            mood = "urgent"
        else:
            mood = "neutral"

        return {
            "mood": mood,
            "confidence": 0.7,
            "notes": "heuristic fallback",
        }
