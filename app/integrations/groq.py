"""Groq integration for LLM inference via OpenAI-compatible API."""
import json
import re
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

_BASE_URL = "https://api.groq.com/openai/v1"


@dataclass(frozen=True)
class ModerationResult:
    score: float
    flagged: bool
    reason: str


class GroqClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.groq_api_key.get_secret_value()
        self._model = settings.groq_model
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _chat(self, system: str, user: str, max_tokens: int) -> str:
        payload = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{_BASE_URL}/chat/completions",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()
        return ""

    async def generate_lesson_summary(self, transcript_text: str) -> str:
        system = (
            "Você é um assistente que resume aulas. "
            "Crie um resumo conciso em português com bullets. "
            "Máximo 5 bullets. Foque nos pontos principais."
        )
        return await self._chat(
            system=system,
            user=f"Resuma esta transcrição de aula:\n\n{transcript_text}",
            max_tokens=512,
        )

    async def moderate_content(self, text: str) -> ModerationResult:
        system = (
            "Você é um moderador de conteúdo. "
            "Avalie o texto abaixo e responda APENAS com um JSON no formato: "
            '{"score": float_entre_0_e_1, "flagged": bool, "reason": "string"}. '
            "Score >= 0.7 significa conteúdo tóxico/inadequado."
        )
        raw = await self._chat(
            system=system,
            user=f"Avalie este conteúdo:\n\n{text}",
            max_tokens=256,
        )
        if not raw:
            return ModerationResult(score=0.0, flagged=False, reason="empty response")
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                raw = match.group(0)
            data = json.loads(raw)
            score = float(data.get("score", 0))
            flagged = bool(data.get("flagged", False))
            reason = str(data.get("reason", ""))
            if score >= 0.7 and not flagged:
                flagged = True
            return ModerationResult(score=score, flagged=flagged, reason=reason)
        except Exception:
            return ModerationResult(score=0.0, flagged=False, reason="parse error")
