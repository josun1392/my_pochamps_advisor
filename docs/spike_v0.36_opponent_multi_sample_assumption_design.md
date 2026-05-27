# v0.36 Opponent Multi-Sample Assumption Design

Status: design only  
Date: 2026-05-27

## 1. Current State

The project now has a minimal opponent stat sample foundation, but those samples are not connected to live advice.

Relevant current state:

- `data/static/pokemon_stat_samples.json` exists as a sentinel fixture.
- `core/pokemon_stat_sample_repository.py` loads, validates, normalizes, and looks up samples.
- Current sentinel species are `garchomp`, `charizard`, and `corviknight`.
- Every sample is `status: "sample_assumed"`.
- Every sample has `is_user_confirmed: false`.
- Every sample has `confidence: "estimated"`.
- Source metadata exists, including `source_type`, `source_name`, `source_url`, `regulation`, `is_official`, and `confidence_reason`.
- Allowed `source_type` values are defined and validated.
- A source tier policy exists in `docs/PROGRESS.md`.
- There is no UI selector for samples.
- There is no automatic sample application.
- Sample stats do not feed `damage_estimate`.
- Sample stats do not feed `speed_context`.
- Current `damage_estimate` may use user-confirmed final stats when `stat_profiles` has all six final stats.
- Current `speed_context` is available only when both active Pokemon have user-confirmed final Speed.

The key current boundary is still correct:

- `user_confirmed_final_stats` are a higher-confidence explicit input.
- `sample_assumed` stats are estimated references.
- `default_assumption` remains a rough fallback.

## 2. Problem Definition

The v0.34 direction considered an opponent sample selector, but a single selected opponent sample can be too strong for real battle uncertainty.

In practice, Team Preview and the opponent's six Pokemon usually do not reveal:

- held item
- full moveset
- SP distribution
- nature
- ability choice
- role
- exact final stats

If the UI asks T1 to pick one opponent sample, the payload may accidentally make a guess look like a fact. Even if the UI says "sample", a single selected profile can bias the LLM toward wording such as "the opponent is this set" or "the opponent has this Speed."

The better model is:

```text
possible sample != confirmed opponent set
```

The advisor should reason over multiple plausible opponent profiles and preserve uncertainty until observations or direct user input narrow the space.

Design goals:

- Represent several possible opponent profiles, not one exact sample.
- Keep all possible samples non-user-confirmed.
- Let future payloads include priors and evidence basis without treating them as final probabilities.
- Preserve user-confirmed information as higher priority than any sample.
- Defer calculation integration until the uncertainty model is explicit.

## 3. Information State Model

### A. `not_confirmed`

Meaning:

- T1 knows only broad information, such as opponent species from Team Preview.
- The app may keep several `possible_samples`.
- No opponent set, item, stats, or role is confirmed.
- `user_confirmed_fields` is empty.

Payload direction:

```json
{
  "known_status": "not_confirmed",
  "is_user_confirmed": false,
  "user_confirmed_fields": {},
  "possible_samples": []
}
```

LLM behavior:

- Discuss samples only as possible profiles.
- Avoid saying the opponent has a specific item, Speed, spread, or role.
- Mention uncertainty clearly.

### B. `partially_confirmed`

Meaning:

- Some information has been observed or directly entered.
- Examples:
  - Life Orb recoil was observed.
  - Leftovers recovery was observed.
  - The opponent used a specific move.
  - An ability interaction revealed the ability.
- `user_confirmed_fields` records the confirmed facts.
- `possible_samples` can be filtered or down-weighted if they conflict with confirmed fields.

Payload direction:

```json
{
  "known_status": "partially_confirmed",
  "is_user_confirmed": false,
  "user_confirmed_fields": {
    "item": "life-orb",
    "ability": "rough-skin"
  },
  "possible_samples": []
}
```

LLM behavior:

- Treat confirmed fields as stronger than sample priors.
- Do not rely on samples that contradict confirmed fields.
- Explain which facts are confirmed and which parts remain assumed.

