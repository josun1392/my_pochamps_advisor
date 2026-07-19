# v13.26 deterministic battle-counter move power

Supported moves are an explicit allowlist: Rage Fist and Last Respects. The
only accepted input is a user-confirmed current-battle counter snapshot; no
damage, HP, team slots, logs, predictions, or LLM prose can create a counter.

- Rage Fist: `min(350, 50 + 50 * qualifying_hits_received)`; zero is valid and
  the power cap is 350.
- Last Respects: `50 + 50 * fainted_allies`; the trusted conventional-team
  counter is bounded to 0–5, with maximum power 300.

Results use `battle_counter_power_assessment` and scope
`explicit-current-battle-counter-move-power-only`. Missing counters are
unavailable and never fall back to metadata move power. Effective power
replaces the move power once in deterministic damage calculation; it is not an
additional multiplier.
