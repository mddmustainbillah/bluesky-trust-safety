import pytest

import bluesky_trust_safety


@pytest.mark.unit
def test_package_is_importable() -> None:
    assert bluesky_trust_safety.__name__ == "bluesky_trust_safety"
