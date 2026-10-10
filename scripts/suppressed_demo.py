import asyncio

from devtools_sms.models import DeveloperEvent
from devtools_sms.release_notifier import SuppressionRegistry, notify_release


async def blocked_sender(
    messages: list[dict[str, str]], idempotency_key: str
) -> dict[str, object]:
    raise AssertionError("suppressed demo must not call the sender")


async def main() -> None:
    registry = SuppressionRegistry()
    registry.suppress("+15550102030", "user_opt_out")
    event = DeveloperEvent(
        operation_id="release-2026-10-01.1",
        kind="release_started",
        recipient="+15550102030",
        text="Release release-2026-10-01.1 started.",
    )
    decision = await notify_release(event, registry, blocked_sender)
    print(decision.model_dump_json())


if __name__ == "__main__":
    asyncio.run(main())

