from typing import Literal

from pydantic import BaseModel, Field


EventKind = Literal[
    "build_failed",
    "release_started",
    "release_completed",
    "diagnostic",
]


class DeveloperEvent(BaseModel):
    operation_id: str = Field(min_length=1, max_length=128)
    kind: EventKind
    recipient: str = Field(min_length=8, max_length=32)
    text: str = Field(min_length=1, max_length=800)


class SuppressionChange(BaseModel):
    recipient: str = Field(min_length=8, max_length=32)
    reason: Literal["user_opt_out", "maintainer_suppression"]


class SendDecision(BaseModel):
    operation_id: str
    status: Literal["suppressed", "accepted"]
    reason: str | None = None
    delivery: dict[str, object] | None = None

