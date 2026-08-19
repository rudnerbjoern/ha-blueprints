from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT_ROOT = REPOSITORY_ROOT / "blueprints"
TEMPLATE_BLUEPRINT_ROOT = BLUEPRINT_ROOT / "template"


class HomeAssistantYamlLoader(yaml.SafeLoader):
    """YAML loader that preserves Home Assistant custom tags."""


def _construct_unknown_tag(loader, tag_suffix, node):
    """Preserve unknown Home Assistant YAML tags."""

    tag = f"!{tag_suffix}"

    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node)
    elif isinstance(node, yaml.MappingNode):
        value = loader.construct_mapping(node)
    else:
        raise TypeError(
            f"Unsupported YAML node type: {type(node)!r}"
        )

    return {
        "__ha_tag__": tag,
        "value": value,
    }


HomeAssistantYamlLoader.add_multi_constructor(
    "!",
    _construct_unknown_tag,
)


def load_home_assistant_yaml(path: Path):
    """Load Home Assistant YAML without resolving custom tags."""

    with path.open(encoding="utf-8") as file:
        return yaml.load(
            file,
            Loader=HomeAssistantYamlLoader,
        )
