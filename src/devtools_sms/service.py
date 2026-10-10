import os

import httpx
from fastapi import FastAPI, HTTPException, status

from .infrai_sms import InfraiError, InfraiSmsClient
from .models import DeveloperEvent, SendDecision, SuppressionChange
from .release_notifier import SuppressionRegistry, notify_release


app = FastAPI(title="Developer SMS suppression service")
registry = SuppressionRegistry()


def sms_client() -> InfraiSmsClient:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is not configured")
    return InfraiSmsClient(api_key)


@app.put("/suppressions/{recipient}", status_code=status.HTTP_204_NO_CONTENT)
async def add_suppression(recipient: str, change: SuppressionChange) -> None:
    if recipient != change.recipient:
        raise HTTPException(status_code=400, detail="Recipient does not match path")
    registry.suppress(recipient, change.reason)


@app.delete("/suppressions/{recipient}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_suppression(recipient: str) -> None:
    registry.remove(recipient)


@app.post("/developer-events", response_model=SendDecision)
async def developer_event(event: DeveloperEvent) -> SendDecision:
    client = sms_client()
    try:
        return await notify_release(event, registry, client.send_batch)
    except InfraiError as exc:
        client_status = exc.status if 400 <= exc.status < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="SMS transport request failed") from exc

