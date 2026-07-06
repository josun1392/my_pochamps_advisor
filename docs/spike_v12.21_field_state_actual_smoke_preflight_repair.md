# v12.21 Field State Actual Smoke Preflight Repair

## Purpose

Diagnose the local test environment before any controlled field-state actual
Gemini smoke.

This milestone does not execute Gemini, does not call any provider, does not
install dependencies, and does not change production code or dependency files.
It records the current shell/Python/pytest/PySide6/uv state and the correct
preflight runner expectation for the repository.

## Current Environment Diagnosis

Repository status at start:

- branch: `master`
- remote tracking: `origin/master`
- unpushed commits: none
- remaining unstaged files:
  - `config/env.example`
  - `logs/token_usage.jsonl`

Current shell Python discovery:

- `where python` lists:
  - `C:\Users\jsp33\anaconda3\python.exe`
  - `C:\Users\jsp33\AppData\Local\Programs\Python\Python311\python.exe`
  - `C:\Users\jsp33\AppData\Local\Microsoft\WindowsApps\python.exe`
- `python --version`: Python 3.13.5
- `python -c "import sys; print(sys.executable)"`:
  - `C:\Users\jsp33\anaconda3\python.exe`
- `python -c "import pytest; print(pytest.__version__)"`: 8.3.4
- `python -c "import PySide6; print(PySide6.__version__)"`: fails with
  `ModuleNotFoundError: No module named 'PySide6'`

Python launcher discovery:

- `py -0p` reports Python 3.11 at
  `C:\Users\jsp33\AppData\Local\Programs\Python\Python311\python.exe`
- Python 3.11 is present but lacks `pytest`
- Python 3.11 also lacks `PySide6`

uv discovery:

- `where uv`: no match
- `uv --version`: command not found in the current shell

Workspace virtual environment:

- `.venv` is not present in the repository root

## Expected Runner / Dependency Source

Project dependency source:

- `pyproject.toml`
- `uv.lock`

Expected runner from project docs:

```powershell
uv run pytest
```

Relevant declarations:

- `requires-python = ">=3.11"`
- runtime dependency: `PySide6>=6.7`
- dev dependencies:
  - `pytest>=8.0`
  - `pytest-mock>=3.12`

`uv.lock` contains locked entries for:

- `pyside6`
- `pyside6-addons`
- `pyside6-essentials`
- `shiboken6`
- `pytest`
- `pytest-mock`

No alternate dependency files were found:

- no `requirements.txt`
- no `requirements-dev.txt`
- no `poetry.lock`
- no `Pipfile`
- no `environment.yml`
- no `conda.yml`
- no `pytest.ini`
- no `tox.ini`

## PySide6 / pytest / uv Status

PySide6 status:

- Missing from the current PATH Python.
- Missing from the discovered Python 3.11 interpreter.
- Required by `pyproject.toml`.
- Locked in `uv.lock`.

pytest status:

- Present in the current Anaconda Python as version 8.3.4.
- Missing from the discovered Python 3.11 interpreter.
- Required as a dev dependency in `pyproject.toml`.
- Locked in `uv.lock`.

uv status:

- Required by project README/AGENTS workflow.
- Not available on the current shell PATH.
- No repo-local `.venv` exists for direct invocation.

## Targeted Tests Attempted

Attempted with current PATH Python:

```powershell
python -m pytest tests/test_advisor_battle_state_context.py -q
python -m pytest tests/test_field_profile_dialog.py -q
python -m pytest tests/test_field_profile_button_integration_contract.py -q
python -m pytest tests/test_ui_turn_pipeline_flag_flow.py -q
python -m pytest tests/test_advisor_payload_contract.py -q
```

## Passing Tests

Current PATH Python passes the non-UI battle-state helper suite:

```text
python -m pytest tests/test_advisor_battle_state_context.py -q
39 passed
```

## Failing Tests

Current PATH Python fails PySide6-dependent suites during collection:

- `tests/test_field_profile_dialog.py`
- `tests/test_field_profile_button_integration_contract.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_payload_contract.py`

Failure class:

```text
ModuleNotFoundError: No module named 'PySide6'
```

Python 3.11 direct invocation is not currently usable for pytest preflight
because it lacks `pytest`.

## Root Cause

The repository expects a uv-managed Python 3.11+ environment containing both
runtime and dev dependencies. The current shell instead resolves `python` to
Anaconda Python 3.13.5, which has pytest but not PySide6. The available Python
3.11 interpreter has neither pytest nor PySide6. `uv` is not on PATH, and no
repo-local `.venv` exists.

This is an environment/runner mismatch, not a field-state implementation
failure.

## Recommended Preflight Command

Once uv is available and the project environment is synced, use:

```powershell
uv run pytest tests/test_field_profile_button_integration_contract.py -q
uv run pytest tests/test_field_profile_dialog.py -q
uv run pytest tests/test_ui_turn_pipeline_flag_flow.py -q
uv run pytest tests/test_advisor_battle_state_context.py -q
uv run pytest tests/test_advisor_payload_contract.py -q
```

For full preflight:

```powershell
uv run pytest -q
```

If `uv` is still unavailable, do not proceed to actual Gemini smoke. Either:

- restore `uv` on PATH, or
- use a known project virtual environment that contains PySide6, pytest, and
  pytest-mock, then run the same targeted tests with that interpreter.

## Install / Change Recommendations

No install command was executed in v12.21.

If T1/T2 approve environment repair outside this task, the documented project
setup path is:

```powershell
uv sync --dev
```

This should be treated as an environment setup action, not as a code change.
Do not change `pyproject.toml` or `uv.lock` for this issue; required
dependencies are already declared and locked.

## Actual Smoke Readiness

Status: NOT READY in the current shell.

Reason:

- PySide6-dependent preflight tests cannot collect.
- `uv` is unavailable on PATH.
- No repo-local synced environment is available.

Actual Gemini smoke must remain blocked until targeted preflight tests pass in
the correct environment and T1/T2 explicitly approve the one-call smoke.

## No Actual Gemini Call

No actual Gemini call, API key validation, network/provider call, retry, second
provider call, Vertex AI call, or token-log output was performed.

## Next Recommendation

Recommended next:

- v12.22 Python Environment Setup Guide

Reason:

- dependencies are declared correctly, but the current shell does not expose a
  usable uv-managed environment for PySide6 UI preflight tests.

Alternative after environment repair:

- v12.22 Controlled Field State Gemini Smoke, only after targeted tests pass and
  T1/T2 explicitly approve exactly one actual Gemini call with retry count 0.
