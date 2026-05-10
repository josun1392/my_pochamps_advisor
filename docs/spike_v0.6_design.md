# Spike v0.6 Design — UI-Selected Pokemon LLM Advice Input

## 1. Goal

v0.6 removes the first hardcoded part of the LLM advice spike. The `LLMAdvicePanel`
button remains unchanged, but the prompt input should use the currently selected
my-side Pokemon and opponent-side Pokemon from the PySide6 UI. This is not a full
battle-state implementation: moves, items, EVs, ranks, weather, field, and complete
turn modeling remain out of scope. `advisor/damage/` stays untouched.

## 2. Current v0.5 Flow

Current flow:

1. `LLMAdvicePanel` button emits `advice_requested`.
2. `MainWindow._start_llm_advice()` creates `LLMAdviceWorker` on `QThread`.
3. Worker calls `llm.advisor_client.run_spike_advice()`.
4. `run_spike_advice()` imports `scripts.spike_advisor` helpers.
5. `collect_battle_data()` returns hardcoded Mega Kangaskhan vs Garchomp data.
6. `build_prompt()` + `call_gemini()` produce the recommendation.
7. `TokenLogger` records usage and `MainWindow` updates the status bar.

## 3. Proposed v0.6 Flow

Proposed flow:

1. `LLMAdvicePanel` button emits `advice_requested`.
2. `MainWindow` validates selected my/opponent slots.
3. `MainWindow` reads minimal Pokemon state from those slots.
4. Worker receives a plain serializable battle input, not UI objects.
5. `llm.advisor_client.run_ui_selected_advice(...)` builds JSON + prompt.
6. Gemini returns the recommendation.
7. `MainWindow` displays text and token/cost status.

UI state collection and LLM calls remain separated. `LLMAdvicePanel` remains a
button/display widget only.

## 4. Data Source Audit

Files inspected:

- `ui/main_window.py`
- `ui/widgets/pokemon_panel.py`
- `ui/widgets/llm_advice_panel.py`
- `core/pokemon_repository.py`
- `llm/advisor_client.py`
- `scripts/spike_advisor.py`

Findings:

- My team selected slot:
  - `MainWindow.selected_slots["team_my"]`
  - initialized to `0`
  - updated by `MainWindow.select_slot("team_my", slot_index)`
- Opponent team selected slot:
  - `MainWindow.selected_slots["team_enemy"]`
  - initialized to `None`
  - `opponent_team_column = PokemonTeamColumn(..., selectable=False)`
  - despite `selectable=False`, `_connect_slot_clicks()` still connects opponent panels to `select_slot("team_enemy", ...)`
- Selected slot access:
  - `_team_column(column_name)` returns `my_team_column` or `opponent_team_column`
  - `PokemonTeamColumn.panels` holds six `PokemonPanel` instances
  - selected panel is `team_column.panels[selected_slots[column_name]]`
- `PokemonView` source:
  - `PokemonRepository.get(en_id) -> PokemonView`
  - fields: `en`, `ko`, `types_en`, `types_ko`, `base_stats`, `abilities_en`, `abilities_ko`
- Current `PokemonPanel` data structure:
  - stores UI state: `slot_number`, `is_selected`, `_current_hp`, `selected_move_index`, `move_buttons`
  - `set_pokemon(view: PokemonView)` writes labels and badges only
  - it does **not** currently store `view`
- Move selection state:
  - `PokemonPanel.selected_move_index: int | None`
  - set by `PokemonPanel.select_move(move_index)`
  - current move names are placeholder button labels, not real move data
- Current v0.6 usable fields:
  - slot index
  - HP percent (`PokemonPanel._current_hp`)
  - selected move index, if any
  - displayed Pokemon labels/types if read from widgets, but this is fragile
  - full reliable Pokemon data only if v0.6 stores `PokemonView` on the panel
- Missing fields:
  - actual selected move data
  - item
  - EV/IV/nature
  - ranks/boosts
  - weather/field
  - active ability choice when multiple abilities exist
  - exact current HP integer

## 5. Minimal Input Schema

Proposed JSON shape:

