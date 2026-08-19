# Copilot Instructions

This repository contains reusable Home Assistant blueprints.

## General

* Write code, comments, documentation, states, reason codes, and public API values in English.
* Prefer clear, maintainable solutions over clever or overly compact ones.
* Keep changes focused and avoid unrelated refactoring.
* Preserve backward compatibility whenever possible.

## Home Assistant Blueprints

* Use typed selectors for entities, targets, numbers, durations, and options.
* Never hardcode installation-specific entity IDs in reusable blueprints.
* Treat published input keys, sensor states, reason codes, and attributes as a public API.
* Do not rename or remove published inputs without a migration reason.
* New optional inputs should have sensible defaults.
* Use `source_url` pointing to the canonical file in this repository.
* Increase `homeassistant.min_version` only when a required feature demands it.
* Prefer native Home Assistant constructs over unnecessary templates.
* Keep `!input` out of Jinja templates; bind inputs to variables first.

## Smart Ventilation

Current sensor states:

```text
ventilate
conditional
keep_closed
neutral
```

Keep machine-readable values language-independent.

The ventilation duration is an estimate only. Do not describe it as an exact or optimal air-exchange time.

When changing ventilation logic, consider:

* drying potential
* indoor dry-air protection
* thermal disadvantage
* cold-weather behavior
* unavailable sensor handling
* backward compatibility of states and attributes

## Documentation

Update documentation when user-visible behavior changes.

Relevant files include:

```text
README.md
docs/smart-ventilation.md
```

Keep the README concise and move detailed technical explanations into `docs/`.

## Style

* YAML: 2-space indentation
* Prefer descriptive names
* Keep comments useful and concise
* Avoid duplicated decision logic
* Do not make speculative changes unrelated to the requested task
