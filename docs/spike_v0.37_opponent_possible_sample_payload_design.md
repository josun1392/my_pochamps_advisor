# v0.37 Opponent Possible Sample Payload Design

Status: design only  
Date: 2026-05-27

## 1. Current State

The project has the data foundation for opponent stat samples, but no payload integration yet.

Current facts:

- `data/static/pokemon_stat_samples.json` exists.
- `core/pokemon_stat_sample_repository.py` exists.
- The repository validates schema, source metadata, normalized species ids, sample ids, stats, SP distribution, and limitations.
- Sentinel samples exist for `garchomp`, `charizard`, and `corviknight`.
- Every sample remains:
  - `status: "sample_assumed"`
  - `is_user_confirmed: false`
  - `confidence: "estimated"`
  - `source_type: "manual_estimate"`
  - `is_official: false`
- v0.35.1 added source metadata and source tier policy.
- v0.36 designed the multi-sample assumption model.
- There is still no `opponent_assumptions` payload section.
- There is no sample UI.
- There is no automatic sample application.
- Sample data is not connected to `damage_estimate`.
- Sample data is not connected to `speed_context`.
- User-confirmed final stats remain the higher-confidence stat source.

The v0.37 design target is the payload contract only.

## 2. Problem Definition

Possible opponent samples can improve advice because they give the LLM useful risk context. For example, a Garchomp with a fast physical sample is tactically different from a bulky sample.

However, putting samples into the payload creates a new risk:

- the LLM may treat a possible sample as the confirmed opponent set
- the LLM may turn sample Speed into exact Speed
- the LLM may turn sample item or move metadata into confirmed information
- the LLM may infer damage, Speed order, survival, KO, OHKO, or 2HKO from sample context
- the LLM may treat `prior_probability: null` as `0%`

Therefore the payload must make the boundary explicit:

```text
possible sample = risk/context signal
possible sample != confirmed calculation input
possible sample != confirmed opponent set
```

v0.37 should design a schema that is useful enough for future prompt context while still making overclaiming hard.

## 3. Top-Level Payload Section

### Option A - `opponent_assumptions`

Pros:

- Clearly identifies the section as assumption metadata.
- Separates uncertain sample context from deterministic calculation fields.
- Can hold availability, known status, user overrides, Top-K metadata, and update policy.
- Matches the v0.36 direction.

Cons:

- Adds a new top-level payload section.
- Requires new contract and prompt guardrails.

### Option B - `possible_opponent_profiles`

Pros:

- Direct and easy to read.
- Names the main content.

Cons:

- Less room for availability state, update policy, and calculation usage.
- Can look like a list of profiles the model should choose from as truth.
- Does not communicate the broader information-state model as well.

### Option C - `battle_assumptions.opponent_samples`

Pros:

- Could group future assumptions under one parent.
- Might later include field, weather, or team-level assumptions.

Cons:

- More nesting.
- Less discoverable for prompt logic.
- May blur opponent sample assumptions with deterministic battle state.

T3 recommendation:

- Use top-level `opponent_assumptions`.
- Treat it as context-only unless a future version explicitly changes `calculation_usage`.
- Keep it separate from:
  - `stat_profiles`
  - `damage_estimate`
  - `speed_context`
  - `opponent_moves.known_moves`

Reason:

- Possible samples are an incomplete-information model, not a stat model currently used by deterministic calculations.

## 4. Proposed Payload Schema

Recommended v0.37 candidate shape:

```json
{
  "opponent_assumptions": {
    "mode": "multi_sample_assumption_v0.37_candidate",
    "available": true,
    "scope": "opponent_active",
    "is_confirmed_information": false,
    "calculation_usage": "context_only",
    "opponent_active": {
      "species_id": "garchomp",
      "known_status": "not_confirmed",
      "is_user_confirmed": false,
      "user_confirmed_fields": {},
      "possible_samples": [
        {
          "sample_id": "garchomp_fast_physical_01",
          "species_id": "garchomp",
          "label_en": "Fast physical sample",
          "label_ko": "고속 물리형 샘플",
          "source": "sample_assumed",
          "source_type": "manual_estimate",
          "confidence": "plausible",
          "prior_probability": null,
          "prior_probability_type": "not_available",
          "evidence_basis": "Manual sentinel sample; not usage-derived.",
          "is_user_confirmed": false,
          "possible_item": null,
          "possible_stats": {
            "spe": 154
          },
          "possible_moves": [],
          "limitations": [
            "This is a possible opponent profile, not confirmed.",
            "Do not treat this as exact opponent stats."
          ]
        }
      ],
      "samples_meta": {
        "total_known_archetypes": 1,
        "included_top_k": 1,
        "default_top_k": 3,
        "coverage_probability": null,
        "coverage_probability_type": "not_available",
        "omitted_archetypes_note": "Only sentinel samples are available in v0.37 candidate."
      },
      "observation_history": [],
      "update_policy": {
        "version": "0.37.0",
        "mode": "static",
        "note": "No observation-based updates are implemented."
      }
    },
    "limitations": [
      "Opponent samples are assumptions, not confirmed sets.",
      "Samples are not used directly for damage or speed calculations in this version.",
      "User-confirmed fields override possible sample assumptions."
    ]
  }
}
```

