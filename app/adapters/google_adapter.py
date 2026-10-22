"""
Google Gemini adapter for API usage tracking.

STATUS: Requires GOOGLE_AI_API_KEY in environment to function.
When not configured, displays as "not connected" in the UI.

Parses Gemini API responses to extract token usage from usageMetadata.
"""
from datetime import datetime, timezone
from decimal import Decimal
from app.adapters.base import BaseAdapter, APICallResult


class GoogleAdapter(BaseAdapter):
    provider_name = "google"

    async def proxy_request(self, payload: dict, api_key: str) -> APICallResult:
        import httpx

        model = payload.pop("model", "gemini-2.0-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=120)

        data = resp.json()
        usage = data.get("usageMetadata", {})
        status = "success" if resp.status_code == 200 else "error"

        return APICallResult(
            provider="google",
            model=model,
            provider_request_id=None,
            timestamp=datetime.now(timezone.utc),
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            cached_tokens=usage.get("cachedContentTokenCount", 0),
            other_units=None,
            duration_ms=int(resp.elapsed.total_seconds() * 1000) if resp.elapsed else None,
            status=status,
            reported_cost=None,
        )

    def parse_response_headers(self, headers: dict) -> dict:
        return {}
