# Spike v0.7 Design — Selected Move Data for LLM Advice

## 1. Goal

v0.7 connects move-related UI state to the LLM payload without turning the spike
into a full damage calculator. The selected my-side and opponent-side Pokemon
from v0.6 remain the base input. v0.7 audits the current move buttons,
`selected_move_index`, repository cache, and move detail cache, then proposes the
smallest safe schema for move candidates. `advisor/damage/` remains untouched.

## 2. Current v0.6 Flow

1. `LLMAdvicePanel` button emits `advice_requested`.
2. `MainWindow._start_llm_advice()` validates selected my/opponent slots.
3. `MainWindow._build_llm_battle_input()` builds `pokemon.my_active` and
   `pokemon.opponent_active`.
4. Worker receives a plain dict and calls
   `run_ui_selected_advice(battle_input)`.
5. `llm/advisor_client.py` serializes the payload into the Gemini prompt.
6. Gemini returns a recommendation; `MainWindow` updates the panel and status bar.

## 3. v0.7 Proposed Flow

1. Keep the v0.6 selected my/opponent Pokemon flow.
2. Read my-side `PokemonPanel.selected_move_index`.
3. Build a move candidate payload from structured cache data where available.
4. If the selected move index can be mapped to a concrete candidate, include
   `my_selected_move`.
5. If it cannot be mapped, keep the selected index and add a limitation instead
   of inventing a move.
6. Reuse `run_ui_selected_advice(battle_input)` with an expanded schema.

## 4. Move Data Source Audit

Files inspected:

- `ui/widgets/pokemon_panel.py`
- `ui/main_window.py`
- `core/pokemon_repository.py`
- `core/cache_manager.py`
- `data/cache/pokeapi/pokemon/*.json`
- `data/cache/pokeapi/moves/*.json`
- `data/meta/cache_index.json`
- `llm/advisor_client.py`

Findings:

- `PokemonPanel.move_buttons` is a list of four `QPushButton` instances.
- Button labels are placeholders (`Q/W/E/R` + skill number), not real move names.
- `PokemonPanel.selected_move_index` is `int | None`; it stores the clicked
  button index `0..3`, not a move id.
- `PokemonPanel.set_pokemon(view)` stores `pokemon_view`, but does not bind moves.
- `PokemonView` contains `en`, `ko`, `types_*`, `base_stats`, and `abilities_*`;
  it does not contain move data.
- `PokemonRepository.get(...)` reads Pokemon cache and currently drops the raw
  `moves` list instead of exposing it on `PokemonView`.
- Pokemon cache files include a raw `moves` list of move ids/names, e.g.
  Charizard and Garchomp have many learnable moves.
- Move cache files include structured move detail: `name`, localized `names`,
  `type`, `damage_class`, `power`, `accuracy`, `pp`, `priority`, and `target`.
- `CacheManager` can read `moves` by id or name using `cache.get("moves", name)`.
- There is no current selected four-move moveset model.

## 5. Minimal v0.7 Input Schema

Use only fields confirmed above:

```json
{
  "scenario": {
    "mode": "ui-selected-pokemon-v0.7",
    "known_limitations": ["..."]
  },
  "pokemon": {
    "my_active": {"name_en": "charizard", "selected_move_index": 0},
    "opponent_active": {"name_en": "garchomp"}
  },
  "moves": {
    "my_available_moves": [
      {
        "slot": 0,
        "move_id": "flamethrower",
        "name": "Flamethrower",
        "type": "fire",
        "category": "special",
        "power": 90,
        "accuracy": 100
      }
    ],
    "my_selected_move": null,
    "selected_move_index": 0
  }
}
```

Important: `my_available_moves` must represent a known UI moveset only if v0.7
adds a real mapping. If no mapping exists, do not use the first four learnable
moves as a fake moveset. In that case, include `selected_move_index` and a
limitation that actual four-move selection is not connected yet.

## 6. Damage Calculation Boundary