Key semantics:

- `available` says whether sample context exists for the active opponent species.
- `is_confirmed_information` is always `false` for this section.
- `calculation_usage` is `context_only` in v0.37.
- `known_status` mirrors the v0.36 information-state model.
- `possible_samples` are possible profiles only.
- `samples_meta` explains Top-K and coverage limitations.
- `update_policy.mode` remains `static`.

## 5. Availability Behavior

Recommended behavior:

- If opponent active species is present and repository has samples:
  - `available: true`
  - include up to `top_k` possible samples
- If opponent active species is present but repository has no samples:
  - `available: false`
  - `reason: "no_samples_for_species"`
- If opponent active Pokemon is missing:
  - `available: false`
  - `reason: "opponent_active_missing"`
- If repository loading fails:
  - `available: false`
  - `reason: "repository_unavailable"`

Unavailable shape:

```json
{
  "opponent_assumptions": {
    "mode": "multi_sample_assumption_v0.37_candidate",
    "available": false,
    "scope": "opponent_active",
    "reason": "no_samples_for_species",
    "is_confirmed_information": false,
    "calculation_usage": "context_only",
    "opponent_active": {
      "species_id": "missingno",
      "known_status": "not_confirmed",
      "is_user_confirmed": false,
      "user_confirmed_fields": {},
      "possible_samples": [],
      "samples_meta": {
        "total_known_archetypes": 0,
        "included_top_k": 0,
        "default_top_k": 3,
        "coverage_probability": null,
        "coverage_probability_type": "not_available",
        "omitted_archetypes_note": "No sample archetypes are available for this species."
      },
      "observation_history": [],
      "update_policy": {
        "version": "0.37.0",
        "mode": "static",
        "note": "No observation-based updates are implemented."
      }
    },
    "limitations": [
      "No opponent sample should be invented when available is false.",
      "Opponent samples are assumptions, not confirmed sets."
    ]
  }
}
```

Guardrail:

- If `available` is `false`, the LLM must not invent samples.
- It may say no sample context is available for this species.
- It must fall back to the rest of the payload, such as known moves, item profiles, stat profiles, and damage estimates.

## 6. Calculation Usage

v0.37 candidate policy:

```json
{
  "calculation_usage": "context_only"
}
```

Meaning:

- possible samples are not damage inputs
- possible samples are not Speed inputs
- possible samples are not KO inputs
- possible samples are not survival inputs
- possible samples are not final turn order inputs

Explicit non-goals:

- Do not connect samples to `damage_estimate`.
- Do not connect samples to `speed_context`.
- Do not produce OHKO/2HKO/KO chance from samples.
- Do not produce survival claims from samples.
- Do not produce final turn order from samples.

Future versions may define:

- `calculation_usage: "range_context"`
- `calculation_usage: "most_likely_sample"`
- `calculation_usage: "worst_case_sample"`

Those future values require separate implementation, tests, and guardrails.

## 7. Prior Probability Policy

The current sentinel fixture has no usage-derived prior data. Therefore v0.37 should allow:

```json
{
  "prior_probability": null,
  "prior_probability_type": "not_available"
}
```

Allowed `prior_probability_type` candidates:

- `usage_derived`
- `manual_estimate`
- `heuristic`
- `not_available`

Rules:

- `prior_probability` may be `null`.
- `null` does not mean `0%`.
- If numeric, `prior_probability` must be from `0.0` to `1.0`.
- Numeric priors may be unnormalized because the payload may contain only Top-K samples.
- If a prior is numeric, `evidence_basis` is required.
- If a prior is manual or heuristic, the LLM must label it as estimated.

Examples:

```json
{
  "prior_probability": null,
  "prior_probability_type": "not_available",
  "evidence_basis": "Manual sentinel sample; not usage-derived."
}
```

