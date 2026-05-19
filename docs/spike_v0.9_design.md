# Spike v0.9 Design — Selected Move Damage Estimate

## 1. Goal

v0.9 adds a default-assumption damage estimate for exactly one move: the user's currently selected `moves.my_selected_move`.

The goal is to let the Gemini advisor see a deterministic damage range for the selected move without pretending that the app knows the full battle state. The estimate is a rough reference only. It is not final battle damage.

v0.9 must:

- calculate damage only when `my_selected_move` is present
- keep four-move comparison out of scope until v0.10
- keep OHKO, 2HKO, and KO chance out of scope
- use explicit default assumptions
- preserve the v0.8.3 payload contract guardrails
- use existing public damage APIs
- avoid changes to `advisor/damage/`

## 2. Current State

The current UI payload mode is:

```text
ui-selected-pokemon-v0.8
```

The payload already includes:

- selected my-side Pokemon identity
- selected opponent Pokemon identity
- type lists
- base stats
- ability name lists
- HP percent
- selected move slot index
- user-confirmed move metadata for my side

The payload does not include:

- final calculated stats
- EV/IV/nature
- held item
- selected ability certainty
- weather
- terrain
- boosts
- screens
- exact current HP integer
- opponent moves
- damage rolls
- OHKO/2HKO/KO chance
- turn order
- Turn Engine state

## 3. Repo Audit

### Damage API

Relevant files:

- `advisor/damage/formula.py`
- `advisor/damage/calculator.py`
- `advisor/damage/stats.py`
- `advisor/damage/field.py`
- `advisor/damage/types.py`
- `tests/damage/test_roll.py`
- `scripts/spike_advisor.py`

The public damage entry points are usable for v0.9:

- `advisor.damage.formula.DamageContext`
- `advisor.damage.formula.calc_damage_rolls(ctx)`
- `advisor.damage.calculator.calculate(ctx, roll_mode="deterministic")`

`calc_damage_rolls(ctx)` returns the full 16-roll list and is the better v0.9 choice because the payload may include `rolls` plus min/max without relying on a projected output mode.

`DamageContext` requires the v0.9 helper to provide:

- `attacker_level`
- `move_power`
- `attack_stat`
- `defense_stat`
- `move_type`
- `move_id`
- `attacker_types`
- `defender_types`
- `is_physical`
- `is_critical`
- `is_spread`
- `field`

Optional but useful fields:

- `attacker_species`
- `defender_species`
- `attacker_hp_current`
- `attacker_hp_max`
- `defender_hp_current`
- `defender_hp_max`
- `attacker_stats`
- `defender_stats`
- `attacker_boosts`
- `defender_boosts`

### Stats and Default Assumptions

`advisor/damage/stats.py` provides:

- `StatBlock`
- `StatInputs`
- `final_stats(inputs, ...)`
- `nature_from_name(name)`

Base stats from `core/pokemon_repository.PokemonView` use PokeAPI keys:

- `hp`
- `attack`
- `defense`
- `special-attack`
- `special-defense`
- `speed`

Damage stats use `StatBlock` keys:

- `hp`
- `atk`
- `def_`
- `spa`
- `spd`
- `spe`

v0.9 can build default final stats with:

- level 50
- all IVs 31
- all EVs 0
- neutral nature, recommended `hardy`
- rule set `gen9`
- no item
- no ability stat application
- no weather
- no terrain
- no boosts

The result is still a default stat profile, not confirmed in-battle stats.

### Field Defaults

`advisor/damage/field.py` provides `Field()` with:

- weather `none`
- terrain `none`
- no side fields
- `is_doubles=True` by default

For v0.9, the helper should set `Field(is_doubles=False)` unless the project explicitly decides that PoChamps should default to doubles. The existing spike and UI advisor are one-turn single-battle recommendation flows; a single-target selected move estimate should not apply spread reduction by default.

`DamageContext.is_spread` should be `False` in v0.9 because spread move targeting and doubles board state are not connected.

### Type Data

`advisor/damage/types.py` loads the Gen 9 type chart from `data/static/type_chart_gen9.json`. `calc_damage_rolls(ctx)` already applies type effectiveness through the formula path, so the v0.9 helper does not need to compute type effectiveness separately.

