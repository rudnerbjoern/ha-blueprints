import pytest

from tests.helpers import load_home_assistant_yaml


@pytest.fixture
def load_blueprint():
    """Return the Home Assistant-aware YAML loader."""

    return load_home_assistant_yaml
