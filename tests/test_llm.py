from __future__ import annotations

import json

import httpx
import pytest

from shipwatch.config import LLMSettings
from shipwatch.llm import BriefingOut, LLMClient, LLMError


def _handler(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content.decode())
    messages = payload["messages"]
    last = messages[-1]["content"]
    if "invalid" in last.lower() and any(m.get("role") == "assistant" for m in messages):
        body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "title": "ok",
                                "sections": [
                                    {
                                        "heading": "Prices",
                                        "item_ids": ["a"],
                                        "claims": [{"text": "cut", "source_item_ids": ["a"]}],
                                    }
                                ],
                            }
                        )
                    }
                }
            ]
        }
        return httpx.Response(200, json=body)
    if request.url.path.endswith("/chat/completions") and not any(
        m.get("role") == "assistant" for m in messages
    ):
        body = {"choices": [{"message": {"content": "not-json"}}]}
        return httpx.Response(200, json=body)
    return httpx.Response(500, json={"error": "nope"})


def test_complete_json_retries_then_validates() -> None:
    transport = httpx.MockTransport(_handler)
    client = LLMClient(
        LLMSettings(base_url="https://llm.example/v1", retries=2), transport=transport
    )
    data = client.complete_json(
        [{"role": "user", "content": "brief these items"}],
        BriefingOut,
    )
    assert data["title"] == "ok"
    assert data["sections"][0]["claims"][0]["source_item_ids"] == ["a"]
    client.close()


def test_complete_json_raises_after_retries() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "still-bad"}}]})

    client = LLMClient(
        LLMSettings(base_url="https://llm.example/v1", retries=1),
        transport=httpx.MockTransport(fail),
    )
    with pytest.raises(LLMError):
        client.complete_json([{"role": "user", "content": "x"}], BriefingOut)
    client.close()
