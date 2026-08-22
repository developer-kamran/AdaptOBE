"""AI-generated CLO wording via the Groq API (CLAUDE.md-adjacent Module: faculty modules round).

Unlike every other "AI" feature in this codebase (CLO<->PLO mapping, question<->CLO
tagging), which is `all-MiniLM-L6-v2` embedding *similarity search*, this module does
real text *generation* -- there is no way to produce a brand-new CLO's wording from a
topic/PLO/requirements by comparing existing embeddings. A generative LLM call is
unavoidable here.

The Groq client is lazily constructed (mirrors `app/ml/embeddings.py`'s lazy model
load) so importing this module -- and therefore booting the API or collecting tests
-- never requires a real API key. `AsyncGroq` is natively async, unlike the
CPU-bound sentence-transformer encode, so no `asyncio.to_thread` offload is needed
here.
"""

import json

from dataclasses import dataclass

from app.core.config import settings
from app.schemas.clo import BLOOM_LEVELS
from app.services.exceptions import LLMGenerationError

#: Picked from this account's actual live model list (`client.models.list()`)
#: rather than a name that looked plausible -- Groq deprecates/rotates models
#: over time, and a stale name 404s with "model_not_found" rather than falling
#: back gracefully. Re-check `client.models.list()` if this ever 404s again.
MODEL_NAME = "openai/gpt-oss-120b"

_client = None


def get_client():
    """Return the shared AsyncGroq client, constructing it on first use."""
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise LLMGenerationError(
                "GROQ_API_KEY is not configured -- set it in backend/.env to use "
                "AI CLO generation."
            )
        from groq import AsyncGroq

        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


@dataclass
class CloSuggestion:
    title: str
    description: str
    bloom_level: str


def _build_prompt(topic: str, requirements: str, plo_texts: list[str]) -> str:
    plo_block = "\n".join(f"- {text}" for text in plo_texts)
    requirements_block = requirements.strip() or "None specified."
    return (
        "You are an academic curriculum designer writing a single Course Learning "
        "Outcome (CLO) for a university computing course.\n\n"
        f"Topic / concept the CLO should cover:\n{topic}\n\n"
        f"Programme Learning Outcome(s) this CLO should support:\n{plo_block}\n\n"
        f"Additional requirements from the instructor:\n{requirements_block}\n\n"
        "Write ONE CLO. Respond with ONLY a JSON object, no other text, in exactly "
        "this shape:\n"
        '{"title": "short outcome title (max ~10 words)", '
        '"description": "one or two sentences, starting with a measurable action '
        'verb, describing what a student will be able to do", '
        f'"bloom_level": "one of {list(BLOOM_LEVELS)}"}}'
    )


def _parse_response(raw: str) -> CloSuggestion:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise LLMGenerationError("The AI response was not valid JSON") from exc

    title = str(data.get("title") or "").strip()
    description = str(data.get("description") or "").strip()
    bloom_level = str(data.get("bloom_level") or "").strip()

    if not title or not description:
        raise LLMGenerationError("The AI response was missing a title or description")
    if bloom_level not in BLOOM_LEVELS:
        raise LLMGenerationError(
            f"The AI returned an unrecognized Bloom level: {bloom_level!r}"
        )

    return CloSuggestion(title=title, description=description, bloom_level=bloom_level)


async def agenerate_clo_suggestion(
    topic: str, requirements: str, plo_texts: list[str]
) -> CloSuggestion:
    """Ask Groq for a CLO suggestion. Raises LLMGenerationError on any failure --
    network, API, or malformed-output -- so callers only need to handle one type."""
    client = get_client()
    prompt = _build_prompt(topic, requirements, plo_texts)

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_completion_tokens=400,
        )
    except Exception as exc:  # noqa: BLE001 - any SDK/network failure becomes one typed error
        raise LLMGenerationError(f"AI CLO generation request failed: {exc}") from exc

    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise LLMGenerationError("The AI returned an empty response")

    return _parse_response(content)
