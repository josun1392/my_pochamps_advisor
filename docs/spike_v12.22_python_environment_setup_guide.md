# v12.22 Python Environment Setup Guide

## Purpose

Document how to restore the Python test environment required before any future
field-state actual Gemini smoke.

This guide is documentation-only. It does not install dependencies, does not
run `uv sync`, does not change dependency files, and does not execute any
Gemini, provider, network, retry, or Vertex AI call.

## Current Problem

The v12.21 preflight diagnosis found:

- current shell `python` is Anaconda Python 3.13.5
- the repository expects a uv-managed environment
- current shell does not have `uv` on PATH
- `PySide6` is missing from both current Python and the available Python 3.11
- Python 3.11 also lacks `pytest`
- PySide6-dependent tests fail during collection

This is a local environment/runner mismatch. The project dependency declarations
already include the required packages.

## Expected Runner / Dependency Source

Expected Python:

- Python 3.11 or newer

Expected dependency manager:

- `uv`

Expected runner:

```powershell
uv run pytest
```

Dependency source:

- `pyproject.toml`
- `uv.lock`

Relevant `pyproject.toml` declarations:

- `requires-python = ">=3.11"`
- runtime dependency: `PySide6>=6.7`
- dev dependencies:
  - `pytest>=8.0`
  - `pytest-mock>=3.12`

Relevant lockfile status:

- `uv.lock` is present
- `uv.lock` contains PySide6, PySide6 add-ons/essentials, shiboken6, pytest,
  and pytest-mock entries

Not present:

- `requirements.txt`
- `requirements-dev.txt`
- `pytest.ini`
- `tox.ini`

## Windows Setup Guide

Use this only after T1 approves environment setup. These commands are provided
as a guide and were not executed in v12.22.

1. Open a new PowerShell shell.

2. Move to the repo root:

```powershell
cd "C:\Users\jsp33\OneDrive\Desktop\내 파일\project\대학\파이썬\poke_advisor"
```

3. Confirm `uv` is available:

```powershell
where uv
uv --version
```

4. If `uv` is not available, install or restore `uv` using the user's preferred
   Windows method, then restart the shell or refresh PATH.

5. Confirm the shell sees the intended Python tooling:

```powershell
where python
python --version
uv python list
```

6. Restore/sync the project environment from the existing lockfile:

```powershell
uv sync --dev
```

7. Run the targeted preflight set:

```powershell
uv run pytest tests/test_field_profile_button_integration_contract.py -q
uv run pytest tests/test_field_profile_dialog.py -q
uv run pytest tests/test_ui_turn_pipeline_flag_flow.py -q
uv run pytest tests/test_advisor_battle_state_context.py -q
uv run pytest tests/test_advisor_payload_contract.py -q
```

8. Run full pytest if the targeted set passes:

```powershell
uv run pytest -q
```

## Targeted Preflight Commands

Required before any field-state actual smoke:

```powershell
uv run pytest tests/test_field_profile_button_integration_contract.py -q
uv run pytest tests/test_field_profile_dialog.py -q
uv run pytest tests/test_ui_turn_pipeline_flag_flow.py -q
uv run pytest tests/test_advisor_battle_state_context.py -q
uv run pytest tests/test_advisor_payload_contract.py -q
```

These cover:

- FieldProfileDialog behavior
- Field state button/session-state behavior
- limited-context checkbox gate
- UI-selected prompt path
- battle-state helper/field-profile normalization
- payload contract no-leakage and safety guards

## Full Preflight Command

Run after targeted tests pass:

```powershell
uv run pytest -q
```

## Troubleshooting

### `uv: command not found`

Cause:

- `uv` is not installed or is not on PATH for the current shell.

Action:

- Install or restore `uv` outside Codex execution if T1 approves.
- Restart PowerShell or refresh PATH.
- Re-run `where uv` and `uv --version`.

### PySide6 missing

Symptom:

```text
ModuleNotFoundError: No module named 'PySide6'
```

Cause:

- The test is running under a Python environment that was not synced from the
  project dependency set.

Action:

- Use `uv run pytest ...` after `uv sync --dev`.
- Do not add PySide6 manually to `pyproject.toml`; it is already declared.

### pytest missing

Symptom:

```text
No module named pytest
```

Cause:

- The selected Python is not the uv-managed dev environment.

Action:

- Use `uv run pytest ...`.
- If using a direct virtual environment, ensure it was created from
  `uv sync --dev`.

### Wrong Python selected

Symptom:

- `where python` shows Anaconda first.
- `python --version` differs from the intended project interpreter.
- PySide6-dependent tests fail even though dependencies are declared.

Action:

- Prefer `uv run ...`, which selects the project environment.
- Avoid relying on bare `python -m pytest` for UI preflight unless it points to
  the synced project environment.

### Anaconda Python is first on PATH

Cause:

- User PATH order prioritizes Anaconda.

Action:

- Use `uv run pytest` from the repo root.
- Do not treat Anaconda pytest success on non-UI tests as sufficient actual
  smoke readiness.

### `.venv` is missing or broken

Symptom:

- no `.venv` exists
- direct `.venv\Scripts\python.exe` invocation is unavailable
- PySide6/pytest are missing

Action:

- After T1 approval, restore the environment with `uv sync --dev`.
- If a broken `.venv` exists, repair it as an explicit environment setup task,
  not as part of actual smoke execution.

### PATH refresh does not expose uv

Action:

- Open a new PowerShell window.
- Re-run `where uv`.
- If still unavailable, document the installer/path issue and do not proceed to
  actual Gemini smoke.

## Actual Smoke Readiness Checklist

Before any controlled field-state actual Gemini smoke:

- repo is clean except allowed `config/env.example` and `logs/token_usage.jsonl`
- branch is `master`
- remote tracking is `origin/master`
- no unpushed commit exists
- `uv` is available
- uv dev environment is restored/synced
- targeted PySide6 tests pass
- `tests/test_advisor_payload_contract.py` passes
- no secrets are staged
- `logs/token_usage.jsonl` is unstaged
- actual Gemini call is separately approved by T1/T2
- approved call policy remains exactly 1 actual Gemini call, retry count 0, no
  second provider, and no Vertex AI

## Security / Logging Policy

- `.env` contents must not be printed.
- `GEMINI_API_KEY` must not be printed.
- access tokens and credentials must not be printed.
- ADC credentials and service account JSON must not be printed.
- raw `logs/token_usage.jsonl` contents must not be printed.
- only sanitized token summary may be reported after an actual smoke.
- `logs/token_usage.jsonl` remains unstaged and uncommitted.
- `config/env.example` remains out of scope for this setup-guide task.

## Non-Goals

v12.22 does not:

- install `uv`
- run `uv sync --dev`
- run `pip install`
- run `conda install`
- change `pyproject.toml`
- change `uv.lock`
- change requirements files
- change production code
- run an actual Gemini call
- validate API keys
- run network/provider calls
- change FieldProfileDialog behavior
- change field mapping behavior
- change prompt guard wording

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call,
network/provider call, API key validation, dependency install, or token-log
output is part of v12.22.

## Next Recommendation

Recommended next:

- v12.23 Environment Setup Execution

Reason:

- the required dependencies are already declared/locked, but the current shell
  cannot run PySide6-dependent preflight tests until uv and the project
  environment are restored.

Alternative:

- v12.23 Controlled Field State Gemini Smoke, only if the user has already
  restored the environment, targeted tests pass, and T1/T2 explicitly approve
  exactly one actual Gemini call.

Safe non-provider alternative:

- v12.23 Item Activation/Consumption Boundary Design
