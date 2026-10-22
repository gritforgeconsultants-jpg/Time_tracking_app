from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime


@dataclass
class APICallResult:
    provider: str
    model: str
    provider_request_id: str | None
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    other_units: dict | None
    duration_ms: int | None
    status: str  # success, error, partial
    reported_cost: Decimal | None  # provider-reported cost if available


class BaseAdapter(ABC):
    provider_name: str

    @abstractmethod
    async def proxy_request(self, payload: dict, api_key: str) -> APICallResult:
        """Forward a request to the provider and parse the response for tracking."""
        ...

    @abstractmethod
    def parse_response_headers(self, headers: dict) -> dict:
        """Extract tracking info from provider response headers."""
        ...
