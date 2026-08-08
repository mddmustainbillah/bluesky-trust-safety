"""Tests for Jetstream event contracts."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from bluesky_trust_safety.contracts.jetstream import parse_jetstream_event

FIXTURE_DIRECTORY = Path("tests/fixtures/jetstream")


def load_fixture(filename: str) -> dict[str, Any]:
    """Load a synthetic Jetstream fixture."""

    fixture_path = FIXTURE_DIRECTORY / filename

    with fixture_path.open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


@pytest.mark.unit
def test_valid_create_event_is_parsed() -> None:
    payload = load_fixture("post_create.json")

    event = parse_jetstream_event(payload)

    assert event.schema_version == 1
    assert event.did == "did:plc:aaaaaaaaaaaaaaaaaaaaaaaa"
    assert event.kind == "commit"
    assert event.commit.operation == "create"
    assert event.commit.collection == "app.bsky.feed.post"
    assert event.raw_payload == payload


@pytest.mark.unit
def test_valid_update_event_is_parsed() -> None:
    payload = load_fixture("post_update.json")

    event = parse_jetstream_event(payload)

    assert event.commit.operation == "update"
    assert event.commit.record is not None
    assert event.commit.record["text"] == ("This synthetic test post has been updated.")


@pytest.mark.unit
def test_valid_delete_event_is_parsed() -> None:
    payload = load_fixture("post_delete.json")

    event = parse_jetstream_event(payload)

    assert event.commit.operation == "delete"
    assert event.commit.rkey == "3kexamplepost"
    assert event.commit.record is None
    assert event.commit.cid is None


@pytest.mark.unit
def test_invalid_operation_is_rejected() -> None:
    payload = load_fixture("post_create.json")
    payload["commit"]["operation"] = "insert"

    with pytest.raises(ValidationError):
        parse_jetstream_event(payload)


@pytest.mark.unit
def test_invalid_timestamp_is_rejected() -> None:
    payload = load_fixture("post_create.json")
    payload["time_us"] = 0

    with pytest.raises(ValidationError):
        parse_jetstream_event(payload)


@pytest.mark.unit
def test_missing_did_is_rejected() -> None:
    payload = load_fixture("post_create.json")
    payload.pop("did")

    with pytest.raises(ValidationError):
        parse_jetstream_event(payload)


@pytest.mark.unit
def test_missing_commit_is_rejected() -> None:
    payload = load_fixture("post_create.json")
    payload.pop("commit")

    with pytest.raises(ValidationError):
        parse_jetstream_event(payload)


@pytest.mark.unit
def test_unknown_fields_are_accepted() -> None:
    payload = load_fixture("post_create.json")
    payload["future_field"] = "new Jetstream value"
    payload["commit"]["future_commit_field"] = "new commit value"

    event = parse_jetstream_event(payload)

    assert event.model_extra is not None
    assert event.model_extra["future_field"] == "new Jetstream value"
    assert event.commit.model_extra is not None
    assert event.commit.model_extra["future_commit_field"] == "new commit value"