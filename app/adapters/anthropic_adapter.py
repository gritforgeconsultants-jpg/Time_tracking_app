"""
Anthropic adapter for API usage tracking.

STATUS: Requires ANTHROPIC_API_KEY in environment to function.
When not configured, displays as "not connected" in the UI.

Parses Anthropic API responses to extract:
- Model used
- Input/output token counts (including cache_creation and cache_read)
- Request ID (request-id header)
"""
from datetime import datetime, timezone
from decimal import Decimal
from app.adapters.base import BaseAdapter, APICallResult


class AnthropicAdapter(BaseAdapter):
    provider_name = "anthropic"

    async def proxy_request(self, payload: dict, api_key: str) -> APICallResult:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                timeout=120,
            )

        data = resp.json()
        usage = data.get("usage", {})
        status = "success" if resp.status_code == 200 else "error"

        cached = usage.get("cache_read_input_tokens", 0)

        return APICallResult(
            provider="anthropic",
            model=data.get("model", payload.get("model", "unknown")),
            provider_request_id=resp.headers.get("request-id"),
            timestamp=datetime.now(timezone.utc),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cached_tokens=cached,
            other_units={
                "cache_creation_tokens": usage.get("cache_creation_input_tokens", 0),
            } if usage.get("cache_creation_input_tokens") else None,
            duration_ms=int(resp.elapsed.total_seconds() * 1000) if resp.elapsed else None,
            status=status,
            reported_cost=None,
        )

    def parse_response_headers(self, headers: dict) -> dict:
        return {"request_id": headers.get("request-id")}