### Probability Layer

`advisor/probability/single_hit.py` and `advisor/probability/composer.py` can compute KO probability when target HP and damage outcomes are known. v0.9 should not use them yet.

Reasons:

- exact HP is not connected
- final stats are default assumptions only
- crit, accuracy, multihit, residual chip, and turn timing are not integrated into this payload path
- adding KO chance would make the LLM more likely to overstate confidence

### UI and Payload Sources

Relevant files:

- `ui/main_window.py`
- `ui/widgets/pokemon_panel.py`
- `core/pokemon_repository.py`
- `core/move_repository.py`
- `llm/advisor_payload_contract.py`
- `llm/advisor_client.py`

`MainWindow._build_llm_battle_input()` already creates:

- `pokemon.my_active`
- `pokemon.opponent_active`
- `moves.my_selected_move_index`
- `moves.my_available_moves`
- `moves.my_selected_move`

`PokemonPanel` stores:

- `pokemon_view`
- `current_hp_percent`
- `selected_move_index`
- `selected_moves`

`MoveView` provides the fields needed for simple damaging moves:

- `move_id`
- `name_en`
- `name_ko`
- `type`
- `category`
- `power`
- `accuracy`
- `pp`

`category == "physical"` maps to attack vs defense. `category == "special"` maps to special attack vs special defense. `category == "status"` or `power is None` should be unavailable in v0.9.

## 4. Default Assumptions

v0.9 should use this stat and field profile:

```json
{
  "level": 50,
  "ivs": "31 all",
  "evs": "0 all",
  "nature": "neutral",
  "item": "none",
  "boosts": "none",
  "weather": "none",
  "terrain": "none",
  "screens": "none",
  "critical": false,
  "roll": "16-roll range",
  "spread": false,
  "exact_hp": "unavailable; percent range uses default defender HP stat"
}
```

Important wording:

- This is not a real team spread.
- This is not final battle damage.
- This is a default-assumption reference estimate.
- The LLM may compare this estimate only within the stated assumptions.

## 5. Design Options

### Option A — Damage Range Only

Output:

- min damage
- max damage
- optional full rolls
- no percent range
- no KO chance

Pros:

- smallest implementation
- lowest risk of overclaiming
- avoids the "what is max HP?" decision

Cons:

- raw HP damage is less useful to users
- LLM may struggle to explain significance without percent context
- still needs default attack/defense stats, so it does not avoid the default profile decision

### Option B — Damage Range + Percent Range

Output:

- min damage
- max damage
- full 16 rolls
- defender default max HP
- percent range against default max HP
- explicit assumptions and limitations
- no KO chance

Pros:

- useful enough for user-facing advice
- keeps confidence bounded
- uses existing stats and damage APIs
- avoids probability scope creep
- establishes the shape v0.10 can reuse for four moves

Cons:

- percent range may look more authoritative than it is
- requires strong payload and prompt language that default HP is not confirmed exact HP

### Option C — Damage Range + OHKO Chance

Output:

- all of Option B
- 16-roll OHKO chance

Pros:

- more immediately actionable
- probability helpers already exist

Cons:

- scope creep for v0.9
- easy for the LLM to overstate
- exact current HP is not connected
- accuracy, crit, multihit, residuals, and turn state are not ready in this path
- better handled after the four-move estimate shape is stable

### Recommendation

T3 recommendation: **Option B**.

v0.9 should provide damage range plus percent range using default defender HP. It should not provide OHKO, 2HKO, or KO chance. The payload must make the default assumptions and non-final status impossible to miss.

## 6. Proposed Payload Schema

Attach the estimate to `moves.my_selected_move.damage_estimate`.

Rationale:

- the estimate belongs to the selected move
- v0.10 can reuse the same `damage_estimate` shape on each entry of `moves.my_available_moves`
- the top-level payload remains readable

Example:

