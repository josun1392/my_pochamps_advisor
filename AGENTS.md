## Custom Command: /goal

When the user starts a message with `/goal`, treat the rest of the message as the active project goal, not as a built-in Codex app command.

Behavior:
1. Restate the goal in one sentence.
2. Identify the current milestone and expected output.
3. Check repository status before making changes.
4. Propose a short execution plan before implementation.
5. Keep the scope narrow and follow the latest explicit T1/T2 constraints.
6. If the goal involves architecture, payload schema, damage calculations, or LLM behavior, prefer a design/contract step before implementation unless T1 explicitly asks for implementation.
7. Do not push without explicit T1 approval.
8. Do not commit `docs/handoff_capsule_v1.1.md`, `logs/`, secrets, API keys, or temporary files.
9. Do not modify `advisor/damage/` or `advisor/probability/` unless the goal explicitly authorizes it and tests are added.
10. If blocked, report the blocker, what was verified, and the safest next action.

## Project Setup

This is a Python 3.11+ project managed with `uv`.

Use these commands for a fresh environment:

```powershell
uv sync --dev
cd tools/smogon_bridge
npm install
cd ../..
```

`config/.env` is a local-only secret file and is intentionally not tracked.
Ask the user for the required Gemini or Vertex AI environment variables instead
of creating placeholder secrets in git.

## Verification

Default test command:

```powershell
uv run pytest
```

Useful targeted checks:

```powershell
uv run python scripts/verify_champions_roster.py
uv run python scripts/verify_damage_engine.py
uv run python scripts/verify_field_engine.py
uv run python scripts/verify_parity_bridge.py
```

Run parity bridge checks only after installing `tools/smogon_bridge` Node
dependencies.