### C. `user_confirmed`

Meaning:

- T1 has directly confirmed the relevant opponent set, item, stats, or other fields.
- This state should disable multi-sample reasoning for the confirmed fields.
- Multi-sample data may remain as background context only if it is useful and clearly secondary.

Payload direction:

```json
{
  "known_status": "user_confirmed",
  "is_user_confirmed": true,
  "user_confirmed_fields": {
    "final_stats": {
      "hp": 183,
      "atk": 150,
      "def": 115,
      "spa": 90,
      "spd": 105,
      "spe": 154
    }
  },
  "possible_samples": []
}
```

LLM behavior:

- Use user-confirmed fields as the active source.
- Do not let sample priors override confirmed fields.
- Continue to avoid final turn order, KO, OHKO, or 2HKO claims unless future explicit systems provide them.

## 4. Schema Proposal

Two top-level locations are plausible.

### Option A - `opponent_assumptions`

Pros:

- Clear that this is assumption metadata.
- Keeps possible samples separate from confirmed `stat_profiles`.
- Can later hold observation history and update policy.

Cons:

- Adds a new top-level section.
- Damage and Speed helpers would need an explicit bridge later.

### Option B - `possible_opponent_profiles`

Pros:

- Directly names the contents.
- Simple for LLM consumption.

Cons:

- Less room for known status, user overrides, samples meta, and update policy.
- May become too narrow once observations and team-level context are added.

T3 recommendation:

- Use `opponent_assumptions` as the future top-level section.
- Put active opponent data under `opponent_assumptions.opponent_active`.
- Keep `stat_profiles.opponent_active` reserved for the current stat source used by deterministic calculations.
- Do not make possible samples authoritative stat profiles.

Recommended design shape:

```json
{
  "opponent_assumptions": {
    "mode": "multi_sample_assumption_v0.36_design",
    "opponent_active": {
      "species_id": "garchomp",
      "known_status": "not_confirmed",
      "is_user_confirmed": false,
      "user_confirmed_fields": {},
      "possible_samples": [
        {
          "sample_id": "garchomp_choice_scarf_01",
          "species_id": "garchomp",
          "label_ko": "스카프 고속 물리형",
          "label_en": "Choice Scarf fast physical",
          "source": "sample_assumed",
          "source_type": "usage_based_estimate",
          "confidence": "plausible",
          "prior_probability": 0.45,
          "evidence_basis": "Manual estimate based on common PoChamps archetypes.",
          "is_user_confirmed": false,
          "possible_item": "choice-scarf",
          "possible_stats": {
            "spe": 134
          },
          "notes": [
            "This is a possible opponent profile, not confirmed.",
            "Do not treat this as exact opponent stats."
          ],
          "limitations": [
            "Possible sample is not a confirmed opponent set.",
            "Prior probability is an estimate, not a confirmed probability.",
            "Do not use as final battle truth."
          ]
        }
      ],
      "samples_meta": {
        "total_known_archetypes": 7,
        "included_top_k": 3,
        "coverage_probability": 0.85,
        "omitted_archetypes_note": "Lower-prior archetypes are omitted from the active payload."
      },
      "observation_history": [],
      "update_policy": {
        "version": "0.36.0",
        "mode": "static",
        "note": "v0.36 only defines priors. Observation-based updates are deferred."
      }
    }
  }
}
```

## 5. Required Fields

Each `possible_samples` entry should include at least:

- `sample_id`
- `species_id`
- `label_en`
- `label_ko`
- `source`
- `source_type`
- `confidence`
- `prior_probability`
- `evidence_basis`
- `is_user_confirmed`
- `possible_item`
- `possible_stats`
- `notes`
- `limitations`

Recommended validation rules:

- `sample_id` is non-empty and stable.
- `species_id` matches the active opponent species.
- `source` should be `sample_assumed` or another explicit non-confirmed source.
- `source_type` must come from the allowed source type set.
- `is_user_confirmed` must be `false`.
- `prior_probability` is either `null` or a number from `0.0` to `1.0`.
- `evidence_basis` is required whenever `prior_probability` is not `null`.
- `possible_stats` may be partial; it should not masquerade as all six confirmed final stats unless the profile explicitly contains all six and still marks them assumed.
- `limitations` must say the sample is not confirmed.

## 6. Prior Probability / Evidence Basis

Qualitative confidence alone can make LLM interpretation drift. For example, "plausible" does not tell the model whether a sample is the main risk or a rare edge case.

Future profiles should support:

- `prior_probability`: numeric estimated prior from `0.0` to `1.0`, or `null` when no responsible estimate exists.
- `evidence_basis`: short explanation of where the prior came from.
- `confidence`: qualitative label such as `plausible`, `estimated`, or `low_confidence`.

Examples:

```json
{
  "prior_probability": 0.45,
  "evidence_basis": "manual estimate based on common PoChamps archetypes",
  "confidence": "plausible"
}
```

```json
{
  "prior_probability": null,
  "evidence_basis": "No usage-backed prior available yet.",
  "confidence": "estimated"
}
```

Guardrail:

- The LLM must not describe a prior as the real probability of the opponent set.
- A `0.45` prior means "current model weight", not "45% confirmed chance."
- If the source is manual, the LLM should say it is a manual estimate.

## 7. Top-K / Coverage Metadata

Putting every possible sample into the payload can increase token cost and make advice noisier. The payload should include only the most relevant candidates by default and tell the LLM what was omitted.

Recommended metadata:

```json
{
  "samples_meta": {
    "total_known_archetypes": 7,
    "included_top_k": 3,
    "coverage_probability": 0.85,
    "omitted_archetypes_note": "Some rare archetypes are not included."
  }
}
```

Field semantics:

- `total_known_archetypes`: count of known sample archetypes for the species.
- `included_top_k`: number of samples included in this payload.
- `coverage_probability`: estimated mass covered by included samples, or `null` when no responsible estimate exists.
- `omitted_archetypes_note`: natural-language warning about excluded candidates.

Guardrail:

- Top-K omission does not mean omitted archetypes are impossible.
- The LLM should mention that the payload contains only major candidates when that matters.
- `coverage_probability` must be treated as an estimate, not a battle fact.

## 8. Update Hook / Future Bayesian Update

v0.36 must not implement dynamic updates, but the schema should leave space for future observation-based changes.

Recommended hook:

```json
{
  "observation_history": [],
  "update_policy": {
    "version": "0.36.0",
    "mode": "static",
    "note": "v0.36 only defines priors. Observation-based updates are deferred."
  }
}
```

Future update examples:

- Opponent moved first unexpectedly:
  - increase prior for Choice Scarf or fast samples
  - decrease prior for slow bulky samples
- Opponent shows Leftovers recovery:
  - increase prior for Leftovers samples
  - exclude samples with incompatible confirmed item assumptions
- Opponent shows Life Orb recoil:
  - treat Life Orb as a strong confirmed-field candidate
  - filter non-Life Orb samples or mark them conflicting
- Opponent uses a move:
  - increase samples containing that move
  - reduce samples whose role or known moves conflict

v0.36 boundary:

- No Bayesian update implementation.
- No observation engine.
- No Turn Engine.
- No automatic state mutation.

## 9. User Override Path

Multi-sample assumptions must not replace direct user input.

Recommended policy:

- `user_confirmed_fields` always wins over sample priors.
- If a confirmed item conflicts with a sample's `possible_item`, the sample should be excluded or marked `conflicts_with_confirmed_fields`.
- If final stats are user-confirmed, sample stats should not feed the active stat model.
- In full `user_confirmed` state, `possible_samples` can be empty or moved to background context.

Example:

```json
{
  "known_status": "partially_confirmed",
  "user_confirmed_fields": {
    "item": "life-orb",
    "ability": "rough-skin"
  },
  "possible_samples": [
    {
      "sample_id": "garchomp_life_orb_physical_01",
      "possible_item": "life-orb",
      "conflict_status": "compatible"
    },
    {
      "sample_id": "garchomp_choice_scarf_01",
      "possible_item": "choice-scarf",
      "conflict_status": "conflicts_with_confirmed_fields",
      "conflict_reasons": [
        "Confirmed item life-orb conflicts with possible_item choice-scarf."
      ]
    }
  ]
}
```

Recommended helper behavior:

- Keep conflicting samples out of the default Top-K payload.
- Optionally retain a small audit list of excluded samples for debugging.
- Never let a conflicting sample drive advice.

## 10. Calculation Mode Design

v0.36 defines future calculation modes only. It must not connect these modes to damage or Speed.

### Mode A - `worst_case`

Meaning:

- Use the most dangerous plausible sample for the question being asked.
- Prioritizes safety.

Example use:

- "If the opponent is the fastest plausible Garchomp, can my Pokemon afford this line?"

Risk:

- Can be overly conservative if the worst case is rare.

### Mode B - `most_likely`

Meaning:

- Use the highest-prior sample.
- Good for ordinary advice when the top prior is credible.

Risk:

- Can miss lower-prior dangerous cases.

### Mode C - `expected_value`

Meaning:

- Combine sample outcomes by prior weights.
- Useful for probability-weighted advice.

Risk:

- Requires responsible priors.
- Can hide catastrophic tails.

### Mode D - `range`

Meaning:

- Report min-to-max across included possible samples.

Example:

- "Across included samples, Speed ranges from 102 to 154."

Risk:

- Ranges can look precise even when samples are incomplete.

Recommended v0.36 stance:

- Define the enum only.
- Do not apply it to `damage_estimate`.
- Do not apply it to `speed_context`.
- Do not calculate KO, OHKO, 2HKO, survival, or final turn order.

## 11. Payload / LLM Guardrails

Bad wording:

- "상대는 스카프 한카리아스입니다."
- "상대 스피드는 154입니다."
- "이 샘플이 실제 상대 세트입니다."
- "100% 확신하고 움직이세요."
- "샘플 기준으로 확정 선공입니다."

Good wording:

- "상대가 스카프 한카리아스일 가능성이 있습니다."
- "현재 샘플 후보 중 스카프형이 높은 위험 후보입니다."
- "상대 스피드는 샘플별로 범위가 달라질 수 있습니다."
- "이 정보는 가능성 기반이며, 실제 상대 세트는 확인되지 않았습니다."
- "현재 정보로는 불확실성이 크므로 보수적인 선택도 고려할 수 있습니다."

Required guardrails:

- Do not describe a possible sample as a confirmed set.
- Do not overstate `prior_probability` as a real confirmed probability.
- Do not describe `sample_assumed` stats as user-confirmed stats.
- Do not make final damage, Speed, turn order, KO, OHKO, 2HKO, or survival claims from sample data.
- Do not trust samples that conflict with `user_confirmed_fields`.
- Do not rule out archetypes omitted by Top-K selection.
- Do not infer item, ability, nature, SP distribution, or moves from a sample unless explicitly present, and still label them as possible.
- Always distinguish "confirmed", "observed", "possible", and "default assumption" language.

Suggested prompt guardrail language for a future payload:

```text
If opponent_assumptions.possible_samples is present, treat each sample as a possible profile only.
Do not call any possible sample the opponent's actual set.
Use prior_probability only as an estimated model prior, not as confirmed probability.
User-confirmed fields override sample priors.
Do not claim final Speed order, KO, survival, or exact damage from possible samples.
```

## 12. UI Touch Point Direction

v0.36 should not add UI.

Future UI direction:

- Avoid a large new battle-screen UI surface.
- Avoid forcing T1 to select exactly one sample.
- The existing opponent Stats dialog could later expose "View possible samples" or "Sample distribution".
- Samples should be displayed as estimated candidates, not chosen truth.
- The UI should visually separate:
  - user-confirmed final stats
  - observed fields
  - possible sample profiles
  - default assumptions
