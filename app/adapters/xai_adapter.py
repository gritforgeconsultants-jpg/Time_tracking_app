"""
xAI / Grok adapter for API usage tracking.

STATUS: Requires XAI_API_KEY in environment to function.
When not configured, displays as "not connected" in the UI.

xAI uses an OpenAI-compatible API format.
"""
from datetime import datetime, timezone
from decimal import Decimal
from app.adapters.base import BaseAdapter, APICallResult


class XAIAdapter(BaseAdapter):
    provider_name = "xai"

    async def proxy_request(self, payload: dict, api_key: str) -> APICallResult:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=120,
            )

        data = resp.json()
        usage = data.get("usage", {})
        status = "success" if resp.status_code == 200 else "error"

        return APICallResult(
            provider="xai",
            model=data.get("model", payload.get("model", "unknown")),
            provider_request_id=resp.headers.get("x-request-id"),
            timestamp=datetime.now(timezone.utc),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            cached_tokens=0,
            other_units=None,
            duration_ms=int(resp.elapsed.total_seconds() * 1000) if resp.elapsed else None,
            status=status,
            reported_cost=None,
        )

    def parse_response_headers(self, headers: dict) -> dict:
        return {"request_id": headers.get("x-request-id")}
