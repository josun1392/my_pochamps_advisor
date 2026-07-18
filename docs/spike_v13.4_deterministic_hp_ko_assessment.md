# v13.4 Deterministic HP And KO Assessment

## Inventory

- Existing UI state exposes `hp_percent`, not exact current HP. It remains a
  visible-state value and is never converted to an exact integer here.
- v13.1 final-stat `hp` means maximum HP. v13.4 keeps it distinct from a new
  exact user-confirmed current/max HP snapshot.
- Legacy `ko_context` reads legacy damage estimates and their HP/default
  assumptions. It can model legacy roll outcomes but is not changed or merged.
- Existing damage roll helpers and probability paths include broader mechanics;
  v13.4 instead reconstructs only v13.3's unchanged 16 integer 85..100 rolls.
- Hazards/chip/recovery and survival contexts (including Focus Sash) remain
  separate legacy/limited contexts and are not applied to this result.

## Contract

`user_confirmed_current_hp` has side, exact `current_hp`, exact `maximum_hp`,
and known confidence. Validation requires `0 <= current_hp <= maximum_hp` and
rejects percent, estimates, post-turn values, decimals, and invalid ranges.
The session dialog replaces one snapshot per side; Cancel/invalid preserve the
prior state and Clear removes it. The existing limited-context checkbox gates
both raw HP context and every HP/KO result.

For a resolved v13.3 damage estimate, percentage uses integer rolls divided by
maximum HP and rounds display values to one decimal. OHKO counts `damage >=
current_hp` over 16 rolls. Within-two-hits enumerates all 256 independent roll
pairs; first-hit OHKO pairs are intentionally included. No recovery, chip,
hazard, survival, accuracy, critical, modifier, or between-turn state is used.

## Result Boundary

`hp_assessments` is separate from `damage_estimate` and legacy `ko_context`.
Its exact `[Deterministic Results]` entries cover percentage, OHKO count/status,
and two-hit count/status/scope; no 16-roll list is acknowledged. Parser and
semantic validation reject changed HP identities/counts/ranges/scopes and
claims about exact remaining HP, guaranteed real-battle KO, Focus Sash,
Leftovers, accuracy, criticals, or turn transitions.

## Verification

- HP/UI/gate contracts: 44 passed.
- `uv run pytest -q`: 2027 passed, 2 deselected in 27.65s (offline full suite).