```json
{
  "prior_probability": 0.45,
  "prior_probability_type": "manual_estimate",
  "evidence_basis": "Manual estimate based on common PoChamps archetypes."
}
```

LLM guardrail:

- Do not say a `null` prior means the sample is impossible.
- Do not say a numeric prior is the real probability of the opponent set.
- Do not assume included priors sum to `1.0`.

## 8. Top-K / Coverage Policy

Recommended default:

- `default_top_k: 3`

Fields:

- `total_known_archetypes`: number of samples or archetypes known for that species in the repository/builder.
- `included_top_k`: actual number of samples included in this payload.
- `default_top_k`: requested default limit.
- `coverage_probability`: numeric estimated coverage when usage data exists, otherwise `null`.
- `coverage_probability_type`: `usage_derived`, `manual_estimate`, `heuristic`, or `not_available`.
- `omitted_archetypes_note`: required natural-language caveat.

Rules:

- `included_top_k` must not exceed `default_top_k` unless the caller explicitly requests another limit.
- `included_top_k` may be less than `default_top_k` when fewer samples exist.
- `coverage_probability: null` must not be interpreted as zero coverage.
- Omitted archetypes are not impossible.

Example:

```json
{
  "samples_meta": {
    "total_known_archetypes": 7,
    "included_top_k": 3,
    "default_top_k": 3,
    "coverage_probability": 0.85,
    "coverage_probability_type": "usage_derived",
    "omitted_archetypes_note": "Some lower-prior archetypes are not included."
  }
}
```

## 9. User Confirmed Override

User-confirmed information must override possible sample assumptions.

Recommended fields:

```json
{
  "known_status": "partially_confirmed",
  "user_confirmed_fields": {
    "item": "leftovers"
  }
}
```

Conflict example:

```json
{
  "sample_id": "garchomp_choice_scarf_01",
  "possible_item": "choice-scarf",
  "conflict_status": "conflicts_with_confirmed_fields",
  "conflict_reasons": [
    "Confirmed item leftovers conflicts with possible_item choice-scarf."
  ]
}
```

Policy options:

- Remove conflicting samples from `possible_samples`.
- Keep conflicting samples only with `conflict_status: "conflicts_with_confirmed_fields"`.
- Prefer removal in the default LLM payload to reduce overclaiming.
- Optionally keep conflict details in debug-only payloads later.

v0.37 stance:

- Document the conflict policy only.
- Do not implement filtering.
- Do not implement observation or user override UI.

## 10. LLM Contract / Guardrail

Bad wording:

- "상대는 고속 물리형 한카리아스입니다."
- "상대 스피드는 154입니다."
- "이 샘플이 실제 상대 세트입니다."
- "이 샘플 기준으로 확정 선공입니다."
- "prior_probability가 null이므로 가능성이 없습니다."

Good wording:

- "가능한 후보 중 고속 물리형 한카리아스 샘플이 있습니다."
- "이 샘플은 추정이며 실제 상대 세트는 확인되지 않았습니다."
- "prior probability는 아직 제공되지 않았습니다."
- "샘플은 현재 damage/speed 계산에 직접 사용되지 않았습니다."
- "확인된 정보가 생기면 그 정보가 샘플보다 우선합니다."

Required guardrails:

- Do not describe `possible_samples` as confirmed sets.
- Do not describe `sample_assumed` as `user_confirmed`.
- Do not interpret `prior_probability: null` as `0%`.
- Do not say Top-K omitted archetypes are impossible.
- Do not claim final turn order, KO, OHKO, 2HKO, or survival from samples.
- Do not trust a sample that conflicts with `user_confirmed_fields`.
- Do not say sample stats were used in damage or Speed calculations when `calculation_usage` is `context_only`.
- Do not infer item, ability, moves, nature, or SP distribution unless the sample explicitly includes those fields, and still label them possible.
- Do not promote `possible_stats.spe` to the opponent's exact Speed.

Contract language for future `ADVISOR_KNOWN_LIMITATIONS`:

- `opponent_assumptions`, when present, contains possible opponent profiles, not confirmed sets.
- `opponent_assumptions.calculation_usage == context_only` means samples are not used directly for damage or speed calculations.
- `prior_probability: null` means no prior is available, not zero probability.
- User-confirmed fields override possible sample assumptions.
- Do not infer final turn order, KO, survival, or exact stats from possible samples.

## 11. Prompt Integration Direction

Future `advisor_client` prompt behavior:

- If `opponent_assumptions.available` is `true`, summarize only the most relevant risks.
- Do not list every sample unless the user asks for detailed assumption context.
- Mention that samples are possible profiles, not confirmed sets.
- Mention `calculation_usage: context_only` when discussing why sample data did not change damage or Speed estimates.
- Do not call any estimate a "sample-based calculation" unless a future calculation mode actually uses samples.
- If `prior_probability` is `null`, say prior probability is not provided.
- If samples conflict with `user_confirmed_fields`, do not rely on the conflicting samples.
- If `available` is `false`, do not invent possible samples.

Recommended prompt addition:

```text
If opponent_assumptions is present, treat possible_samples only as context-only risk profiles.
Do not call them confirmed opponent sets.
If calculation_usage is context_only, do not say those samples changed damage_estimate or speed_context.
Do not interpret null prior_probability as zero probability.
User-confirmed fields override sample assumptions.
```

Summary behavior:

- Mention one or two top risks if useful.
- Prefer concise caveats over long sample dumps.
- Use sample context to explain uncertainty, not to fabricate certainty.

## 12. Future Builder / Helper Design

Candidate function:

```python
build_opponent_assumptions_payload(opponent_active, repository, top_k=3) -> dict
```

Supporting helpers:

```python
select_possible_samples(species_id: str, top_k: int = 3) -> list[dict]
attach_samples_meta(samples: list[dict], total_known_archetypes: int, coverage_probability: float | None) -> dict
apply_user_confirmed_field_filter(samples: list[dict], user_confirmed_fields: dict) -> list[dict]
normalize_prior_probabilities(samples: list[dict]) -> list[dict]
leave_prior_unnormalized(samples: list[dict]) -> list[dict]
validate_opponent_assumptions_payload(payload: dict) -> None
```

T3 recommendation:

- Keep `PokemonStatSampleRepository` focused on read-only sample data.
- Add a separate builder for payload policy.
- Start with `leave_prior_unnormalized()` because Top-K payloads may omit archetypes.
- Use `normalize_prior_probabilities()` only if a future calculation mode requires normalized weights.
- Keep the builder disconnected from damage and Speed helpers in the first implementation.

## 13. Tests Plan

Future implementation tests:

- species with samples produces `available: true`
- unknown species produces `available: false`
- unknown species reason is `no_samples_for_species`
- missing opponent active produces `reason: opponent_active_missing`
- repository failure produces `reason: repository_unavailable`
- default `top_k` is `3`
- `included_top_k` matches included sample count
- `possible_samples[*].is_user_confirmed` is `false`
- `prior_probability: null` is allowed
- null prior is not converted to `0`
- numeric prior must be within `0.0` to `1.0`
- `prior_probability_type` enum is validated
- `samples_meta` is present
- `coverage_probability` may be `null`
- `omitted_archetypes_note` is present
- `observation_history` is present and empty
- `update_policy.mode` is `static`
- `user_confirmed_fields` is present
- conflict policy can mark or remove confirmed-field conflicts
- `calculation_usage` is `context_only`
- no `damage_estimate` changes by default
- no `speed_context` changes by default
- prompt guardrail text is present
- existing repository regression remains
- existing payload contract regression remains

## 14. v0.38 Candidate

Recommended next candidate:

`v0.38 - Opponent Possible Sample Payload Implementation`

Include:

- `opponent_assumptions` payload builder.
- Active species sample lookup through `PokemonStatSampleRepository`.
- `top_k`, `samples_meta`, `observation_history`, and static `update_policy`.
- `calculation_usage: "context_only"`.
- Contract docs.
- Prompt guardrail.
- Tests.

Exclude:

- UI.
- damage integration.
- speed integration.
- calculation modes.
- Bayesian update.
- Turn Engine.
- KO/OHKO/2HKO.

Alternative:

`v0.38 - Opponent Sample Fixture Expansion`

Why lower priority:

- More samples without payload guardrails can increase overclaiming risk.
- Source quality and prior policy should be settled first.
- Current sentinel fixture is enough to validate builder shape.

T3 recommendation:

- Proceed with `v0.38 - Opponent Possible Sample Payload Implementation`.
- Keep it context-only.
- Continue to defer UI and calculation integration.

## 15. Out of Scope

Explicitly excluded from v0.37:

- code implementation
- data fixture changes
- repository changes
- UI changes
- automatic sample selection implementation
- damage integration
- speed integration
- calculation mode implementation
- Bayesian update implementation
- Turn Engine implementation
- KO/OHKO/2HKO implementation
- item effect additions
- logs, `.env`, secrets, API keys, or handoff capsule commits
