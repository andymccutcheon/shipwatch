"""OpenAI-compatible chat client with JSON schema validation and retries."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from shipwatch.config import LLMSettings


class LLMError(RuntimeError):
    pass


class CharacterizationOut(BaseModel):
    kind: str
    rationale: str = ""


class FactOut(BaseModel):
    text: str
    kind: str = "other"
    evidence: str = ""


class FactsOut(BaseModel):
    facts: list[FactOut]


class ClaimOut(BaseModel):
    text: str
    source_item_ids: list[str]


class SectionOut(BaseModel):
    heading: str
    item_ids: list[str] = []
    claims: list[ClaimOut]
    score: float = 0.0


class BriefingOut(BaseModel):
    title: str
    sections: list[SectionOut]


class LLMClient:
    def __init__(
        self,
        settings: LLMSettings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self._client = httpx.Client(
            base_url=settings.base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {settings.api_key()}",
                "Content-Type": "application/json",
            },
            timeout=settings.timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def complete_json(
        self, messages: list[dict[str, str]], model: type[BaseModel]
    ) -> dict[str, Any]:
        conversation = list(messages)
        last_error = "unknown error"
        raw = ""
        for _attempt in range(self.settings.retries + 1):
            raw = self._chat(conversation)
            try:
                data = _parse_json(raw)
                validated = model.model_validate(data)
                return validated.model_dump()
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = str(exc)
                conversation = conversation + [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": (
                            f"Your previous output was invalid: {last_error}. "
                            "Return a single JSON object that matches the schema. No markdown."
                        ),
                    },
                ]
        raise LLMError(f"LLM JSON failed after retries: {last_error}\n{raw[:400]}")

    def _chat(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
            "response_format": {"type": "json_object"},
        }
        try:
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM HTTP error: {exc}") from exc
        body = response.json()
        try:
            return str(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"unexpected LLM response: {body!r}") from exc


def _parse_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def characterization_messages(title: str, content: str) -> list[dict[str, str]]:
    kinds = (
        "launch, model_release, pricing_change, deprecation, "
        "api_change, availability, security, non_shipment, other"
    )
    return [
        {
            "role": "system",
            "content": (
                "Classify a changelog item. Return JSON "
                '{"kind": "...", "rationale": "..."}. '
                f"kind must be one of: {kinds}. "
                "Use non_shipment for customer case studies, how-X-ships-faster "
                "stories, promo, webinars, hiring, and opinion posts."
            ),
        },
        {"role": "user", "content": f"Title: {title}\n\n{content[:4000]}"},
    ]


def facts_messages(title: str, content: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Extract atomic facts from a changelog. Return JSON "
                '{"facts": [{"text": "...", "kind": "...", "evidence": "verbatim snippet"}]} . '
                "Every fact must be supported by the evidence snippet. Do not invent."
            ),
        },
        {"role": "user", "content": f"Title: {title}\n\n{content[:6000]}"},
    ]


def briefing_messages(item_payload: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Write a weekly shipping briefing. Return JSON with keys title and sections. "
                "Each section has heading, score, item_ids, and claims. "
                "Each claim has text and source_item_ids. "
                "Every claim MUST cite one or more provided item ids. "
                "Do not add facts that are not in the source items. "
                "Prefer concrete shipped changes over vague marketing."
            ),
        },
        {
            "role": "user",
            "content": json.dumps({"items": item_payload}, ensure_ascii=False),
        },
    ]
