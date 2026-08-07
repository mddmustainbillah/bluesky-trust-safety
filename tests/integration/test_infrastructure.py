import pytest
from redis import Redis
from sqlalchemy import create_engine, text

from bluesky_trust_safety.common.settings import Settings


@pytest.mark.integration
def test_redis_is_reachable() -> None:
    settings = Settings()
    redis_client = Redis.from_url(
        settings.redis_url.get_secret_value(),
        decode_responses=True,
    )

    try:
        assert redis_client.ping() is True
    finally:
        redis_client.close()


@pytest.mark.integration
def test_postgres_is_reachable() -> None:
    settings = Settings()
    engine = create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()

        assert result == 1
    finally:
        engine.dispose()