```json
{
  "moves": {
    "my_selected_move": {
      "slot": 0,
      "move_id": "flamethrower",
      "name_en": "Flamethrower",
      "name_ko": "Flamethrower",
      "type": "fire",
      "category": "special",
      "power": 90,
      "accuracy": 100,
      "pp": 15,
      "damage_estimate": {
        "status": "available_with_default_assumptions",
        "scope": "selected_move_only",
        "is_final_battle_damage": false,
        "selected_move_id": "flamethrower",
        "damage_range": {
          "min": 32,
          "max": 39
        },
        "percent_range": {
          "min": 17.4,
          "max": 21.3,
          "denominator": "default_defender_max_hp"
        },
        "rolls": [32, 33, 33, 34, 34, 35, 35, 36, 36, 37, 37, 38, 38, 39, 39, 39],
        "assumptions": {
          "level": 50,
          "ivs": "31 all",
          "evs": "0 all",
          "nature": "neutral",
          "item": "none",
          "boosts": "none",
          "weather": "none",
          "terrain": "none",
          "screens": "none",
          "critical": false,
          "spread": false,
          "rule_set": "gen9"
        },
        "derived_stats": {
          "attacker": {
            "attack_stat_used": 161,
            "attack_stat_name": "spa"
          },
          "defender": {
            "defense_stat_used": 105,
            "defense_stat_name": "spd",
            "default_max_hp": 183
          }
        },
        "limitations": [
          "This is not final battle damage.",
          "EV/IV/nature/item/final stats are not connected.",
          "Weather, terrain, boosts, screens, exact HP, and Turn Engine state are not connected.",
          "Use as rough reference only."
        ]
      }
    }
  }
}
```

The actual numeric values above are illustrative. v0.9 tests should assert schema and consistency, not copy these example numbers unless they are generated from a fixture.

### Unavailable Schema

When damage cannot be calculated, keep a stable object:

```json
{
  "status": "unavailable_status_move",
  "scope": "selected_move_only",
  "is_final_battle_damage": false,
  "selected_move_id": "will-o-wisp",
  "reason": "Selected move is a status move.",
  "assumptions": {
    "level": 50,
    "ivs": "31 all",
    "evs": "0 all",
    "nature": "neutral",
    "item": "none",
    "boosts": "none",
    "weather": "none",
    "terrain": "none",
    "screens": "none",
    "critical": false,
    "spread": false,
    "rule_set": "gen9"
  },
  "limitations": [
    "No damage estimate is available for this selected move.",
    "Do not infer damage, OHKO/2HKO, or KO chance."
  ]
}
```

Recommended statuses:

- `available_with_default_assumptions`
- `unavailable_no_selected_move`
- `unavailable_status_move`
- `unavailable_missing_power`
- `unavailable_missing_pokemon`
- `unavailable_missing_base_stats`
- `unavailable_missing_type`
- `unavailable_unsupported_category`
- `unavailable_engine_error`

## 7. Integration Plan

Do not put damage math inside `MainWindow`.

Add a helper module:

```text
llm/advisor_damage_estimate.py
```

Primary function:

```python
def build_selected_move_damage_estimate(battle_input: dict) -> dict:
    ...
```

Responsibilities:

1. Read `pokemon.my_active`, `pokemon.opponent_active`, and `moves.my_selected_move`.
2. Return an unavailable estimate if required data is missing.
3. Convert PokeAPI stat keys to `StatBlock`.
4. Build default `StatInputs` for attacker and defender.
5. Call `final_stats(...)` with default assumptions.
6. Choose `attack_stat` and `defense_stat` from move category.
7. Build `DamageContext`.
8. Call `calc_damage_rolls(ctx)`.
9. Return available estimate with min/max, rolls, default HP denominator, percent range, assumptions, derived stats, and limitations.

Integration point:

```python
battle_input = self._build_llm_battle_input()
battle_input["moves"]["my_selected_move"]["damage_estimate"] = build_selected_move_damage_estimate(battle_input)
```

Better integration shape:

```python
battle_input = self._build_llm_battle_input()
attach_selected_move_damage_estimate(battle_input)
```

This keeps `MainWindow` as payload collector and delegates calculation to the helper.

### Why `llm/` Is Acceptable

The helper is for advisor payload enrichment, not core damage behavior. It should use `advisor/damage` as a dependency but remain outside the engine. If the project later adds a broader payload package, this helper can move to `advisor/payload/` without changing the damage engine.

## 8. Context Construction Details

### Stat Conversion

Convert:

```text
hp -> hp
attack -> atk
defense -> def_
special-attack -> spa
special-defense -> spd
speed -> spe
```

