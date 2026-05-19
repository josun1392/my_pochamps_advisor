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
