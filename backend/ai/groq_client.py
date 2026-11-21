import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from groq import Groq

logger = logging.getLogger(__name__)

# List of preferred models with automatic fallback
CANDIDATE_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]


class GroqClient:
    """Async wrapper for the Groq API supporting fallback models and JSON extraction."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API")
        self._client: Optional[Groq] = None

    def _get_client(self) -> Groq:
        if not self._client:
            if not self.api_key:
                raise ValueError("GROQ_API_KEY is not configured in the environment or .env file.")
            self._client = Groq(api_key=self.api_key)
        return self._client

    def _sync_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 300,
        response_format: Optional[dict] = None,
    ) -> str:
        client = self._get_client()
        last_error = None

        for model_name in CANDIDATE_MODELS:
            try:
                kwargs = {
                    "messages": messages,
                    "model": model_name,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                completion = client.chat.completions.create(**kwargs)
                content = completion.choices[0].message.content or ""
                return content.strip()
            except Exception as e:
                logger.warning(f"Groq model {model_name} failed: {e}. Trying next candidate...")
                last_error = e

        raise RuntimeError(f"All Groq candidate models failed. Last error: {last_error}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 300,
    ) -> str:
        """Generate text completion asynchronously."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return await asyncio.to_thread(
            self._sync_chat_completion,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        """Generate and parse structured JSON response."""
        messages = []
        full_system = (system_prompt or "") + "\nRespond with valid JSON only. Do not include markdown formatting or commentary."
        messages.append({"role": "system", "content": full_system.strip()})
        messages.append({"role": "user", "content": prompt})

        raw = await asyncio.to_thread(
            self._sync_chat_completion,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Fallback cleanup for code fences if any
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())


# Global singleton instance
groq_client = GroqClient()
