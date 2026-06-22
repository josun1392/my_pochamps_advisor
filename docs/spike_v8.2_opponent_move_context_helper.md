# v8.2 Opponent Move Context Helper

## Purpose

v8.2 adds a minimal helper that builds a v8.1-compatible `opponent_move_context` from caller-provided move data.

The helper is source-bound:

- it normalizes known moves only when they come from trusted sources
- it normalizes unconfirmed moves only as candidates
- it never creates moves from species, common sets, usage data, or metadata guesses
- it does not connect the context to the advice payload adapter, prompt, UI, or Gemini call path

## Helper Location

`llm/advisor_opponent_move_context.py`

Primary API:

```python
build_opponent_move_context(
    known_moves=None,
    candidate_moves=None,
    selected_opponent_move=None,
)
```

## Input

`known_moves` and `candidate_moves` accept caller-provided move dictionaries with safe metadata fields such as:

- `source`
- `move_id`
- `name`
- `type`
- `category`
- `power`
- `accuracy`
- `priority`
- `target`
- `effect_flags`

`selected_opponent_move` is optional. If omitted, the helper emits:

```python
{"status": "unknown"}
```

Explicit selected moves require:

- `status="explicit"`
- trusted `source`
- `move_id`
- `name`

## Output

The helper returns the v8.1 contract shape:

```python
{
    "kind": "opponent_move_context",
    "confidence": "limited" | "unknown",
    "selected_opponent_move": {...},
    "known_opponent_moves": [...],
    "candidate_moves": [...],
    "priority_move_candidates": [...],
    "unsupported": [...],
    "safety_notes": [...],
}
```

`confidence` is `unknown` when there are no known moves, candidate moves, or explicit selected move. It is `limited` when source-bound information is present.

## Trusted Sources

Known moves require one of:

- `user_confirmed`
- `visible_ui`
- `explicit_input`

Untrusted known-move sources are omitted:

- `meta_inferred`
- `species_common_set`
- `usage_based_guess`

Candidate moves allow only source-bound candidate origins:

- `visible_or_cache_candidate`
- `champions_movepool`
- `visible_ui`

The helper does not use species names to generate moves.

## Known Move Handling

Trusted known moves are normalized with:

```python
"confirmed": True
```

Known moves are not inferred from candidates, species, usage data, or common sets.

## Candidate Move Handling

Candidate moves are always normalized with:

```python
"confirmed": False
"selected": False
```

Candidate inputs with selected or confirmed semantics are omitted:

- `confirmed=True`
- `selected=True`
- `will_use=True`
- `likely_selected=True`

Candidate moves are never promoted to known moves.

## Selected Move Handling

Absent selected move:

```python
{"status": "unknown"}
```

Explicit selected move:

```python
{"status": "explicit", "source": "...", "move_id": "...", "name": "..."}
```

Rejected selected move statuses:

- `inferred`
- `predicted`
- `likely`

The helper does not infer the selected opponent move from known or candidate moves.

## Priority Candidates

Candidate moves with trusted integer `priority > 0` are copied into `priority_move_candidates`.

Priority candidates remain unconfirmed:

```python
"confirmed": False
"selected": False
```

This is not turn-order resolution and does not imply the opponent selected that move.

## Forbidden Fields

The helper output does not emit:

- `inferred_moveset`
- `predicted_move`
- `likely_move`
- `will_use`
- `usage_rate_guess`
- `meta_set`
- `EVs`
- `IVs`
- `nature`
- `hidden_item`
- `post_turn_hp`
- `item_consumed`
- `rng_resolved`
- `speed_tie_resolved`

## Unsupported Boundaries

`unsupported` includes:

- hidden moveset inference
- opponent set inference
- selected opponent move inference
- EV/IV/nature inference
- hidden item inference
- weather/terrain/boost inference
- RNG resolution
- full turn resolution

## Tests

`tests/test_advisor_opponent_move_context.py` covers:

- empty input returns unknown context
- trusted known moves become `confirmed=True`
- untrusted known sources are omitted
- candidates remain `confirmed=False` and `selected=False`
- unsafe candidate semantics are omitted
- explicit selected move is allowed
- inferred / predicted / likely selected move statuses are rejected
- positive-priority candidates create unconfirmed priority candidates
- no species-only move inference
- forbidden fields are absent
- unsupported boundaries and safety notes are present

Existing v8.1 fixture-level payload contract tests remain green.

## Not Implemented

v8.2 does not add:

- payload adapter integration
- prompt integration
- UI checkbox behavior changes
- actual Gemini calls
- hidden moveset inference
- selected opponent move inference
- species/common set/meta-based move generation
- EV/IV/nature, hidden item, weather, terrain, or boost inference
- RNG, Quick Claw activation, item consumption, post-turn HP, or full turn resolution

## Next Recommendation

Recommended next:

- v8.3 Opponent Move Context Payload Adapter

Alternative if source extraction still feels too thin:

- v8.3 Opponent Move Source Extraction Design

The adapter should remain default-off / explicit-only and should not add prompt integration or UI behavior changes in the same step.
