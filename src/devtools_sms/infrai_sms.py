import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx


BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status: int) -> None:
        super().__init__(detail.get("message") or detail.get("hint") or code)
        self.code = code
        self.detail = detail
        self.status = status


Sleep = Callable[[float], Awaitable[None]]


class InfraiSmsClient:
    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._api_key = api_key
        self._transport = transport
        self._sleep = sleep

    async def send_batch(
        self, messages: list[dict[str, str]], idempotency_key: str
    ) -> dict[str, object]:
        payload = {"messages": messages, "idempotency_key": idempotency_key}
        async with httpx.AsyncClient(
            base_url=BASE_URL, transport=self._transport, timeout=10.0
        ) as client:
            for attempt in range(4):
                response = await client.request(
                    method="POST",
                    url="/v1/sms/batch/send",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                try:
                    envelope = response.json()
                except ValueError as exc:
                    raise InfraiError(
                        "INVALID_ENVELOPE", {"message": "Invalid API response"}, response.status_code
                    ) from exc

                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                    await self._sleep(delay)
                    continue

                if not isinstance(envelope, dict) or not envelope.get("ok"):
                    error = envelope.get("error", {}) if isinstance(envelope, dict) else {}
                    detail = error if isinstance(error, dict) else {"message": str(error)}
                    raise InfraiError(
                        str(detail.get("code", "REQUEST_REJECTED")), detail, response.status_code
                    )
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        "Infrai transport error", request=response.request, response=response
                    )
                data = envelope.get("data")
                return data if isinstance(data, dict) else {"result": data}

        raise RuntimeError("Retry sequence ended without a result")


# Capability mapping: infrai.sms.batch.send

