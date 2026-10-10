from collections.abc import Awaitable, Callable

from .models import DeveloperEvent, SendDecision


BatchSender = Callable[[list[dict[str, str]], str], Awaitable[dict[str, object]]]


class SuppressionRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, str] = {}

    def suppress(self, recipient: str, reason: str) -> None:
        self._entries[recipient] = reason

    def remove(self, recipient: str) -> None:
        self._entries.pop(recipient, None)

    def reason_for(self, recipient: str) -> str | None:
        return self._entries.get(recipient)


async def notify_release(
    event: DeveloperEvent,
    registry: SuppressionRegistry,
    send_batch: BatchSender,
) -> SendDecision:
    reason = registry.reason_for(event.recipient)
    if reason:
        return SendDecision(
            operation_id=event.operation_id,
            status="suppressed",
            reason=reason,
        )

    delivery = await send_batch(
        [{"to": event.recipient, "text": event.text}],
        f"devtools:{event.operation_id}",
    )
    return SendDecision(
        operation_id=event.operation_id,
        status="accepted",
        delivery=delivery,
    )

