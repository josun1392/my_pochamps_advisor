# v8.1 Opponent Move Context Payload Contract

## Purpose

v8.1 locks the fixture-level payload contract for a future optional top-level `opponent_move_context`.

This is a contract/test step only:

- no runtime helper
- no payload adapter
- no prompt integration
- no UI behavior change
- no actual Gemini call
- no full Turn Engine

The contract separates explicitly known opponent moves from possible/unconfirmed candidate moves so the LLM can reason about opponent threats without treating candidates as confirmed selected moves or hidden set inference.

## Contract Shape

Draft future optional top-level field:

```python
{
    "opponent_move_context": {
        "kind": "opponent_move_context",
        "confidence": "limited",
        "selected_opponent_move": {
            "status": "unknown"
        },
        "known_opponent_moves": [
            {
                "source": "user_confirmed",
                "move_id": "thunderbolt",
                "name": "Thunderbolt",
                "type": "electric",
                "category": "special",
                "power": 90,
                "accuracy": 100,
                "priority": 0,
                "confirmed": True
            }
        ],
        "candidate_moves": [
            {
                "source": "visible_or_cache_candidate",
                "move_id": "quick-attack",
                "name": "Quick Attack",
                "type": "normal",
                "category": "physical",
                "power": 40,
                "accuracy": 100,
                "priority": 1,
                "confirmed": False,
                "selected": False
            }
        ],
        "priority_move_candidates": [
            {
                "source": "visible_or_cache_candidate",
                "move_id": "quick-attack",
                "name": "Quick Attack",
                "priority": 1,
                "confirmed": False,
                "selected": False
            }
        ],
        "unsupported": [
            "hidden moveset inference",
            "opponent set inference",
            "selected opponent move inference",
            "EV/IV/nature inference",
            "hidden item inference",
            "weather/terrain/boost inference",
            "RNG resolution",
            "full turn resolution"
        ],
        "safety_notes": [
            "Candidate moves are not confirmed selected moves.",
            "Only explicitly known or visible move data should be treated as known."
        ]
    }
}
```

## Allowed Values

`confidence`:

- `limited`
- `unknown`

Forbidden confidence values:

- `resolved`
- `certain`
- `confirmed_full_set`

`selected_opponent_move.status`:

- `unknown`
- `explicit`

`explicit` requires trusted source and explicit `move_id` / `name`.

Forbidden selected status values:

- `inferred`
- `predicted`
- `likely`

Trusted sources for known moves:

- `user_confirmed`
- `visible_ui`
- `explicit_input`

Candidate sources:

- `visible_or_cache_candidate`
- `champions_movepool`
- `visible_ui`

## Known Moves

`known_opponent_moves` may contain only moves explicitly confirmed by the user or visible UI state.

Required semantics:

- source is trusted
- `confirmed` is `True`
- candidate-only or metadata-only moves must not be placed here

Forbidden sources:

- `meta_inferred`
- `species_common_set`
- `usage_based_guess`

## Candidate Moves

`candidate_moves` are possible/unconfirmed moves only.

Required semantics:

- `confirmed` is `False`
- `selected` is `False`
- source identifies candidate origin

Forbidden candidate semantics:

- `confirmed=True`
- `selected=True`
- `will_use=True`
- `likely_selected=True`

Candidate moves may help the LLM mention possible threats, but only when labeled unconfirmed.

## Priority Candidates

`priority_move_candidates` are a filtered candidate view for moves with known positive priority.

They remain candidates:

- `confirmed=False`
- `selected=False`
- no selected-move inference
- no turn-order resolution

Priority metadata may be used only when trusted metadata exposes it.

## Move Metadata Allowed Fields

Allowed fields:

- `move_id`
- `name`
- `type`
- `category`
- `power`
- `accuracy`
- `priority`
- `target`
- `effect_flags`
- `source`
- `confirmed`
- `selected`

`effect_flags` is allowed only when a future trusted metadata source exposes safe normalized flags. v8.1 only locks the field name; it does not implement extraction.

## Forbidden Fields

The context must not include fields that imply hidden inference or resolved outcomes:

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

## Required Unsupported Boundaries

`unsupported` must include:

- hidden moveset inference
- opponent set inference
- selected opponent move inference
- EV/IV/nature inference
- hidden item inference
- weather/terrain/boost inference
- RNG resolution
- full turn resolution

## Prompt Safety Wording Candidate

Future prompt guard meaning:

```text
Opponent move context is based only on explicitly known or visible data.
Do not infer hidden movesets.
Do not treat candidate moves as confirmed selected moves.
Do not infer the opponent's selected move unless explicitly provided.
Do not infer EVs, IVs, nature, hidden item, weather, terrain, or boosts unless explicitly provided.
```

Korean documentation wording:

```text
상대 기술 정보는 명시적으로 알려진 정보 또는 UI에 보이는 정보에 한정한다.
후보 기술을 실제 선택 기술이나 실제 기술배치로 확정하지 않는다.
상대가 이번 턴 선택한 기술을 명시 입력 없이 추론하지 않는다.
EV/IV/nature, 숨겨진 아이템, 날씨, 필드, 랭크 보정은 명시 정보 없이 추정하지 않는다.
```

## Tests

v8.1 adds fixture-level tests in `tests/test_advisor_payload_contract.py`.

Coverage:

- valid fixture passes
- `confidence` allowed values only
- selected opponent move `unknown` allowed
- selected opponent move `explicit` allowed
- selected opponent move `inferred` / `predicted` / `likely` rejected
- known moves require trusted source
- candidate moves must not be confirmed or selected
- priority candidates must not be confirmed or selected
- forbidden fields rejected recursively
- required unsupported boundaries enforced
- safety notes include candidate-not-confirmed meaning
- prompt safety wording anchors locked

## Next Recommendation

Recommended next:

```text
v8.2 Opponent Move Context Helper
```

Scope:

- build a minimal helper that converts existing `opponent_moves` fixture/source dictionaries into the v8.1 contract shape
- preserve known vs candidate separation
- no hidden moveset inference
- no selected opponent move inference
- no runtime payload adapter yet unless explicitly scoped later

Safe alternatives:

```text
v8.2 Opponent Move Source Extraction Design
v8.2 Opponent Move Prompt Guard Design
```

## Safety Statement

- No production runtime helper was implemented.
- No payload adapter was implemented.
- No prompt integration was implemented.
- No UI checkbox behavior was changed.
- No actual Gemini call was made.
- No retry was made.
- No Vertex AI call was made.
- No full Turn Engine was implemented.
- No resolved turn order was implemented.
- No opponent set inference, hidden moveset inference, selected opponent move inference, EV/IV/nature inference, hidden item inference, or weather/terrain/boost inference was implemented.
- No speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update was implemented.
- No damage formula, raw damage rolls, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