- A single-sample selector should not be the default mental model.

T3 recommendation:

- Keep v0.36 design-only.
- Consider v0.37 payload design or repository extension before UI.
- Defer any sample selector UI until v0.38 or later, and prefer "possible samples" over "select this set."

## 13. Repository / Data Direction

The existing `PokemonStatSampleRepository` can remain the read-only fixture loader for v0.35 data. Multi-sample assumptions likely need a separate helper so the repository does not become responsible for battle-state policy.

Potential fixture additions:

- `prior_probability`
- `evidence_basis`
- `archetype_tags`
- `possible_item`
- `possible_moves`
- `possible_ability`
- `calculation_relevant_stats`
- `sample_role`

Potential helper:

`core/opponent_assumption_builder.py`

Candidate functions:

```python
build_possible_samples_for_species(species_id: str, top_k: int = 3) -> dict
filter_samples_by_confirmed_fields(samples: list[dict], user_confirmed_fields: dict) -> list[dict]
normalize_sample_priors(samples: list[dict]) -> list[dict]
```

Recommended responsibilities:

- Repository:
  - load sample data
  - validate sample schema
  - return samples by species or sample id
- Assumption builder:
  - construct `opponent_assumptions`
  - apply Top-K selection
  - attach `samples_meta`
  - apply user-confirmed-field filters
  - normalize or preserve priors
  - keep mode static until update logic exists

Design choice:

- Keep fixture data source-oriented.
- Keep payload selection policy in a builder.
- Keep deterministic calculations separate from possible-sample context until explicitly approved.

## 14. Tests Plan

Future implementation tests:

- possible sample payload generation for a species
- `possible_samples[*].is_user_confirmed` remains `false`
- `prior_probability` accepts `null` or `0.0` to `1.0`
- invalid prior values are rejected
- `evidence_basis` is required when prior is present
- `included_top_k` limits payload samples
- `samples_meta.coverage_probability` exists or is explicitly `null`
- omitted archetype note is present
- `known_status` enum validation
- `user_confirmed_fields` override behavior
- confirmed item filters conflicting samples
- conflicting samples are not used in default Top-K
- `observation_history` exists but remains empty in static mode
- `update_policy.mode` is `static`
- calculation mode enum validation
- LLM guardrail text includes possible-sample limitations
- no damage integration by default
- no speed integration by default
- existing sample repository regression remains
- existing final stats input regression remains
- existing speed_context regression remains

## 15. v0.37 Candidate

Recommended next candidate:

`v0.37 - Opponent Possible Sample Payload Design`

Why:

- v0.36 is a conceptual shift.
- The next safest step is to define the exact payload contract before implementing builder code.
- It can settle field names, guardrails, Top-K behavior, and prompt wording without touching calculations.

Include:

- `opponent_assumptions` contract draft.
- possible sample required fields.
- `samples_meta` contract.
- `known_status` and `user_confirmed_fields` contract.
- static `update_policy` contract.
- LLM guardrail wording.
- decision on whether priors live in fixture data or builder policy.

Alternative:

`v0.37 - Opponent Multi-Sample Repository Extension`

Include:

- Add `prior_probability`, `evidence_basis`, and `archetype_tags` to fixture samples.
- Add schema validation for priors and archetype fields.
- Defer payload builder to v0.38.

T3 recommendation:

- Prefer `v0.37 - Opponent Possible Sample Payload Design`.
- Decide first whether priors belong in fixture data or a builder layer.
- Then implement repository extension or builder with less churn.

## 16. Out of Scope

Explicitly excluded from v0.36:

- code implementation
- data fixture changes
- repository implementation
- UI implementation
- automatic sample selection implementation
- damage integration
- speed integration
- Bayesian update implementation
- calculation mode implementation
- Turn Engine implementation
- KO/OHKO/2HKO implementation
- item effect additions
- damage/probability engine changes
- logs, `.env`, secrets, API keys, or handoff capsule commits
