# v0.76 Charge Move Metadata Fixture Design

## Current State

v0.75 validated that the repo does not currently expose a stable charge-move metadata source for Power Herb.

Observed state:

- `data/static/moves.json`: not present.
- `data/cache/moves/`: not present.
- `data/cache/pokeapi/moves/`: present, but inspected move entries do not expose a charge-turn field suitable for the LLM payload.
- No confirmed `is_charge_move`, `charge_turn`, `two_turn`, `skip_charge`, or `power_herb_eligible` field exists in the current move metadata path.
- `core.move_repository.MoveView` exposes ordinary move metadata only: `move_id`, names, type, category, power, accuracy, and pp.
- Champions movepool cache entries expose move ids and ordinary move metadata, but not charge-turn eligibility.
- `data/static/items.json`, `data/static/items_damage.json`, and `data/static/champions_legal_items.json` do not currently confirm Power Herb metadata or legality.
- v0.74 designed an additive move-level `charge_context`, but there is no approved source to decide whether a move is Power Herb eligible.
- v0.75 explicitly rejected description text parsing.

Therefore Power Herb implementation should wait for a curated, deterministic, repo-native fixture or an equivalent explicit metadata source.

## Fixture Goal

The fixture should:

- represent charge move status as explicit metadata
- represent Power Herb eligibility separately from generic charge move status
- avoid move-description parsing
- make unknown or missing metadata safely unavailable
- support limited `charge_context` without a Turn Engine
- keep raw damage rolls unchanged
- keep raw `ko_context` unchanged
- make weather and item consumption limitations visible without simulating them

The fixture is not a damage formula input. It should only support a limited charge-move usability context.

## Proposed Fixture Path

### Option A - `data/static/charge_moves.json`

Dedicated fixture for charge move metadata.

Pros:

- simple, explicit purpose
- easy to validate with focused tests
- small implementation surface for v0.77
- avoids implying a full move metadata system

Cons:

- narrow scope
- future recharge / semi-invulnerable / weather-skip metadata may need schema expansion

### Option B - `data/static/move_metadata_overrides.json`

General override fixture for extra move metadata not present in the current move repository.

Pros:

- extensible for future metadata such as recharge, semi-invulnerable turn, high-crit flags, or weather-sensitive behavior
- can centralize move metadata patches

Cons:

- broader than the current Power Herb need
- easier to overgrow into a partial move database
- requires stricter schema boundaries

### Option C - `data/static/power_herb_eligible_moves.json`

Narrow allowlist only for Power Herb.

Pros:

- minimal
- very direct for v0.77/v0.78

Cons:

- hides the difference between "charge move" and "Power Herb eligible"
- less reusable for future charge-move context, weather notes, or rule validation
- can become item-specific logic instead of move metadata

T3 recommendation:

- Use `data/static/charge_moves.json` for v0.77.
- Keep it small and versioned.
- Defer `move_metadata_overrides.json` until the repo has multiple independent move metadata override needs.
- Avoid `power_herb_eligible_moves.json` because Power Herb eligibility should be one field on explicit charge move metadata, not the whole fixture identity.

## Proposed Schema

Recommended initial schema:

```json
{
  "version": "charge_moves_v1",
  "schema_notes": [
    "Explicit curated metadata for charge-move usability context.",
    "This fixture does not implement turn sequencing, weather, or item consumption."
  ],
  "moves": {
    "solar-beam": {
      "is_charge_move": true,
      "power_herb_eligible": true,
      "charge_type": "standard_charge",
      "known_exceptions": ["weather_can_affect_charge_turn"],
      "source": "curated_fixture",
      "confidence": "needs_rule_confirmation",
      "notes": "Weather interaction is not modeled."
    },
    "meteor-beam": {
      "is_charge_move": true,
      "power_herb_eligible": true,
      "charge_type": "standard_charge",
      "known_exceptions": ["secondary_effect_not_modeled"],
      "source": "curated_fixture",
      "confidence": "needs_rule_confirmation",
      "notes": "Stat boost and secondary effects are not modeled."
    }
  }
}
```

Field policy:

- `version`: required; starts at `charge_moves_v1`.
- `moves`: required object keyed by normalized lowercase hyphenated `move_id`.
- `is_charge_move`: required boolean.
- `power_herb_eligible`: required boolean.
- `charge_type`: required label, not a simulator. Initial labels can include:
  - `standard_charge`
  - `semi_invulnerable_charge`
  - `rule_sensitive_charge`
  - `deferred_validation`
- `known_exceptions`: optional array of labels.
- `source`: required string. Initial value can be `curated_fixture`.
- `confidence`: required label. Suggested values:
  - `confirmed`
  - `needs_rule_confirmation`
  - `deferred`
- `notes`: required short text, especially for weather, item consumption, secondary effects, or edge cases.

The fixture should not store final turn probabilities, final damage changes, or item consumption state.

## Initial Move Scope

Candidate moves requested for validation:

| move_id | repo/cache presence | recommended v0.77 fixture treatment |
| --- | --- | --- |
| `solar-beam` | Champions movepool, pokemon cache, ko mapping, PokeAPI index | include candidate; standard charge; weather note |
| `solar-blade` | Champions movepool, pokemon cache, ko mapping | include candidate; standard charge; weather note |
| `meteor-beam` | Champions movepool, pokemon cache, ko mapping | include candidate; standard charge; secondary effect note |
| `sky-attack` | Champions movepool, pokemon cache, ko mapping | include candidate; standard charge; secondary effect note |
| `skull-bash` | pokemon cache, ko mapping, PokeAPI index; no Champions movepool hit in this pass | defer or include only if fixture design accepts non-Champions-cache candidates |
| `fly` | Champions movepool, pokemon cache, ko mapping, PokeAPI index | defer for semi-invulnerable policy |
| `dig` | Champions movepool, pokemon cache, ko mapping, PokeAPI index | defer for semi-invulnerable policy |
| `dive` | Champions movepool, pokemon cache, ko mapping | defer for semi-invulnerable policy |
| `bounce` | Champions movepool, pokemon cache, ko mapping | defer for semi-invulnerable policy |
| `razor-wind` | not observed in inspected repo/cache paths | defer; not initial implementation scope |
| `phantom-force` | Champions movepool, pokemon cache, ko mapping | defer for semi-invulnerable / rule policy |
| `shadow-force` | not observed in inspected repo/cache paths | defer; not initial implementation scope |
| `freeze-shock` | not observed in inspected repo/cache paths | defer; not initial implementation scope |
| `ice-burn` | not observed in inspected repo/cache paths | defer; not initial implementation scope |
| `geomancy` | not observed in inspected repo/cache paths | defer; special/rule-sensitive |

Recommended minimal v0.77 implementation scope:

- include `solar-beam`
- include `solar-blade`
- include `meteor-beam`
- include `sky-attack`
- optionally include `skull-bash` only if T1/T2 accept `ko_mapping` / pokemon cache presence as enough for metadata fixture candidates

Deferred until a second fixture pass:

- semi-invulnerable moves: `fly`, `dig`, `dive`, `bounce`, `phantom-force`
- absent candidates: `razor-wind`, `shadow-force`, `freeze-shock`, `ice-burn`, `geomancy`

Important distinction:

- "present in cache" means the move id exists somewhere in repo data.
- It does not prove Champions/PoChamps legality, current Pokemon eligibility, or Power Herb behavior.
- Fixture entries should be curated rule metadata, not inferred from description text.

## Eligibility Policy

Move id normalization:

- Use lowercase hyphenated slugs.
- Trim whitespace.
- Convert spaces and underscores to hyphens.
- Do not rely on localized names.
- Do not parse move descriptions.

Available policy:

- The attacker item must be `power-herb`.
- The item status must be `user_confirmed`.
- The move id must normalize to a fixture key.
- The fixture entry must have `is_charge_move=true`.
- The fixture entry must have `power_herb_eligible=true`.

Unavailable policy:

- no user-confirmed Power Herb -> `no_power_herb` or `item_not_user_confirmed`
- unsupported charge item -> `unsupported_charge_item`
- move id missing or unknown -> `move_charge_metadata_missing`
- move id not present in fixture -> `move_charge_metadata_missing` unless a future repository can prove non-charge status
- move id present with `is_charge_move=false` -> `move_not_charge_move`
- move id present with `power_herb_eligible=false` -> `move_not_charge_move` or a future more specific reason such as `not_power_herb_eligible`

