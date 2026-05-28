# v0.41 Repo-Native Minimal Sample Pack Design

Status: design only  
Date: 2026-05-28

## 1. Current State

The opponent stat sample foundation exists, but the fixture is still intentionally small.

Current facts:

- `data/static/pokemon_stat_samples.json` exists.
- `core/pokemon_stat_sample_repository.py` exists.
- The fixture structure is a species-keyed dictionary:

```json
{
  "schema_version": "0.1",
  "format": "pokemon_champions",
  "samples": {
    "garchomp": [
      {
        "sample_id": "garchomp_fast_physical_01",
        "species_id": "garchomp"
      }
    ]
  }
}
```

- The current fixture contains three sentinel samples:
  - `garchomp_fast_physical_01`
  - `charizard_special_attacker_01`
  - `corviknight_bulky_01`
- Every current sample is:
  - `status: "sample_assumed"`
  - `is_user_confirmed: false`
  - `source_type: "manual_estimate"`
  - `confidence: "estimated"`
- `llm/opponent_assumptions.py` emits top-level `opponent_assumptions`.
- `opponent_assumptions.calculation_usage` is `context_only`.
- Sample stats are not connected to `damage_estimate`.
- Sample stats are not connected to `speed_context`.
- `advisor.damage.stats.final_stats` exists and can calculate final stats from base stats, SP distribution, nature, level, and Champions rules.
- `core.champions_item_repository.ChampionsItemRepository` exists and can classify Champions legal items.

## 2. v0.40 Failure Summary

v0.40 validated the T2-1 19-sample candidate package and intentionally stopped before fixture mutation.

Failure causes:

- Candidate schema was not repo-native:
  - candidate used `existing_samples` and `new_samples_v40`
  - candidate entries used `species`
  - current repo fixture uses species-keyed `samples` and sample-level `species_id`
- T2 manual final stats did not match repo calculator output:
  - matched: 0
  - mismatched: 13
  - unverified: 6
- Some species could not be validated because local repo cache/base stats were unavailable:
  - `gholdengo`
  - `amoonguss`
  - `metagross`
- `rotom_wash` conflicted with repo normalization:
  - repository normalization converts `rotom_wash` to `rotom-wash`
  - local cache uses `data/cache/pokemon/rotom-wash.json`
- Candidate `possible_items` contained illegal or unknown items according to the current Champions legal item repository.
- Korean name / ability fields had suspicious or unresolved entries:
  - `garchomp` ability `사기` conflicted with Rough Skin mapping `까칠한피부`
  - `kingambit` Korean name was not confirmed from repo-backed data during validation
  - `amoonguss`, `gholdengo`, and `metagross` could not be confirmed locally

Conclusion:

- The next sample pack must be generated from repo-native data paths, not manually copied from a domain candidate package.

## 3. New Principle

v0.41 establishes a stricter implementation rule:

- T1/T2 may propose archetypes and SP distributions.
- T1/T2 should not hand-calculate final stats for fixture use.
- Final stats must be generated or verified by repo code.
- `advisor.damage.stats.final_stats` is the source of truth for computed sample final stats.
- Species without repo cache/base stats are excluded from the minimal pack.
- `possible_items` must prefer Champions legal items only.
- Items that are unknown or not legal in `ChampionsItemRepository` must not be placed in `possible_items`.
- Unknown or non-legal item ideas can be preserved only in `reviewer_notes` or `risk_notes`.
- Samples remain possible assumptions, never confirmed battle facts.
- Every sample remains:
  - `status: "sample_assumed"`
  - `is_user_confirmed: false`
  - `source_type: "manual_estimate"`
  - `confidence: "estimated"`
  - `calculation_usage: "context_only"`
- `prior_probability` remains `null` unless usage-derived data exists.
- `coverage_probability` remains `null` unless usage-derived coverage exists.

Hard rule:

```text
SP distribution may be manually proposed.
Final stats must be repo-calculated.
```

## 4. Repo-Native Schema Direction

The minimal sample pack should keep the existing fixture structure.

Recommended shape:

```json
{
  "schema_version": "0.1",
  "format": "pokemon_champions",
  "samples": {
    "garchomp": [
      {
        "sample_id": "garchomp_fast_physical_repo_v42",
        "species_id": "garchomp",
        "label_en": "Fast physical repo-calculated sample",
        "label_ko": "고속 물리형 repo 계산 샘플",
        "source": "manual_sample",
        "source_type": "manual_estimate",
        "confidence": "estimated",
        "status": "sample_assumed",
        "is_user_confirmed": false,
        "stats": {
          "hp": 183,
          "atk": 169,
          "def": 115,
          "spa": 90,
          "spd": 105,
          "spe": 126
        },
        "assumptions": {
          "sp_distribution": {
            "hp": 0,
            "atk": 32,
            "def": 0,
            "spa": 0,
            "spd": 2,
            "spe": 32
          },
          "nature": {
            "plus": "atk",
            "minus": "spa"
          },
          "item": null,
          "iv_assumption": "31_all",
          "level": 50,
          "stats_truth_source": "repo_calculator_from_sp_distribution",
          "stats_calculator": "advisor.damage.stats.final_stats",
          "stats_verified_at": null
        },
        "possible_items": [
          "choice-scarf"
        ],
        "possible_items_review_status": "legal_only",
        "calculation_usage": "context_only",
        "prior_probability": null,
        "coverage_probability": null,
        "limitations": [
          "Estimated sample, not user-confirmed.",
          "Do not treat as exact opponent stats.",
          "Do not use as final battle truth.",
          "This sample is context-only unless explicitly integrated in a future version."
        ]
      }
    ]
  }
}
```

Schema direction:

- Keep species-keyed dictionary.
- Use `species_id`, not mixed `species` / `species_id`.
- Species keys must equal `normalize_species_id(species_id)`.
- Form species must use repo/cache slugs, such as `rotom-wash`.
- Do not introduce a flat `samples[]` array in v0.42.
- Do not perform broad schema migration in v0.42.
- Additive fields may be added only if repository validation and tests are updated at the same time.

## 5. Stats Generation Policy

SP distribution is the human-editable input.

Final stats are generated by repo code:

- calculator: `advisor.damage.stats.final_stats`
- rule set: `champions`
- level: `50`
- IV assumption: `31_all`
- per-stat SP cap: `0..32`
- total SP cap: `<= 66`

Recommended sample fields:

- `stats_truth_source: "repo_calculator_from_sp_distribution"`
- `stats_calculator: "advisor.damage.stats.final_stats"`
- `stats_verified_at: null` or generation date
- `assumptions.nature.plus`
- `assumptions.nature.minus`
- `assumptions.iv_assumption: "31_all"`
- `assumptions.level: 50`

Policy:

- T2 manual final stats must not be copied into the fixture.
- T2 may provide:
  - species id
  - archetype
  - SP distribution
  - nature assumption
  - role notes
- T3 computes final stats from repo cache/base stats.
- If repo base stats are missing, do not create the sample.
- If repo calculator raises, do not create the sample.
- Tests must recompute final stats and compare them to fixture `stats`.

## 6. Species Eligibility Policy

A species is eligible for the v0.42 minimal pack only if all required local validation inputs exist.

Required:

- repo cache/base stats exist
- species normalization is clear
- `advisor.damage.stats.final_stats` can compute final stats
- legal item candidates can be checked against `ChampionsItemRepository`
- Korean name / ability can be verified or omitted without making unsafe claims

Likely eligible from current repo inspection:

- `garchomp`
- `charizard`
- `corviknight`
- `tyranitar`
- `archaludon`
- `dragonite`
- `rotom-wash`
- `kingambit`

Notes:

- `kingambit` has local cache/base stats, but Korean name confirmation still needs care.
- `rotom-wash` should use the normalized cache/form slug `rotom-wash`, not `rotom_wash`.

Deferred:

- `gholdengo`
- `amoonguss`
- `metagross`

Reason:

- local cache/base stats were not available during v0.40 validation.
- final stats cannot be repo-calculated without base stats.

T3 recommendation:

- v0.42 should use only 5 to 7 species from the likely eligible group.
- Defer `kingambit` unless Korean name policy is clarified or Korean name is omitted.
- Do not include deferred species until cache/base stats exist.

## 7. Item Eligibility Policy

`possible_items` should be conservative.

Default rule:

- Include only items where `ChampionsItemRepository.classify_item(item_id)["legal"] is True`.

Exclude from `possible_items`:

- damage-supported but non-legal items
- unknown items
- pseudo-items
- banned marker items

From v0.40 validation, exclude in v0.42 possible items:

- illegal / not normal Champions legal:
  - `choice-specs`
  - `choice-band`
  - `life-orb`
- unknown in current repository:
  - `heavy-duty-boots`
  - `loaded-dice`
  - `weakness-policy`
  - `assault-vest`
  - `throat-spray`
  - `power-herb`
  - `covert-cloak`
  - `air-balloon`
  - `black-sludge`
  - `rocky-helmet`

Allowed review status candidates:

- `legal_checked`
- `legal_only`
- `excluded_unknown_items`
- `needs_future_source_update`

Recommended behavior:

- Put legal items in `possible_items`.
- Put excluded non-legal or unknown item ideas in `reviewer_notes`, for example:
  - "Excluded heavy-duty-boots because it is unknown in the current Champions item repository."
  - "Excluded life-orb because it is damage-supported but not normal Champions legal."
- Do not silently delete items without recording the reason during implementation.

