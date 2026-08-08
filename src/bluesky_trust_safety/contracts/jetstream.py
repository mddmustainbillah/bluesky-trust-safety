"""Data models for Bluesky Jetstream events."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class JetstreamCommit(BaseModel):
    """Commit information contained inside a Jetstream event."""

    model_config = ConfigDict(extra="allow")

    operation: Literal["create", "update", "delete"]
    collection: str = Field(min_length=1)
    rkey: str = Field(min_length=1)
    record: dict[str, Any] | None = None
    cid: str | None = None
    rev: str | None = None


class JetstreamEvent(BaseModel):
    """A validated event received from Jetstream."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal[1] = 1
    did: str = Field(min_length=1)
    time_us: int = Field(gt=0)
    kind: Literal["commit"]
    commit: JetstreamCommit
    raw_payload: dict[str, Any]


def parse_jetstream_event(payload: dict[str, Any]) -> JetstreamEvent:
    """Validate a raw dictionary as a Jetstream event."""

    event_data = payload.copy()
    event_data["raw_payload"] = payload.copy()

    return JetstreamEvent.model_validate(event_data)
