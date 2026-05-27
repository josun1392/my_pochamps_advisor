# v0.39 Opponent Sample Expansion Source Plan

Status: design only  
Date: 2026-05-28

## 1. Current State

The project now has the first opponent sample foundation:

- `data/static/pokemon_stat_samples.json` exists.
- `core/pokemon_stat_sample_repository.py` exists.
- `llm/opponent_assumptions.py` builds top-level `opponent_assumptions`.
- `opponent_assumptions.calculation_usage` is `context_only`.
- Possible samples are sent to the LLM as assumptions, not confirmed opponent sets.
- Possible samples are not connected to `damage_estimate`.
- Possible samples are not connected to `speed_context`.
- Possible samples are not used for KO, OHKO, 2HKO, survival, or final turn order.
- Current samples are sentinel-only:
  - `garchomp`
  - `charizard`
  - `corviknight`
- Current samples all remain:
  - `status: "sample_assumed"`
  - `is_user_confirmed: false`
  - `confidence: "estimated"`
  - `source_type: "manual_estimate"`
  - `is_official: false`
- Source metadata and source type validation exist.
- There is no UI selector.
- There is no automatic sample application.
- There is no external scraping or build script.

The current sample count is enough to validate repository and payload behavior, but not enough to represent a useful battle metagame distribution.

## 2. Problem Definition

Multi-sample opponent advice becomes useful only when likely opponent forms are represented with enough breadth. A single sentinel Garchomp sample can prove the pipeline works, but it cannot describe the real range of possible Garchomp sets.

The risk is that adding many weakly sourced samples can make the advisor sound more certain while becoming less trustworthy.

Important constraints:

- Exact final stats and SP distributions are not always public.
- Item, move, ability, role, team context, and stat spread evidence may come from different source tiers.
- A common item or moveset does not prove a final stat spread.
- A published team paste may be real, stale, format-specific, or manually transcribed.
- A high-confidence sample source is still not the actual current opponent unless the user confirms it.
- Sample expansion should improve context, not create false certainty.

Therefore the next expansion should prioritize:

- clear source tier
- explicit confidence
- manual review
- limitations
- small initial scope
- regression tests
- no automatic calculation integration

## 3. Source Tier Policy

### Tier 1 - Direct Stat / Stat Usage Source

Definition:

- Sources that directly expose stat usage, Speed tiers, final stats, or spread information for a Pokemon in the target format or a close equivalent.

Examples:

- Pokebase-like stat usage or Speed tier source candidates.

Use:

- Best source tier for sample stat values.
- Can justify `confidence: "confirmed"` or `confidence: "usage_derived"` only when the final stat or spread evidence is actually visible.

Required review:

- Verify whether the source provides final stats, SP distribution, or only derived Speed tiers.
- Verify the format and season.
- Record whether the data is usage-derived, direct team data, or manually interpreted.

### Tier 2 - Usage / Item / Move / Team Context Source

Definition:

- Sources that provide usage, item, move, ability, role, or team archetype context but may not provide final stats.

Examples:

- Pikalytics.
- Pokemon Zone.

Use:

- Useful for likely roles, common items, common moves, and broad archetypes.
- Can support fields such as `likely_item`, `possible_items`, `likely_moves`, `possible_moves`, and `role`.

Required review:

- Do not treat item or move usage as direct stat evidence.
- If no direct stat evidence exists, any stat values derived from this tier must remain estimated or heuristic.

### Tier 3 - Team Article / Replica Team / Manual Extract

Definition:

- Sources where a specific team, paste, article, replica code, creator video, image, or write-up can be manually extracted.

Examples:

- DevonCorp team article.
- Public team paste.
- Creator video description.
- Replica team code.

Use:

- Good for team-specific sample candidates.
- Can support `confidence: "team_extract"` when the source is explicit and the extraction is reviewed.

Required review:

- Check whether the team is from the correct format/regulation.
- Mark stale season risk.
- Preserve source URL and reviewer notes.
- Record whether stats were explicitly shown or inferred.

### Tier 4 - Rules Validation Source

Definition:

- Sources used to validate rules, caps, legal stat mechanics, or format constraints.

Examples:

- Pokeos.
- Bulbapedia SP rule references.

Use:

- Validate that a sample is plausible/legal under Pokemon Champions rules.
- Confirm SP cap or format mechanics.

Required review:

- Do not use Tier 4 as the source for a sample spread by itself.
- Treat it as a validation layer.

### Tier 5 - Manual Estimate

Definition:

- T1/project curated estimated samples created for sentinel coverage or early advisor behavior.

Use:

- Lowest confidence source tier.
- Good for testing schema and payload behavior before real source expansion.

Required policy:

- `source_type: "manual_estimate"`
- `confidence: "estimated"`
- `is_user_confirmed: false`
- Must never be described as official, confirmed, or actual opponent stats.

## 4. Source Metadata Requirements

Future sample entries should require or strongly prefer:

- `source_type`
- `source_name`
- `source_url`
- `source_note`
- `regulation`
- `season`
- `last_reviewed`
- `is_official`
- `confidence`
- `confidence_reason`
- `evidence_basis`
- `reviewer_notes`
- `limitations`

Recommended semantics:

- `source_type` records the kind of evidence.
- `source_name` names the human-readable source.
- `source_url` may be `null` for internal sentinel/manual samples.
- `source_note` explains how the source should and should not be used.
- `regulation` records the Pokemon Champions regulation when known.
- `season` records freshness when known.
- `last_reviewed` records the last manual review date.
- `is_official` describes the source, not whether this is the actual opponent.
- `confidence` describes the sample source quality, not opponent certainty.
- `confidence_reason` explains why the confidence was chosen.
- `evidence_basis` summarizes what the sample is based on.
- `reviewer_notes` captures T1/T2 review caveats.
- `limitations` must state that the sample is not user-confirmed and not final battle truth.

## 5. Confidence Model

Recommended confidence enum:

### `confirmed`

Meaning:

- A source clearly exposes final stats, SP distribution, or equivalent direct spread information.

Guardrail:

- This means the sample source is confirmed.
- It does not mean the live opponent is confirmed to use that set.
- `is_user_confirmed` remains `false`.

### `usage_derived`

Meaning:

- The sample is derived from aggregate usage or stat distribution.

Guardrail:

- It can support priors or coverage metadata if source quality is sufficient.
- It still does not confirm the live opponent.

### `team_extract`

Meaning:

- The sample was manually extracted from a team paste, article, replica team, video, or other concrete team source.

Guardrail:

- It is source-specific and may be stale or format-specific.

### `estimated`

Meaning:

- Manual estimate or project-curated sentinel.

Guardrail:

- Lowest confidence.
- Current sentinel samples stay here.

### `unknown`

Meaning:

- Insufficient source quality or migrated legacy data.

Guardrail:

- Should be avoided for new curated samples unless the sample is intentionally quarantined or incomplete.

Global rule:

- Higher confidence never changes `is_user_confirmed` to `true`.
- No sample confidence value proves the actual opponent's current set.

## 6. Sample Type / Archetype Model

Future samples should be treated as archetypes, not just stat dictionaries.

Candidate fields:

- `archetype_id`
- `archetype_tags`
- `role`
- `likely_item`
- `possible_items`
- `likely_moves`
- `possible_moves`
- `stat_focus`
- `speed_tier_label`
- `risk_notes`

Candidate archetype tags:

- `fast_physical`
- `scarf_physical`
- `bulky_support`
- `special_attacker`
- `defensive_pivot`
- `setup_sweeper`

Why:

- The advisor needs to reason about risk, not just final stats.
- A sample with Speed but no role context is easy to overread.
- A role-focused schema lets the LLM say "possible Scarf physical risk" without claiming exact stats.

Recommended v0.40 approach:

- Add archetype fields only if they can be manually reviewed.
- Keep `possible_stats` optional in the payload if a sample is role-only.
- Preserve `is_user_confirmed: false` on every archetype.

## 7. Initial Expansion Scope

Do not expand to the full roster immediately.

Recommended v0.40 scope:

- 10 to 15 core Pokemon.
- 1 to 3 archetypes per species.
- Prefer species that are already common in testing or likely to expose different tactical risks.

Initial candidates:

- `garchomp`
  - Already used in local Gemini verification.
  - Good for fast physical, Scarf physical, and bulky/utility risk.
- `charizard`
  - Existing sentinel sample and item/damage modifier testing path.
  - Good for special attacker and possible speed-risk examples.
- `tyranitar`
  - Used in local Heat Wave verification.
  - Good for bulky attacker and special-defense risk examples.
- `corviknight`
  - Existing sentinel sample.
  - Good for bulky support / defensive pivot examples.
- `archaludon`
  - Likely useful for bulky/special or format-specific risk context.
- `pikachu`
  - Optional if it remains useful for regression or demonstration scenarios.

T3 recommendation:

- Start with 10 to 15 species only if T1/T2 can review source notes for each sample.
- Keep each species to top 2 or 3 archetypes.
- Prefer quality and reviewability over coverage.
- Keep manual estimates explicit until Tier 1 or Tier 2 evidence is available.

## 8. Manual Review Workflow

Recommended workflow for adding or changing samples:

1. Collect source candidate.
2. Assign source tier and `source_type`.
3. Confirm item, move, ability, and role evidence.
4. Record direct stat/SP evidence if the source provides it.
5. If stat evidence is indirect or absent, mark the stats as manual estimate.
6. Write `limitations` that prevent user-confirmed or final-truth interpretation.
7. Run sample schema validation.
8. Add `reviewer_notes` with source caveats and freshness.
9. Add or update repository and payload tests.
10. Request T1/T2 review before commit.

Review checklist:

- Is the source appropriate for Pokemon Champions or only adjacent?
- Is the regulation/season known?
- Are final stats explicit, derived, or estimated?
- Are item and move claims sourced separately from stat claims?
- Does the sample remain `is_user_confirmed: false`?
- Would the LLM overstate this if the caveat were removed?

## 9. No Scraping Policy

v0.39 does not add scraping or build scripts.

Future scraping or generated-data workflows should be designed only after:

- source terms are reviewed
- rate limits are understood
- data freshness policy is defined
- generated data and curated data are separated
- manual review is mandatory before curated fixture updates
- generated artifacts are excluded or clearly staged
- T1/T2 approve the source and storage policy

Default policy:

- No external scraping for v0.39.
- No generated data cache.
- No build script.
- No fixture expansion in this design step.

## 10. Payload Impact

Current v0.38 payload behavior remains valid:

- `opponent_assumptions` stays top-level.
- `calculation_usage` stays `context_only`.
- `possible_samples` remain possible profiles.
- `sample_assumed` remains not user-confirmed.
- `top_k` default remains `3`.

Impact after expansion:

- `possible_samples` becomes more useful because more than one archetype can exist per species.
- `included_top_k` will often be `3`.
- `total_known_archetypes` can exceed `included_top_k`.
- `omitted_archetypes_note` becomes important.

Prior and coverage policy:

- `prior_probability` may remain `null` for manual estimates.
- `prior_probability_type` should remain `not_available` unless there is a real evidence basis.
- `coverage_probability` should remain `null` for manual-only packs.
- Numeric `coverage_probability` should require usage-derived source quality.
- Numeric priors do not need to sum to `1.0` in a Top-K payload.

LLM policy:

- Top-K omitted archetypes are not impossible.
- Null prior is not zero probability.
- The LLM must not invent probabilities when the payload has none.

## 11. LLM Guardrail

Required guardrails for sample expansion:

- Sample source confidence is not live opponent confirmation.
- More samples do not make any one sample a confirmed set.
- `manual_estimate` samples should be described with low confidence.
- `usage_based_estimate` samples still do not prove the actual opponent set.
- If no prior is provided, do not invent probability.
- If samples are not connected to calculations, do not say damage or Speed was calculated from samples.
- Do not turn sample Speed into exact opponent Speed.
- Do not turn likely item or possible item into confirmed item.
- Do not turn likely moves into confirmed moves.
- Do not claim final turn order, KO, OHKO, 2HKO, or survival from sample context.

Good wording:

- "Possible Garchomp samples include fast physical and bulky variants, but none are confirmed."
- "The sample pack is context-only and was not used directly for damage or Speed calculation."
- "This manual estimate should be treated as a low-confidence risk cue."
- "No prior probability is available for this sample."

Bad wording:

- "The opponent is the fast physical sample."
- "This sample confirms the opponent's Speed."
- "The source confidence means the live opponent definitely has this spread."
- "No prior is listed, so this set is impossible."
- "Damage was calculated from the possible sample."

## 12. Tests Plan

Future implementation tests should cover:

- sample source metadata required fields
- confidence enum validation
- source_type enum validation
- archetype field validation
- species with multiple samples respects Top-K limit
- `manual_estimate` samples keep `prior_probability: null`
- `coverage_probability: null` remains allowed
- usage-derived samples are the only candidates for numeric coverage/prior values
- `possible_samples[*].is_user_confirmed` remains `false`
- high-confidence source samples still remain `is_user_confirmed: false`
- omitted Top-K archetypes do not remove unavailable/unknown caveats
- existing `opponent_assumptions` regression stays green
- existing sample repository regression stays green
- no damage/speed integration by default

## 13. v0.40 Candidate

Recommended next candidate:

`v0.40 - Opponent Sample Expansion Sentinel Pack`

Include:

- 10 to 15 curated species.
- 1 to 3 archetypes per species.
- strengthened source metadata.
- confidence and limitation fields.
- optional archetype fields if reviewed.
- repository validation tests.
- payload Top-K behavior regression tests.

Exclude:

- scraping
- UI
- damage integration
- Speed integration
- calculation mode
- Bayesian update
- Turn Engine
- KO/OHKO/2HKO

Alternative:

`v0.40 - Opponent Sample Archetype Schema Polish`

Why it may be chosen:

- If T1/T2 want schema certainty before adding more sample data.
- If source candidates are not ready for review.

T3 recommendation:

- Prefer `v0.40 - Opponent Sample Expansion Sentinel Pack` if T1/T2 can supply or approve source notes for the initial species.
- Otherwise, do a short archetype schema polish first and keep the sample pack for v0.41.

## 14. Out of Scope

Explicitly excluded from v0.39:

- code implementation
- fixture changes
- sample additions
- repository changes
- UI changes
- scraping or build script creation
- automatic sample application
- damage integration
- Speed integration
- calculation mode implementation
- Bayesian update implementation
- Turn Engine implementation
- KO/OHKO/2HKO implementation
- item effect additions
- logs, `.env`, secrets, API keys, or handoff capsule commits
