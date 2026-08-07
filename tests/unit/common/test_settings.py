import pytest
from pydantic import ValidationError

from bluesky_trust_safety.common.settings import Settings

DATABASE_URL = "postgresql+psycopg2://bluesky:test-password@localhost:5433/bluesky_trust_safety"
REDIS_URL = "redis://localhost:6379/0"


@pytest.mark.unit
def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BTS_DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("BTS_REDIS_URL", REDIS_URL)
    monkeypatch.setenv("BTS_ENVIRONMENT", "test")

    settings = Settings(_env_file=None)

    assert settings.environment == "test"
    assert settings.log_level == "INFO"
    assert settings.database_url.get_secret_value() == DATABASE_URL
    assert settings.redis_url.get_secret_value() == REDIS_URL


@pytest.mark.unit
def test_required_settings_must_be_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BTS_DATABASE_URL", raising=False)
    monkeypatch.delenv("BTS_REDIS_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.unit
def test_invalid_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            redis_url=REDIS_URL,
            environment="unknown",
        )


@pytest.mark.unit
def test_secrets_are_redacted() -> None:
    settings = Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        redis_url=REDIS_URL,
    )

    settings_representation = repr(settings)

    assert "test-password" not in settings_representation
    assert DATABASE_URL not in settings_representation
