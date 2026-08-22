# Contributing

Thanks for contributing to this repository.

## General Rules

* Keep changes focused and easy to review.
* Write code, comments, documentation, states, and reason codes in English.
* Preserve backward compatibility whenever possible.
* Treat published blueprint inputs, states, attributes, and reason codes as a public API.

## Home Assistant Blueprints

* Use typed selectors instead of free-text entity IDs.
* Do not hardcode installation-specific entities.
* Bind `!input` values to variables before using them in templates.
* Add sensible defaults for new optional inputs.
* Only increase `homeassistant.min_version` when required by a feature.
* Keep `source_url` pointed at the canonical file in this repository.

## Documentation

Update the relevant documentation when user-visible behavior changes.

Main documentation files:

* `README.md`
* `docs/smart-ventilation.md`
* `docs/smart-ventilation.de.md`

Dashboard UI changes belong in the separate
[Smart Ventilation Card](https://github.com/rudnerbjoern/smart-ventilation-card)
repository.

## Test Suite

On Windows, prepare the local `.venv` and test dependencies once:

```powershell
.\scripts\prepare-tests.ps1
```

Then run the same YAML, Markdown, and Python checks used by CI:

```powershell
.\scripts\run-tests.ps1
```

Use `run-tests.ps1 -Coverage` to include a terminal coverage report. Re-run
`prepare-tests.ps1` whenever the test dependencies need to be installed or
updated.

## Commit Messages

Follow the conventions defined in:

`.github/commit-message-instructions.md`

## Pull Requests

Before submitting a pull request:

* Review the changed blueprint logic.
* Check YAML formatting.
* Update documentation where required.
* Avoid unrelated formatting or refactoring changes.
