# v12.23 Environment Setup Execution

## Purpose

Restore the project test environment from the existing uv-managed dependency
set and verify the field-state actual-smoke preflight suites before any future
actual Gemini call.

This step executed environment setup and tests only. It did not execute an
actual Gemini call, provider call, API key validation, retry, second provider
call, or Vertex AI call.

## Initial Environment Status

Initial repo state:

- branch: `master`
- remote tracking: `origin/master`
- unpushed commits: none
- allowed existing unstaged files:
  - `config/env.example`
  - `logs/token_usage.jsonl`

Initial shell environment:

- bare `python`: Anaconda Python 3.13.5
- `python` executable: `C:\Users\jsp33\anaconda3\python.exe`
- `uv`: not available on PATH at the start of the task
- PySide6-dependent tests were not ready in the original shell

No `.env`, API key, credential, or raw token log contents were printed.

## uv Availability

`uv` was not available through the current shell PATH. A Windows package-manager
install was executed within the v12.23 approved environment-repair scope.

Installed uv:

- version: `uv 0.11.26`
- installed via: Windows package manager
- current shell PATH still did not resolve bare `uv` immediately after install
- direct executable path was used for setup and tests in this session

Remaining operator note:

- open a new shell or refresh PATH before relying on bare `uv`
- direct `uv.exe` execution works in the current session

## Setup Actions Executed

Executed setup actions:

- verified initial repo status
- verified bare Python and missing `uv` status
- installed/restored `uv` within the approved v12.23 scope
- used `uv python list` to confirm available interpreters
- ran `uv sync --dev` with Python 3.11.9
- created/restored the repo `.venv`
- verified the uv-managed environment imports `pytest` and `PySide6`
- ran targeted preflight tests
- ran full pytest

No production code was changed.

No dependency manifest or lockfile was changed:

- `pyproject.toml`: unchanged
- `uv.lock`: unchanged
- requirements files: unchanged / not present

`.venv/` is ignored by git and was not staged.

## uv Sync Result

`uv sync --dev` completed successfully using CPython 3.11.9.

Post-sync environment:

- Python: 3.11.9
- pytest: 9.0.3
- PySide6: 6.11.0
- environment location: repo-local `.venv`

The sync restored the declared project test environment from the existing
`pyproject.toml` and `uv.lock`.

## Targeted Test Results

Targeted field-state actual-smoke preflight tests passed:

- `uv run pytest tests/test_field_profile_button_integration_contract.py -q`
  - `8 passed`
- `uv run pytest tests/test_field_profile_dialog.py -q`
  - `7 passed`
- `uv run pytest tests/test_ui_turn_pipeline_flag_flow.py -q`
  - `19 passed`
- `uv run pytest tests/test_advisor_battle_state_context.py -q`
  - `39 passed`
- `uv run pytest tests/test_advisor_payload_contract.py -q`
  - `366 passed`

PySide6-dependent tests now collect and pass in the uv-managed environment.

## Full Test Result

Full test suite:

- `uv run pytest -q`
  - `1397 passed, 2 deselected`

## Actual Smoke Readiness

Current environment readiness:

- status: READY for a future controlled field-state actual Gemini smoke

Readiness basis:

- `uv` is available through the installed executable
- `uv sync --dev` completed
- repo-local `.venv` was restored
- PySide6-dependent targeted tests pass
- advisor payload contract tests pass
- full pytest passes
- no dependency files changed
- no production code changed
- no unexpected tracked repo changes were introduced
- `logs/token_usage.jsonl` remains unstaged and uncommitted
- `config/env.example` remains unstaged and uncommitted

Execution boundary:

- a future actual Gemini smoke still requires separate explicit T1/T2 approval
- future provider call policy remains exactly 1 actual Gemini call, retry 0,
  second provider 0, and Vertex AI 0

## Remaining Issues

The only remaining environment note is shell PATH refresh:

- the current shell did not resolve bare `uv` immediately after installation
- a new PowerShell session or PATH refresh should make `uv` available directly
- until then, the installed `uv.exe` path can be used explicitly

No test blocker remains for the targeted preflight set.

## Security / Logging Confirmation

Security confirmations:

- no actual Gemini call was made
- no network/provider call for Gemini or Vertex AI was made
- no retry was triggered
- no second provider call was made
- no API key validation was performed
- no `.env` contents were printed
- no API key, access token, ADC credential, service account JSON, or billing
  details were printed
- raw `logs/token_usage.jsonl` contents were not printed
- `logs/token_usage.jsonl` remains unstaged and uncommitted
- `config/env.example` remains unstaged and uncommitted
- `docs/handoff_capsule_v1.1.md` was not modified or committed

## Non-Goals

This step did not:

- run an actual Gemini smoke
- validate provider credentials
- change production code
- change `pyproject.toml`
- change `uv.lock`
- change requirements files
- change FieldProfileDialog behavior
- change field mapping behavior
- change prompt guard wording
- add a limited-context checkbox
- change UI checkbox defaults
- change payload builder call flow
- implement a full Turn Engine
- change `damage_estimate` or `ko_context`

## Next Recommendation

Recommended next:

- v12.24 Controlled Field State Gemini Smoke

Reason:

- the uv-managed environment is restored
- targeted field-state preflight tests pass
- full pytest passes
- actual smoke execution can now be considered, but only after separate
  explicit T1/T2 approval for exactly one actual Gemini call
