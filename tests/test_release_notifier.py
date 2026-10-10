import asyncio

from devtools_sms.models import DeveloperEvent
from devtools_sms.release_notifier import SuppressionRegistry, notify_release


def test_opted_out_recipient_is_suppressed_without_a_send() -> None:
    calls: list[tuple[list[dict[str, str]], str]] = []

    async def record_send(
        messages: list[dict[str, str]], idempotency_key: str
    ) -> dict[str, object]:
        calls.append((messages, idempotency_key))
        return {"message_id": "batch-1"}

    registry = SuppressionRegistry()
    registry.suppress("+15550102030", "user_opt_out")
    event = DeveloperEvent(
        operation_id="build-481",
        kind="build_failed",
        recipient="+15550102030",
        text="Build 481 failed in the package stage.",
    )

    result = asyncio.run(notify_release(event, registry, record_send))

    assert result.status == "suppressed"
    assert result.reason == "user_opt_out"
    assert calls == []


def test_allowed_release_uses_stable_idempotency_key() -> None:
    calls: list[tuple[list[dict[str, str]], str]] = []

    async def record_send(
        messages: list[dict[str, str]], idempotency_key: str
    ) -> dict[str, object]:
        calls.append((messages, idempotency_key))
        return {"message_id": "batch-2"}

    event = DeveloperEvent(
        operation_id="release-482",
        kind="release_completed",
        recipient="+15550102031",
        text="Release 482 completed.",
    )

    result = asyncio.run(notify_release(event, SuppressionRegistry(), record_send))

    assert result.status == "accepted"
    assert calls == [
        ([{"to": "+15550102031", "text": "Release 482 completed."}], "devtools:release-482")
    ]