Default blocks:

```python
DEFAULT_LEVEL = 50
DEFAULT_IVS = StatBlock(31, 31, 31, 31, 31, 31)
DEFAULT_EVS = StatBlock(0, 0, 0, 0, 0, 0)
DEFAULT_BOOSTS = StatBlock(0, 0, 0, 0, 0, 0)
```

Use `nature_from_name("hardy")` or `(None, None)` for neutral nature.

### Move Category

Rules:

- `physical`: use attacker `atk`, defender `def_`
- `special`: use attacker `spa`, defender `spd`
- `status`: unavailable
- anything else: unavailable

### DamageContext Defaults

Use:

```python
DamageContext(
    attacker_level=50,
    move_power=move["power"],
    attack_stat=selected_attacking_stat,
    defense_stat=selected_defending_stat,
    move_type=move["type"],
    move_id=move["move_id"],
    attacker_types=tuple(my_active["types"]),
    defender_types=tuple(opponent_active["types"]),
    is_physical=move["category"] == "physical",
    is_critical=False,
    is_spread=False,
    field=Field(is_doubles=False),
    attacker_species=my_active["name_en"],
    defender_species=opponent_active["name_en"],
    attacker_stats=attacker_stats,
    defender_stats=defender_stats,
    attacker_boosts=DEFAULT_BOOSTS,
    defender_boosts=DEFAULT_BOOSTS,
    attacker_hp_current=attacker_stats.hp,
    attacker_hp_max=attacker_stats.hp,
    defender_hp_current=None,
    defender_hp_max=defender_stats.hp,
)
```

No item or ability object should be selected in v0.9 because current payload lists possible abilities but does not know the active ability. This avoids false precision. Ability effects can be added later when active ability selection is connected.

### Percent Range

Use default defender HP from the default stat profile:

```text
percent = damage / default_defender_max_hp * 100
```

Round to one decimal place for payload readability.

The payload must label the denominator as `default_defender_max_hp`, not exact current HP.

## 9. Contract Update Plan

Update `docs/advisor_payload_contract.md`:

- add `damage_estimate` under `moves.my_selected_move`
- define available and unavailable statuses
- define default assumptions
- state that default-assumption percent range uses default defender max HP
- state that v0.9 still does not provide KO chance
- state that the LLM may discuss damage only with phrases like "under default assumptions"
- state that the LLM must not call the estimate final battle damage

Update `llm/advisor_payload_contract.py`:

- add constants for `ADVISOR_DAMAGE_ASSUMPTIONS`
- add constants for damage estimate statuses
- update known limitations to distinguish "damage calculation is not connected in v0.8" from "damage estimate is default-assumption only in v0.9"

Recommended v0.9 limitation wording:

```text
Damage estimate, when present, uses default assumptions and is not final battle damage.
Do not infer OHKO/2HKO or KO chance unless explicit KO probability fields are provided.
EV/IV/nature/item/final stats, active ability, weather, terrain, boosts, screens, exact HP, and Turn Engine state are not connected.
```

Update `llm/advisor_client.py` prompt text:

- keep concise recommendation behavior
- explicitly say damage estimates are usable only under their assumptions
- prohibit final-damage language unless `is_final_battle_damage` is true
- prohibit KO chance language unless KO probability fields exist

## 10. Error Handling

`build_selected_move_damage_estimate(...)` should never raise for ordinary incomplete UI state. It should return an unavailable object.

Cases:

- no selected move: `unavailable_no_selected_move`
- selected move power is `None`: `unavailable_missing_power`
- selected move category is `status`: `unavailable_status_move`
- selected move category not `physical` or `special`: `unavailable_unsupported_category`
- attacker or defender missing: `unavailable_missing_pokemon`
- base stats missing or incomplete: `unavailable_missing_base_stats`
- attacker or defender type missing: `unavailable_missing_type`
- damage engine exception: `unavailable_engine_error`
- exact HP unavailable: still available, but percent denominator must be `default_defender_max_hp`
- Gemini API key missing or invalid: no change from current UI error handling; this is outside damage estimate construction

For engine errors, include a short safe reason:

```json
{
  "status": "unavailable_engine_error",
  "reason": "Damage engine failed while calculating the selected move estimate."
}
```

Do not include tracebacks in the Gemini payload.

## 11. Tests

Recommended new tests:

```text
tests/test_advisor_damage_estimate.py
```

Test cases:

1. default assumptions object is stable
2. Charizard vs Garchomp + Flamethrower returns available estimate
3. available estimate includes min/max, 16 rolls, percent range, assumptions, limitations
4. status move returns `unavailable_status_move`
5. selected move missing returns `unavailable_no_selected_move`
6. move with missing power returns `unavailable_missing_power`
7. physical move uses `atk` vs `def_`
8. special move uses `spa` vs `spd`
9. missing Pokemon/base stats/types returns unavailable instead of raising
10. contract guardrails still contain no-KO and non-final-damage language

Update existing payload contract tests:

- assert `damage_estimate` location and status shape when attached
- assert no OHKO/2HKO/KO chance fields appear in v0.9

Expected test count:

- current: 616 passed, 2 deselected
- v0.9 likely adds 8 to 12 tests
- expected after v0.9: about 624 to 628 passed, 2 deselected

Run:

```powershell
uv run pytest tests/test_advisor_damage_estimate.py -q
uv run pytest tests/test_advisor_payload_contract.py -q
uv run pytest -q
```

## 12. Manual Verification Scenarios

### Charizard vs Garchomp + Flamethrower

Steps:

1. Select Charizard as my active Pokemon.
2. Select Garchomp as opponent active Pokemon.
3. Select move slot 1.
4. Assign Flamethrower.
5. Request LLM advice.
6. Inspect payload or debug output.

Expected:

- `moves.my_selected_move.damage_estimate.status` is `available_with_default_assumptions`
- `selected_move_id` is `flamethrower`
- `damage_range` is present
- `percent_range` is present and uses `default_defender_max_hp`
- `is_final_battle_damage` is `false`
- LLM refers to default assumptions, not final damage

### No Selected Move

Expected:

- no damage estimate is attached, or estimate status is `unavailable_no_selected_move`
- UI still calls Gemini if the current product decision allows species-only advice
- LLM does not invent damage

### Status Move

Example:

- Will-O-Wisp or Swords Dance

Expected:

- `status` is `unavailable_status_move`
- no damage range
- LLM states that selected move has no direct damage estimate

### Missing Power

Expected:

- `status` is `unavailable_missing_power`
- no damage range
- no exception escapes into the UI thread

### Gemini Payload Check

Expected:

- `damage_estimate` appears only for the selected move in v0.9
- `my_available_moves` does not become a four-move comparison yet
- no KO chance fields exist

### Regression

Expected:

- `uv run pytest -q` remains green
- no slow perf tests required for v0.9

## 13. Out of Scope

v0.9 excludes:

- four-move damage comparison
- OHKO/2HKO/KO chance
- opponent move damage
- Turn Engine
- EV/IV/nature/item input UI
- final stats input UI
- weather/terrain/boost/screen UI
- active ability selection
- damage engine modification
- Minimax or critic loop
- automatic LLM calls
- streaming, cancel, or retry

## 14. Rollback Plan

To roll back v0.9 implementation later:

1. Remove `llm/advisor_damage_estimate.py`.
2. Remove calls that attach `damage_estimate` to `battle_input`.
3. Revert `docs/advisor_payload_contract.md` to the v0.8.3 contract language.
4. Revert `llm/advisor_payload_contract.py` damage-estimate constants.
5. Revert `llm/advisor_client.py` prompt additions.
6. Remove `tests/test_advisor_damage_estimate.py` and any v0.9-specific payload assertions.
7. Run `uv run pytest -q`.

This restores the v0.8.3 state where the LLM sees selected Pokemon and user-confirmed move metadata, but no damage estimate.

## 15. T1/T2 Decisions Needed Before Implementation

1. Confirm Option B.
2. Confirm default level 50.
3. Confirm rule set `gen9` for the temporary default stat profile, rather than `champions`.
4. Confirm `Field(is_doubles=False)` for selected single-target estimate.
5. Confirm no active ability selection in v0.9, despite ability lists being present.
6. Confirm `moves.my_selected_move.damage_estimate` as the schema location.
7. Confirm no OHKO/2HKO/KO chance fields in v0.9.
