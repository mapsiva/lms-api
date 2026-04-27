"""Anthropic Claude integration for summaries and moderation."""
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.core.config import get_settings


@dataclass(frozen=True)
class ModerationResult:
    score: float
    flagged: bool
    reason: str


class AnthropicClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())
        self._model = "claude-haiku-4-5-20251001"

    async def generate_lesson_summary(self, transcript_text: str) -> str:
        """Generate concise bullet-point summary in Portuguese."""
        system_prompt = (
            "Você é um assistente que resume aulas. "
            "Crie um resumo conciso em português com bullets. "
            "Máximo 5 bullets. Foque nos pontos principais."
        )
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"Resuma esta transcrição de aula:\n\n{transcript_text}",
                }
            ],
        )
        content_blocks = resp.content
        if content_blocks and hasattr(content_blocks[0], "text"):
            return content_blocks[0].text.strip()
        return ""

    async def moderate_content(self, text: str) -> ModerationResult:
        """Score content toxicity. Threshold 0.7 for flagging."""
        system_prompt = (
            "Você é um moderador de conteúdo. "
            "Avalie o texto abaixo e responda APENAS com um JSON no formato: "
            '{"score": float_entre_0_e_1, "flagged": bool, "reason": "string"}. '
            "Score >= 0.7 significa conteúdo tóxico/inadequado."
        )
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=256,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Avalie este conteúdo:\n\n{text}",
                }
            ],
        )
        content_blocks = resp.content
        if not content_blocks or not hasattr(content_blocks[0], "text"):
            return ModerationResult(score=0.0, flagged=False, reason="empty response")

        raw = content_blocks[0].text.strip()
        import json
        import re

        try:
            # Extract JSON from possible markdown fences
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
