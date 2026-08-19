from pathlib import Path

import pytest

from tests.helpers import TEMPLATE_BLUEPRINT_ROOT

BLUEPRINT_FILES = sorted(
    TEMPLATE_BLUEPRINT_ROOT.glob("*.yaml")
)


@pytest.mark.parametrize(
    "blueprint_path",
    BLUEPRINT_FILES,
    ids=lambda path: path.name,
)
def test_template_blueprint_is_valid_mapping(
    blueprint_path: Path,
    load_blueprint,
):
    document = load_blueprint(blueprint_path)

    assert isinstance(document, dict)


@pytest.mark.parametrize(
    "blueprint_path",
    BLUEPRINT_FILES,
    ids=lambda path: path.name,
)
def test_template_blueprint_has_required_metadata(
    blueprint_path: Path,
    load_blueprint,
):
    document = load_blueprint(blueprint_path)

    assert "blueprint" in document

    metadata = document["blueprint"]

    assert metadata["name"]
    assert metadata["domain"] == "template"
    assert metadata["author"]
    assert metadata["source_url"]


@pytest.mark.parametrize(
    "blueprint_path",
    BLUEPRINT_FILES,
    ids=lambda path: path.name,
)
def test_template_blueprint_has_minimum_home_assistant_version(
    blueprint_path: Path,
    load_blueprint,
):
    metadata = load_blueprint(blueprint_path)["blueprint"]

    assert "homeassistant" in metadata
    assert "min_version" in metadata["homeassistant"]


@pytest.mark.parametrize(
    "blueprint_path",
    BLUEPRINT_FILES,
    ids=lambda path: path.name,
)
def test_template_blueprint_source_url_points_to_repository(
    blueprint_path: Path,
    load_blueprint,
):
    metadata = load_blueprint(blueprint_path)["blueprint"]

    expected_suffix = (
        "/blueprints/template/"
        f"{blueprint_path.name}"
    )

    source_url = metadata["source_url"].strip()

    assert (
        "github.com/rudnerbjoern/ha-blueprints/"
        in source_url
    )
    assert source_url.endswith(expected_suffix)


@pytest.mark.parametrize(
    "blueprint_path",
    BLUEPRINT_FILES,
    ids=lambda path: path.name,
)
def test_template_blueprint_defines_sensor(
    blueprint_path: Path,
    load_blueprint,
):
    document = load_blueprint(blueprint_path)

    assert "sensor" in document


@pytest.mark.parametrize(
    "blueprint_path",
    BLUEPRINT_FILES,
    ids=lambda path: path.name,
)
def test_template_blueprint_has_update_trigger(
    blueprint_path: Path,
    load_blueprint,
):
    document = load_blueprint(blueprint_path)

    assert "triggers" in document
    assert isinstance(document["triggers"], list)
    assert document["triggers"]
