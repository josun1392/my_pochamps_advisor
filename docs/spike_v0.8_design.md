# Spike v0.8 Design — Four-Move Moveset Source

## 1. Goal

v0.8 decides where the real four-move moveset should come from before the LLM
payload includes move name/type/power/category. The core rule is strict:
learnset candidates are not battle movesets. The LLM should receive only moves
that the user or a trusted import/preset has explicitly selected. This is still
not a damage-calculation milestone, and `advisor/damage/` remains untouched.

## 2. Current v0.7 State

The v0.7 payload includes a `moves` section with UI move slot metadata only:

- `my_selected_move_index`
- `opponent_selected_move_index`
- `my_available_moves: []`
- `opponent_available_moves: []`
- `move_data_status: "not_connected_in_v0.7"`

`selected_move_index` is only a UI slot index, not a move id. Actual move data is
explicitly not connected.

## 3. Moveset Source Options

### Option A — Manual Move Selection UI

Users assign up to four moves per Pokemon. PokeAPI/cache learnsets can power the
search list, but only the user-confirmed four moves enter the LLM payload.

Pros:
- Safest source of truth for v0.8 MVP.
- Keeps learnset candidates separate from actual battle moves.
- Works without a full team builder.

Cons:
- Requires a small move-setting UI.
- Users must enter moves manually.

### Option B — Showdown Team Export/Import

Users paste a Showdown team export. The parser extracts species, item, ability,
and moves.

Pros:
- Strong source of real battle sets.
- Later phases can reuse item/ability/move data.

Cons:
- Larger parser surface.
- Error handling is bigger than v0.8 needs.
- More likely to pull scope toward full team builder.

### Option C — Curated Sample Moveset Presets

The repo ships human-authored sample sets under something like
`data/movesets/`.

Pros:
- Fast demo path.
- Low UI complexity.

Cons:
- Limited accuracy for real user teams.
- Maintenance burden.
- Can mislead if presets are treated as the user's actual set.

### Option D — PokeAPI/Cache Learnset Auto-Fill

The app automatically inserts all or selected learnable moves from cache.

Pros:
- Easy to populate candidate lists.

Cons:
- Dangerous if treated as an actual four-move moveset.
- Learnsets can include too many historical, transfer, event, or format-illegal moves.
- LLM may infer impossible choices if the payload is not explicit.

Verdict: use learnsets only as search candidates, never as `my_available_moves`.

## 4. Recommended v0.8 MVP

T3 recommendation: Option A minimal version.

Implement four move slots per selected Pokemon. Each slot is assigned manually by
the user through a simple move search/selection flow. The move search may use
PokeAPI/cache learnsets as candidates, filtered by the selected species where
available. The payload includes only user-confirmed move slots. Empty slots stay
empty and become limitations, not inferred moves.

## 5. Data Source Audit

Files inspected:

- `data/cache/pokeapi/moves/*.json`
- `data/cache/pokeapi/pokemon/*.json`
- `data/meta/cache_index.json`
- `data/ko_mapping.json`
- `core/cache_manager.py`
- `core/pokemon_repository.py`
- `core/search_engine.py`
- `ui/widgets/pokemon_panel.py`
- `ui/widgets/pokemon_search_box.py`
- `ui/main_window.py`

Findings:

- Move cache fields available:
  - `id`
  - `name`
  - `type`
  - `damage_class`
  - `power`
  - `accuracy`
  - `pp`
  - `priority`
  - `target`
  - localized `names`
- Pokemon cache contains raw `moves` lists per species.
- `data/meta/cache_index.json` maps move names to cache ids.
- `CacheManager.get("moves", move_id_or_name)` can retrieve move metadata.
- `data/ko_mapping.json` contains Korean move names under `moves`.
- `SearchEngine` already supports `kind="move"` through the KO mapping.
- `PokemonSearchBox` is Pokemon-specific UI, but the search pattern can be reused.
- No existing move selection/search widget exists.
- Current move buttons are placeholders and not data sources.

## 6. Minimal Data Model

Suggested model:

```python
MoveView:
    move_id: str
    name_en: str
    name_ko: str | None
    type: str
    category: str
    power: int | None
    accuracy: int | None
    pp: int | None
```

`PokemonPanel` additions:

```python
selected_moves: list[MoveView | None]  # length 4
selected_move_index: int | None
```

Payload shape:

```json
{
  "moves": {
    "my_available_moves": [
      {"slot": 0, "move_id": "flamethrower", "name": "Flamethrower", "type": "fire", "category": "special", "power": 90}
    ],
    "my_selected_move": {"slot": 0, "move_id": "flamethrower", "name": "Flamethrower"},
    "opponent_available_moves": [],
    "move_data_status": "connected_partial"
  }
}
```

Only non-empty, user-confirmed slots should appear in `my_available_moves`.

## 7. UI Design Options

### Option A1 — Simple Text Entry Per Move Slot

Users type move ids/names directly.

Pros: smallest implementation.  
Cons: typo-prone and less friendly.

### Option A2 — Move Search Dialog/Combo Box

Click a move slot, search candidate moves, confirm one.

Pros: practical and clear.  
Cons: moderate UI work.

### Option A3 — Reuse PokemonSearchBox Pattern For Moves

Create a `MoveSearchBox` or genericize the existing search widget around
`SearchEngine.search(kind="move")`.

Pros: consistent with current UI and uses existing search engine.  
Cons: needs careful naming to avoid over-refactor.

T3 recommendation: A3 if kept small, otherwise A2. Do not use raw text as the
primary MVP unless T1 needs the absolute fastest spike.

## 8. MainWindow / Panel Integration Plan

- Store `selected_moves` on `PokemonPanel`, parallel to `selected_move_index`.
- Keep move selection and move assignment separate:
  - clicking an existing move button selects the slot
  - a small search action assigns a move to that slot
- `MainWindow._build_llm_battle_input()` reads `selected_moves`, not labels.
- Empty move slots are omitted from available moves.
- Worker still receives a plain dict only.
- `LLMAdvicePanel` does not need changes for v0.8.

## 9. advisor_client / Prompt Impact

Keep `run_ui_selected_advice(battle_input, model=None)`. Expand only the payload
schema. Prompt wording can remain mostly unchanged because it already includes
the full JSON. As real move data appears, reduce the v0.7 move limitation from
"move data not connected" to "damage data not connected."

## 10. Damage Calculation Boundary

Option A: move data only.
- Recommended for v0.8.

Option B: move data + rough no-EV damage estimate.
- Not recommended. It creates false precision without final stats/items.

Option C: defer damage entirely.
- Acceptable if move UI work gets too large, but less useful than Option A.

T3 recommendation: v0.8 should connect move data only. Damage estimates should
wait for v0.9 or later, after final stats and battle modifiers have a source.

## 11. Error Handling

- Empty move slot: omit it and mark moveset partial.
- Selected move index points at empty slot: `my_selected_move` is `null` and add
  a limitation.
- Move id not in cache: friendly UI error on assignment; do not put it in payload.
- Move metadata missing: allow partial payload only if `move_id` and `name` are
  present; otherwise reject assignment.
- Species learnset does not include user input: warn or mark as unverified; do
  not silently accept as legal.
- API key missing/invalid: existing friendly error.
- Gemini HTTP error: existing status-code path.

## 12. Known Limitations

Maintain:

- EV/IV/nature/item/final stats are not connected.
- Exact HP is not connected.
- Weather/terrain/boosts are not connected.
- Terastallization is banned in PoChamps and must not be considered.
- Damage, OHKO/2HKO, and KO chance must not be stated as exact without damage data.
- Even with move data connected, KO probability is unavailable until damage data
  is explicitly supplied.

## 13. Out of Scope

- `advisor/damage/` changes
- damage estimate implementation
- EV/IV/nature/item input
- Showdown import implementation in v0.8 MVP
- full battle state
- automatic LLM calls
- streaming/cancel/retry
- Minimax/Critic loop

## 14. Manual Verification Scenarios

1. Select my Pokemon and opponent Pokemon.
2. Assign one or more move slots manually.
3. Select a move slot.
4. Confirm only assigned moves appear in `battle_input.moves.my_available_moves`.
5. Confirm empty move slots are omitted.
6. Confirm selected empty slot produces `my_selected_move: null`.
7. Confirm invalid move assignment is handled before Gemini.
8. Run `uv run pytest -q`.

## 15. Rollback Plan

1. Remove `selected_moves` storage from `PokemonPanel`.
2. Remove move assignment UI.
3. Revert `battle_input.moves` to the v0.7 slot-only shape.
4. Keep v0.6/v0.7 selected Pokemon and selected index payload intact.
5. Re-run pytest.
