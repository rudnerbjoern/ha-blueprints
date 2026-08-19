# Commit Message Instructions

Use short, clear commit messages in English.

Format:

```text
<emoji> <type>(<scope>): <summary>
```

Examples:

```text
:sparkles: feat(ventilation): add smart ventilation sensor
:bug: fix(ventilation): handle unavailable climate sensors
:recycle: refactor(ventilation): centralize recommendation logic
:memo: docs: document ventilation thresholds
:white_check_mark: test(ventilation): add winter edge cases
:wrench: chore: update repository configuration
```

Preferred types and emojis:

```text
:sparkles: feat
:bug: fix
:recycle: refactor
:memo: docs
:white_check_mark: test
:zap: perf
:wrench: chore
:construction_worker: ci
:art: style
```

Rules:

* Keep the summary concise, preferably under 72 characters.
* Use imperative mood and lowercase after the colon.
* Do not end the summary with a period.
* Describe the actual behavior or architectural change.
* Avoid vague messages such as `update files`, `changes`, or `fix stuff`.
* Keep machine-readable blueprint states and reason codes in English.
* Treat published blueprint input keys, states, and reason codes as a public API.
* Update documentation when user-visible blueprint behavior changes.
* Only increase `homeassistant.min_version` when a used feature requires it.