```json
{
  "scenario": {
    "mode": "ui-selected-pokemon-v0.6",
    "format_note": "UI-selected Pokemon only; no full battle state.",
    "known_limitations": [
      "Moves are not connected to real move data yet.",
      "Items, EVs, IVs, nature, ranks, weather, and field are omitted.",
      "Ability is listed from cached species data, not selected by battle state.",
      "HP is currently percentage-based UI state, not exact integer HP."
    ]
  },
  "pokemon": {
    "my_active": {
      "slot_index": 0,
      "en": "charizard",
      "ko": "리자몽",
      "types": ["fire", "flying"],
      "base_stats": {"hp": 78, "attack": 84, "defense": 78},
      "abilities": ["blaze", "solar-power"],
      "hp_percent": 100,
      "selected_move_index": null
    },
    "opponent_active": {
      "slot_index": 0,
      "en": "garchomp",
      "ko": "한카리아스",
      "types": ["dragon", "ground"],
      "base_stats": {"hp": 108, "attack": 130, "defense": 95},
      "abilities": ["sand-veil", "rough-skin"],
      "hp_percent": 100,
      "selected_move_index": null
    }
  }
}
```

Only include fields that can be read from stored `PokemonView` + current panel UI
state. If `PokemonView` is absent, fail before calling Gemini.

## 6. advisor_client Change Design

Keep existing demo function:

```python
run_spike_advice(model: str | None = None) -> tuple[str, dict[str, int], dict[str, Any]]
```

Add v0.6 function:

```python
run_ui_selected_advice(
    my_pokemon: dict[str, Any],
    opponent_pokemon: dict[str, Any],
    model: str | None = None,
) -> tuple[str, dict[str, int], dict[str, Any]]
```

`MainWindow` should pass plain dictionaries built from UI state. The client should
build the v0.6 JSON payload, call Gemini, log tokens, and return recommendation,
usage, and summary. It should not import PySide6 classes.

## 7. MainWindow Integration Plan

Before starting the worker, `MainWindow` should:

1. Read `selected_slots["team_my"]` and `selected_slots["team_enemy"]`.
2. If either is `None`, show a friendly error and do not start the worker.
3. Resolve panels from `my_team_column.panels[index]` and `opponent_team_column.panels[index]`.
4. Require each panel to have stored Pokemon data.
5. Build plain dictionaries with slot index, species names, types, base stats, abilities, HP percent, and selected move index.
6. Pass that payload to `LLMAdviceWorker`.

Required small UI model change for v0.6:

```python
class PokemonPanel:
    pokemon_view: PokemonView | None
```

`set_pokemon(view)` should assign `self.pokemon_view = view`; `clear_pokemon()`
should reset it. This is UI-state storage, not a damage engine change.

## 8. Error Handling

Required cases:

- My Pokemon is not selected:
  - `내 포켓몬을 먼저 선택하세요.`
- Opponent Pokemon is not selected:
  - `상대 포켓몬을 먼저 선택하세요.`
- Selected slot has no Pokemon data:
  - `선택된 슬롯에 포켓몬 정보가 없습니다.`
- Required stat or type data is missing:
  - `포켓몬 기본 정보가 부족합니다.`
- API key missing/invalid:
  - existing friendly key error
- Gemini HTTP error:
  - existing `Gemini API 오류: status code ...`
- TokenLogger failure:
  - recommendation still displays; status bar notes cost logging failure

## 9. Out of Scope

Not included in v0.6:

- `advisor/damage/` changes
- probability engine changes
- automatic LLM calls
- streaming
- Critic loop / self-review agent
- Minimax
- full battle state
- item / EV / IV / nature / rank / weather / field completion
- team builder completion
- real move data binding
- damage parity changes

## 10. Manual Verification Scenarios

1. Select one Pokemon in my team and one Pokemon in opponent team, then click `이번 턴 추천 받기`.
2. Confirm Gemini prompt uses selected species names instead of Mega Kangaskhan/Garchomp.
3. Click with no my-side Pokemon data and confirm friendly error.
4. Click with no opponent-side Pokemon selected and confirm friendly error.
5. Click with selected slot but empty Pokemon data and confirm friendly error.
6. Test invalid API key and confirm v0.5.1 friendly error still works.
7. Confirm button disables during request and re-enables afterward.
8. Confirm status bar token/cost output still works.
9. Run `uv run pytest -q` and keep the 613 default passing suite.

## 11. Rollback Plan

Rollback steps:

1. Revert `MainWindow` to call `run_spike_advice()` without UI-selected payload.
2. Remove any `pokemon_view` storage added to `PokemonPanel`.
3. Remove `run_ui_selected_advice()` from `llm/advisor_client.py`.
4. Keep `LLMAdvicePanel` itself; v0.5 hardcoded spike remains usable.
5. Re-run pytest.

The rollback should restore v0.5.2 behavior: hardcoded Mega Kangaskhan vs
Garchomp spike with the existing button, worker, and status bar.