Option A: pass move data only.
- Pros: small, safe, preserves v0.6 architecture.
- Cons: LLM still cannot make exact KO claims.

Option B: calculate a single move damage estimate.
- Pros: more useful recommendation.
- Cons: risky because EV/IV/nature/item/exact HP/moveset are not connected.

Option C: defer damage calculation to v0.8 and finish move payload connection.
- Pros: best boundary for v0.7; avoids false precision.
- Cons: one more iteration before quantitative move advice.

T3 recommendation: Option C. v0.7 should expose structured move data only when
it is truly connected, and defer damage estimates until a real moveset + stat
input path exists.

## 7. advisor_client Change Design

Keep:

```python
run_ui_selected_advice(battle_input: dict, model: str | None = None)
```

Do not add a new client function for v0.7. Let `battle_input["scenario"]["mode"]`
and the optional `moves` section describe the richer payload. The prompt can stay
mostly unchanged because it already includes the full JSON payload. Avoid large
prompt-level bans; put data limits in `known_limitations`.

## 8. MainWindow Integration Plan

`MainWindow` should collect:

- existing selected my/opponent Pokemon payload
- `my_panel.selected_move_index`
- optional structured move candidates if a trustworthy source exists

Do not read move button text as data. The current text is display placeholder
state. Prefer `PokemonView` plus `CacheManager.get("moves", move_id)` only after
a real four-move source is introduced. If no move source exists, continue with a
friendly limitation rather than a blocking error.

## 9. Error Handling

- My Pokemon missing: friendly error before worker starts.
- Opponent Pokemon missing: friendly error before worker starts.
- Move data missing: proceed with limitation if Pokemon payload is valid.
- `selected_move_index` exists but no mapped move: include index + limitation.
- Move power/type/category missing: include partial fields and mark incomplete.
- API key missing/invalid: existing friendly error.
- Gemini HTTP error: existing status-code error.
- TokenLogger failure: recommendation still displays; cost status notes failure.

## 10. Known Limitations

Carry forward v0.6.2 guardrails and add move-specific limits:

- Base stats are species reference data, not EVs or final calculated battle stats.
- EV/IV/nature/items/boosts/weather/terrain/exact HP are not connected.
- In this project's PoChamps format, Terastallization is banned and must not be considered.
- Do not assume unprovided EVs, IVs, nature, held items, boosts, weather, terrain, exact HP, or Tera types.
- Actual four-move sets are not connected unless `moves.my_available_moves` is explicitly populated from structured data.
- If move data is incomplete, do not infer exact damage or KO chances.
- Speed tier, OHKO/2HKO, and survival claims are uncertain unless final stats, items, move data, and damage data are explicitly provided.

## 11. Out of Scope

- `advisor/damage/` changes
- `advisor/probability/` changes
- full damage calculator integration
- EV/IV/nature/item input
- weather/field/rank implementation
- Tera implementation
- automatic LLM calls
- streaming
- cancel/retry
- Critic loop
- Minimax
- full battle state
- team builder completion

## 12. Manual Verification Scenarios

1. Select my Pokemon and opponent Pokemon, then click the advice button.
2. Select a my-side move button and confirm `selected_move_index` appears in payload.
3. If a structured move source is connected, confirm `my_available_moves` contains real move ids/types/power/category.
4. If no structured move source exists, confirm the payload includes a limitation instead of fake move names.
5. With a valid key, confirm Gemini does not make exact damage claims from incomplete move data.
6. Confirm missing move data does not block the existing v0.6 species-level advice path.
7. Run `uv run pytest -q` and keep the default passing suite unchanged.

## 13. Rollback Plan

1. Remove the optional `moves` section from `_build_llm_battle_input()`.
2. Leave v0.6 selected Pokemon payload intact.
3. Revert any move candidate helper added to `MainWindow`.
4. Keep `run_ui_selected_advice(...)`; it remains valid for v0.6.
5. Re-run pytest and verify the LLMAdvicePanel still works with species-only payload.