## 8. Minimal Pack Scope

v0.42 should be small by design.

Recommended scope:

- 5 to 7 species
- 1 sample per species
- 5 to 7 samples total
- only repo-calculable species
- only legal checked items

Candidate species:

- `garchomp`
- `charizard`
- `corviknight`
- `tyranitar`
- `archaludon`
- `dragonite`
- `rotom-wash`

SP distribution shape:

- simple `32/32/2`
- or simple `32/28/6`
- no complex optimized spreads
- no manual final stat claims

Purpose:

- Validate the repo-native generator/test path.
- Exercise `opponent_assumptions` Top-K behavior later.
- Avoid pretending to be a complete metagame database.

## 9. Archetype Policy

v0.42 samples should be validation archetypes, not meta truth.

Recommended archetypes:

- `garchomp`: `fast_physical`
- `charizard`: `special_attacker`
- `corviknight`: `defensive_pivot`
- `tyranitar`: `bulky_physical`
- `archaludon`: `special_tank`
- `dragonite`: `physical_setup`
- `rotom-wash`: `defensive_pivot`

Rules:

- Keep `source_type: "manual_estimate"`.
- Keep `confidence: "estimated"`.
- Keep `is_user_confirmed: false`.
- Keep role labels simple.
- Do not imply a metagame-optimal spread.
- Include `possible_moves` only if they are repo-validated, or omit them / leave notes.
- If possible move validation is out of scope, keep move ideas in `reviewer_notes`.

## 10. Builder / Test Direction

v0.42 implementation should be generator-like even if no separate script is committed.

Implementation direction:

- T2/T1 provides SP distribution and archetype intent.
- T3 loads repo base stats from local cache/repository.
- T3 computes final stats using `advisor.damage.stats.final_stats`.
- T3 writes computed stats into the fixture.
- T3 records calculator provenance in sample assumptions.

Test direction:

- fixture loads successfully
- species keys are normalized
- `species_id` equals the species-keyed dictionary key
- `rotom-wash` normalization is covered
- SP distribution has all six stat keys
- each SP value is within `0..32`
- total SP is `<= 66`
- fixture stats recompute exactly from:
  - repo base stats
  - SP distribution
  - nature assumption
  - level
  - `advisor.damage.stats.final_stats`
- `possible_items` are list[str]
- every `possible_items` entry is legal in `ChampionsItemRepository`
- unknown/non-legal items are excluded
- `sample_assumed` remains true for all samples
- `is_user_confirmed` remains false
- `calculation_usage` remains `context_only`
- `prior_probability` remains null
- `coverage_probability` remains null
- `opponent_assumptions` default Top-K remains `3`
- sample stats do not modify `damage_estimate`
- sample stats do not modify `speed_context`

## 11. LLM / Payload Guardrail

Existing guardrails remain unchanged:

- Samples are context-only.
- Sample stats are not direct damage inputs.
- Sample stats are not direct Speed inputs.
- Samples are possible profiles, not confirmed opponent sets.
- Legal item-only `possible_items` still do not confirm the live opponent item.
- `prior_probability: null` does not mean `0%`.
- Top-K omitted archetypes are not impossible.
- Do not claim final turn order, KO, OHKO, 2HKO, or survival from samples.

Recommended prompt/contract wording remains:

- "Possible samples are assumptions, not confirmed opponent stats."
- "The sample is context only and was not used directly for damage or speed calculation."
- "Legal possible items are candidate context only, not confirmed held items."

## 12. v0.42 Candidate

Recommended:

`v0.42 - Repo-Native Minimal Sample Pack Implementation`

Include:

- 5 to 7 species
- 1 sample per species
- species-keyed dictionary preserved
- repo calculator generated stats
- Champions legal item only `possible_items`
- validation tests that recompute fixture stats
- `opponent_assumptions` regression tests
- no UI
- no damage/speed integration

Alternative:

`v0.42 - Stat Sample Generator Helper Design`

Use this if:

- T1/T2 want a reusable generation helper designed before fixture edits.
- Korean name / ability policy is not settled.
- legal item candidates for the minimal species are not ready.

T3 recommendation:

- Proceed with `v0.42 - Repo-Native Minimal Sample Pack Implementation` if the 5 to 7 species list and legal-item-only policy are approved.
- Keep the pack intentionally boring: one repo-calculated sample per species.

## 13. Out of Scope

Explicitly excluded from v0.41:

- fixture changes
- sample additions
- code implementation
- repository implementation
- tests changes
- UI changes
- scraping or build script creation
- damage integration
- Speed integration
- calculation mode implementation
- Bayesian update implementation
- KO/OHKO/2HKO implementation
- Turn Engine implementation
- item effect additions
- logs, `.env`, secrets, API keys, or handoff capsule commits
