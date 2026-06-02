# v0.75 Charge Move Rule Validation Design

## Current State

v0.74 designed Power Herb as limited charge-turn usability context, not as a direct damage boost. The proposed field was an additive move-level `charge_context` sibling that must not alter `damage_estimate`, raw rolls, or `ko_context`.

Current implemented context layers remain:

- `damage_estimate` provides raw damage min/max/rolls.
- `ko_context` provides limited raw damage-roll KO/OHKO/2HKO context.
- `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, and `multi_hit_context` are additive limited contexts.
- Power Herb has no `charge_context` implementation.
- Turn Engine, item consumption tracking, weather interaction, and turn-sequence-adjusted KO probability are absent.

The key open issue is source quality. The repo does not currently expose a confirmed LLM-facing charge move metadata field.

Inspected source status:

- `data/static/moves.json`: not present.
- `data/cache/moves/`: not present.
- `data/cache/pokeapi/moves/`: present, but current cache/index shape is not a reliable charge metadata source for the LLM payload.
- `data/static/move_flags.json`: present, but no charge/charging flag.
- `data/cache/champions/regulation_m_a/pokemon_movepools/*.json`: present and contains move entries such as Solar Beam, Meteor Beam, Sky Attack, Fly, Dig, Dive, Bounce, and Solar Blade, but entries only expose fields such as `move_id`, `name_en`, `type`, `category`, `power`, `accuracy`, `pp`, `source_refs`, `confidence`, and `metadata_source`.
- `core.move_repository.MoveView`: exposes only `move_id`, `name_en`, `name_ko`, `type`, `category`, `power`, `accuracy`, and `pp`.
- `data/static/items.json`, `data/static/items_damage.json`, and `data/static/champions_legal_items.json`: no `power-herb` / Power Herb entry found by string search.

## Validation Questions

### Does the repo have move metadata files?

Yes, but not in the requested `data/static/moves.json` location.

Observed:

- `data/static/moves.json`: not present.
- `data/cache/moves/`: not present.
- `data/cache/pokeapi/moves/`: present as numeric PokeAPI cache files.
- `data/cache/champions/regulation_m_a/pokemon_movepools/`: present as Champions/Serebii-derived per-Pokemon movepool JSON.
- `data/static/move_flags.json`: present as a small flag fixture for ability/item-related move flags.

### Does move metadata include a charge-turn field?

No confirmed repo-native charge-turn field was found.

Observed:

- `MoveView` does not include `is_charge_move`, `charge_turn`, `two_turn`, `volatile`, `flags`, or equivalent.
- Champions movepool move entries do not include a charge-turn field.
- `move_flags.json` does not include charge flags.
- Cached PokeAPI move entries inspected for numeric ids such as `76` Solar Beam and `130` Skull Bash had `meta: null` and no directly usable charge field.

### Can Solar Beam / Meteor Beam / Sky Attack / Skull Bash be distinguished?

They can be identified by normalized `move_id` when present in Champions movepool cache, but not as charge moves by metadata.

Observed examples:

- `solar-beam` appears in Champions movepool cache with normal damage metadata.
- `meteor-beam` appears in Champions movepool cache with normal damage metadata.
- `sky-attack` appears in Champions movepool cache with normal damage metadata.
- `skull-bash` appears in `data/ko_mapping.json`, but no direct Champions movepool example was confirmed during this pass.
- These entries lack charge eligibility fields.

This means current repo state can identify a move's id, but cannot reliably classify charge behavior without an allowlist or new metadata.

### Does any field directly indicate Power Herb applicability?

No. No direct `power_herb`, `charge_item`, `charge_move`, or `skip_charge` metadata was found.

### Does item metadata describe Power Herb?

No local static item metadata for Power Herb was found in the inspected item files:

- `data/static/items.json`: no Power Herb entry.
- `data/static/items_damage.json`: no Power Herb entry.
- `data/static/champions_legal_items.json`: no `power-herb` entry.

Historical docs and sample-validation notes mention `power-herb` as an excluded unknown item idea, but those are not legal item metadata.

### Can Champions legality for Power Herb be confirmed?

Not from the current static legal item fixture.

`data/static/champions_legal_items.json` includes legal herbs such as Mental Herb and White Herb, but no Power Herb entry was found. Therefore Power Herb should currently be treated as absent/unknown from the Champions legal item fixture until a separate item legality update validates it.

### What is the move id normalization policy?

Repo item normalization is explicit in `core.champions_item_repository.normalize_item_id`:

- strip whitespace
- lowercase
- remove straight and curly apostrophes
- replace underscores with hyphens
- replace spaces with hyphens

Move ids are already stored as lowercase hyphenated ids in move payloads and Champions movepool cache, such as `solar-beam` and `meteor-beam`.

Recommended move id normalization for charge metadata:

- strip whitespace
- lowercase
- replace spaces and underscores with hyphens
- preserve existing hyphenated move ids
- do not parse localized names for rule matching

### What move metadata reaches the current payload?

For selected/available moves and opponent known moves, the payload currently carries:

- `slot`
- `move_id`
- `name_en`
- `name_ko`
- `type`
- `category`
- `power`
- `accuracy`
- `pp`

No charge-turn field reaches `llm/advisor_damage_estimate.py` today.

## Candidate Rule Sources

### Option A - Existing move metadata field

Use a repo-native move field such as `is_charge_move` if it exists.

Pros:

- Best long-term shape.
- Easy to maintain once source is authoritative.
- Avoids duplicate rule tables.
- Lets `charge_context` follow the same pattern as `accuracy_context` and `multi_hit_context`.

Cons:

- No such field was found in the current payload, Champions cache, or `MoveView`.
- v0.76 cannot safely implement this without adding metadata first.

Verdict:

- Preferred if a charge field is added.
- Not available now.

### Option B - Curated static charge move allowlist

Add a small static fixture such as `data/static/charge_moves.json`.

Example shape:

```json
{
  "schema_version": "charge-moves-v1",
  "source": "curated_static",
  "charge_moves": {
    "solar-beam": {
      "name_en": "Solar Beam",
      "power_herb_eligible": true,
      "notes": ["Weather exceptions are not modeled."]
    },
    "meteor-beam": {
      "name_en": "Meteor Beam",
      "power_herb_eligible": true,
      "notes": ["Stat-change side effects are not modeled."]
    }
  }
}
```

Pros:

- Clear and testable.
- Does not require parsing descriptions.
- Can include only approved charge moves.
- Can encode `power_herb_eligible` separately from generic two-turn/semi-invulnerable moves if needed.

Cons:

- Fixture management required.
- Risk of omission or stale rule coverage.
- Needs source notes and review discipline.

Verdict:

- Best practical next step if T1/T2 want implementation soon.
- Should be designed explicitly before code implementation.

### Option C - Move description text parsing

Infer charge moves from effect text.

Pros:

- Could work if descriptions were complete.
- Avoids a hand-maintained allowlist.

Cons:

- Current cached PokeAPI entries inspected did not expose reliable effect text for charge moves.
- Text parsing is brittle.
- English wording may change.
- It risks false positives such as "charge" in non-charge moves or unrelated descriptions.

Verdict:

- Do not use.

### Option D - Unsupported until explicit metadata

Keep Power Herb `charge_context` unavailable until a charge metadata fixture or repo-native field exists.

Pros:

- Safest behavior.
- Avoids hallucinating charge eligibility.
- Preserves raw damage and `ko_context` separation.

Cons:

- Power Herb context remains mostly unavailable.
- Less useful until metadata work is done.

Verdict:

- Safe fallback.
- If no fixture is approved, this should be the behavior.

## Charge Move Eligibility Policy

Recommended eligibility rules:

- Power Herb modeling requires attacker item `power-herb` with `status: user_confirmed`.
- A move is eligible only when explicit charge metadata says it is a charge move and Power Herb eligible.
- A normal damaging move with known metadata should return unavailable `move_not_charge_move` or omit `charge_context`.
- A move with missing charge metadata should return unavailable `move_charge_metadata_missing` or omit `charge_context`.
- Unknown/unconfirmed Power Herb should return unavailable `item_not_user_confirmed` or omit `charge_context`.
- No Power Herb should return unavailable `no_power_herb` or omit `charge_context`.
- Unsupported charge item should use `unsupported_charge_item` if a future item is recognized but not modeled.

Recommended move id normalization:

- normalize by lowercase/hyphenated ids
- do not use localized names as rule keys
- do not parse display names to detect charge moves

Initial eligibility examples for future fixture review:

- likely Power Herb candidates: `solar-beam`, `solar-blade`, `meteor-beam`, `sky-attack`, `skull-bash`
- semi-invulnerable two-turn moves needing careful policy: `fly`, `dig`, `dive`, `bounce`, `phantom-force`, `shadow-force`
- special-case or rule-sensitive moves needing validation: `geomancy`, weather-affected Solar Beam / Solar Blade

The design should avoid over-claiming eligibility until the fixture explicitly classifies these cases.

Weather exceptions remain out of scope. For example, Solar Beam weather behavior is not modeled in v0.76 unless a future Turn Engine or weather context explicitly supports it.

## Safety Policy

Required safety constraints:

- user-confirmed Power Herb only
- known charge metadata only
- raw damage unchanged
- raw `ko_context` unchanged
- `turn_sequence_integrated=false`
- `item_consumption_tracked=false`
- final turn outcome not calculated
- item already consumed state not inferred
- unknown/unconfirmed Power Herb not inferred
- no weather interaction
- no Turn Engine
- no damage formula change
- no KO probability modification

LLM guardrail wording should continue to say:

- Power Herb may allow an eligible charge move to skip the charging turn as limited context.
- Raw damage and KO/OHKO/2HKO estimates do not include charge-turn sequencing.
- Item consumption is not tracked.
- This is not a final turn outcome prediction.

## Proposed v0.76 Path

### Candidate A - v0.76 Power Herb Limited Charge Context Implementation

Condition:

- repo-native charge move metadata clearly exists.

Result of v0.75 validation:

- Not recommended yet. No stable repo-native charge metadata field was found.

### Candidate B - v0.76 Charge Move Metadata Fixture Design

Condition:

- metadata field is absent or insufficient.

Result of v0.75 validation:

- Recommended next step.

Scope:

- design `data/static/charge_moves.json`
- define schema and source notes
- classify candidate moves carefully
- decide which moves are `power_herb_eligible`
- document weather exceptions as not modeled
- add planned tests for fixture validation

### Candidate C - v0.76 Charge Move Static Allowlist Implementation

Condition:

- a minimal allowlist is safe enough to implement immediately.

Result of v0.75 validation:

- Possible but should follow a short fixture design pass. Implementing allowlist directly risks mixing schema design, rule policy, and payload implementation in one step.

T3 recommendation:

- Proceed with `v0.76 - Charge Move Metadata Fixture Design`.
- Keep description parsing forbidden.
- Do not implement `charge_context` until metadata source and eligibility policy are approved.
- Keep item consumption tracking, weather interaction, and turn-sequence-adjusted KO probability excluded.

## Test Plan

Future implementation tests should cover:

- known charge move + user-confirmed Power Herb -> `charge_context.available=true`
- non-charge move + user-confirmed Power Herb -> unavailable `move_not_charge_move`
- missing metadata -> unavailable `move_charge_metadata_missing`
- no Power Herb -> unavailable `no_power_herb`
- unconfirmed Power Herb -> unavailable `item_not_user_confirmed`
- raw damage min/max/rolls unchanged
- `ko_context` unchanged
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

Fixture-design tests should cover:

- fixture schema version exists
- all charge move ids are normalized hyphenated ids
- each entry has `power_herb_eligible`
- each entry has source/notes
- known examples such as Solar Beam and Meteor Beam are represented if approved
- weather-sensitive entries mark weather as not modeled

## Out of Scope

The v0.75 validation design excludes:

- code implementation
- `charge_context` implementation
- fixture implementation
- allowlist implementation
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