The safest first implementation should avoid broad non-charge conclusions. If the fixture is a charge-move list only, absence means missing metadata, not proof of non-charge behavior.

Safety invariants:

- user-confirmed Power Herb only
- explicit charge metadata only
- raw damage unchanged
- raw `ko_context` unchanged
- `turn_sequence_integrated=false`
- `item_consumption_tracked=false`
- final turn outcome not calculated
- weather exceptions only appear in notes/limitations
- item already consumed state is not inferred

## Repository / Helper Design

Recommended follow-up helper:

- `core/charge_move_repository.py`

Alternative:

- `core/move_metadata_repository.py`

T3 recommendation:

- Start with `core/charge_move_repository.py` because the first fixture is narrow and can stay easy to test.
- Defer a broader `move_metadata_repository.py` until more move metadata fixtures exist.

Helper responsibilities:

- load `data/static/charge_moves.json`
- validate `version`
- validate normalized move ids
- expose `normalize_move_id(move_id)`
- expose `get_charge_move_metadata(move_id)`
- expose `is_power_herb_eligible(move_id)`
- return safe unavailable reasons without guessing

The LLM context builder should depend on this helper/repository, not a hardcoded move list inside `llm/advisor_damage_estimate.py`.

## Test Plan

Fixture/repository tests:

- fixture loads
- `version` exists and equals `charge_moves_v1`
- `moves` exists and is an object
- move ids are unique by JSON key
- move ids are normalized lowercase hyphenated slugs
- required fields exist for every entry
- `solar-beam` returns charge metadata if included
- `meteor-beam` returns charge metadata if included
- unknown move returns unavailable safely
- no description parsing is used

Future `charge_context` implementation tests:

- known charge move + user-confirmed Power Herb -> `charge_context.available=true`
- non-charge move explicitly in fixture -> unavailable `move_not_charge_move`
- missing metadata -> unavailable `move_charge_metadata_missing`
- no Power Herb -> unavailable `no_power_herb`
- unconfirmed Power Herb -> unavailable `item_not_user_confirmed`
- raw damage min/max/rolls unchanged
- raw `ko_context` unchanged
- `charge_context` does not alter OHKO chance
- candidate moves excluded
- prompt guardrails
- existing Loaded Dice multi-hit regression
- existing King's Rock flinch regression
- existing Scope Lens critical regression
- existing Bright Powder accuracy regression
- existing recovery context regression
- existing KO context regression
- full pytest

## Interaction With v0.74 Charge Context

The fixture should feed v0.78 `charge_context` as follows:

- move payload remains the placement point
- `charge_context` remains a move-level sibling
- `damage_estimate` remains unchanged
- `ko_context` remains unchanged
- `turn_sequence_integrated=false`
- `item_consumption_tracked=false`
- weather interaction is not modeled
- final turn outcome is not calculated

The fixture only answers whether a move is a curated Power Herb eligible charge move under limited assumptions. It does not say Power Herb is still unconsumed or that the move definitely resolves in one turn.

## Recommended v0.77 Path

### Candidate A - v0.77 Charge Move Metadata Fixture Implementation

Recommended.

Scope:

- add `data/static/charge_moves.json`
- add a narrow repository/helper
- add fixture/repository tests
- no LLM `charge_context` yet
- no payload contract change beyond possible docs note if needed
- no damage formula change
- no raw roll change

Why:

- separates metadata source creation from LLM context behavior
- lets T1/T2 approve initial move scope before Power Herb language appears in Gemini prompts
- keeps v0.77 small and reviewable

### Candidate B - v0.77 Power Herb Limited Charge Context Implementation

Not recommended yet.

Risk:

- combines fixture creation, repository behavior, LLM payload changes, prompt guardrails, and tests in one step
- makes eligibility policy harder to review
- increases chance of accidental final turn outcome wording

T3 recommendation:

- v0.77 should implement only the metadata fixture and helper.
- v0.78 should implement Power Herb limited `charge_context` using the approved repository.

## Out of Scope

The v0.76 fixture design excludes:

- code implementation
- fixture implementation
- `charge_context` implementation
- Power Herb implementation
- item consumption tracking
- turn-sequence-adjusted KO probability
- Turn Engine
- weather interaction
- damage formula change
- raw damage roll modification
- KO context modification
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits
