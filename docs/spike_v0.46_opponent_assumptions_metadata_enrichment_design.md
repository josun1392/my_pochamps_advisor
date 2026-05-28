# v0.46 Opponent Assumptions Metadata Enrichment Design

## 1. Current State

- `opponent_assumptions` exists as a top-level LLM payload section.
- `opponent_assumptions.calculation_usage` is `context_only`.
- `possible_samples` are `sample_assumed` and `is_user_confirmed: false`.
- Sample stats are not connected to `damage_estimate` or `speed_context`.
- v0.45 added developer-only debug summary helpers:
  - `build_opponent_assumptions_debug_summary`
  - `build_opponent_assumptions_debug_summary_from_assumptions`
  - `format_opponent_assumptions_debug_json`
- v0.45.1 verified that the debug summary is copy-ready, safe, and excludes:
  - full stats dump
  - full payload export
  - secrets / env / token logs
- v0.45.1 also found that `role`, `archetype_id`, and `possible_items` are `null` or empty in the debug output.
- The metadata exists in `data/static/pokemon_stat_samples.json`, but `_possible_sample_payload()` does not currently copy it into `opponent_assumptions.possible_samples`.

## 2. Problem Definition

- Developers need to know which possible sample is present and what role it represents.
- `sample_id` alone is enough for tests, but weak for live debugging.
- If `possible_items` is empty, it is hard to confirm that legal item filtering produced useful sample context.
- Debug summary should show practical metadata without exposing full stats or source dumps.
- Adding too much metadata to the LLM payload could make Gemini:
  - list samples too verbosely
  - treat sample role as confirmed
  - treat possible items as confirmed held items
  - imply sample metadata affected damage or Speed calculation
- The enrichment needs to improve developer visibility without changing battle math semantics.

## 3. Metadata Candidates

Candidate fields:

- `role`
- `archetype_id`
- `archetype_tags`
- `possible_items`
- `confidence`
- `source_type`
- `calculation_usage`
- `is_user_confirmed`
- `limitations`

Good debug summary fields:

- `sample_id`
- `species_id`
- `role`
- `archetype_id`
- `confidence`
- `possible_items`
- `is_user_confirmed`
- `used_for_damage`
- `used_for_speed`

Fields to handle carefully in LLM payload:

- `role`: estimated context only, not confirmed opponent role.
- `archetype_id`: useful for debugging, but not user-facing language by default.
- `possible_items`: possible assumptions only, not confirmed held item.
- `archetype_tags`: useful but can become verbose.
- `limitations`: keep short.

Fields that should remain excluded from debug summary:

- full `stats`
- full `sp_distribution`
- long source metadata
- `source_url`
- `source_note`
- full `update_policy`
- full `coverage_probability` details
- full `prior_probability` details
- long `reviewer_notes`

## 4. Source of Truth

Current flow:

1. `data/static/pokemon_stat_samples.json` stores sample metadata.
2. `PokemonStatSampleRepository` loads and validates sample records.
3. `build_opponent_assumptions_payload()` selects samples.
4. `_possible_sample_payload()` creates the LLM-facing `possible_samples` entries.
5. Debug summary reads only `opponent_assumptions`.

Source-of-truth principle:

- The fixture remains the source of sample metadata.
- The repository remains the validation/normalization boundary.
- `opponent_assumptions` should include only metadata safe enough for the LLM to see.
- The debug summary should summarize safe metadata already present in `opponent_assumptions`.
- The debug summary should not re-query the repository and produce a different view than the payload Gemini saw.

This avoids a mismatch where the debug output says a field was present even though Gemini never received it.

## 5. Enrichment Options

### Option A - Enrich `opponent_assumptions.possible_samples`

Add minimal safe metadata directly to each `possible_samples` entry:

- `role`
- `archetype_id`
- `possible_items`
- existing `confidence`
- existing `is_user_confirmed`

Pros:

- LLM payload and debug summary share one source.
- Debug summary becomes useful without repository re-query.
- Easy to test.
- Minimal implementation surface.

Cons:

- Gemini can see the extra metadata.
- Requires prompt/contract guardrail to prevent verbose listing or overclaiming.

### Option B - Debug summary only enrichment

Keep `opponent_assumptions` unchanged and let debug summary re-query the repository.

Pros:

- Gemini response cannot be influenced by extra metadata.
- Better separation from LLM prompt behavior.

Cons:

- Debug summary may diverge from the exact payload.
- Requires passing repository/species context to the debug helper.
- Can make debugging more confusing if payload and repository differ.

### Option C - Add nested `debug_metadata` inside `possible_samples`

Store metadata under `possible_samples[*].debug_metadata`.

Pros:

- Keeps debug fields visually grouped.
- Payload still carries enough information for export.

Cons:

- Gemini still sees it.
- More nested schema complexity.
- Guardrail cannot truly hide it from the LLM.

### Option D - Separate developer_debug object outside LLM payload

Build a separate object alongside the LLM payload and keep it out of the Gemini request.

Pros:

- Safest for LLM behavior.
- Can include richer metadata without prompt side effects.

Cons:

- Requires a separate generation path.
- Debug export no longer reflects only the payload sent to Gemini.
- More implementation complexity.

## 6. T3 Recommendation

Recommended v0.47 path:

- Use Option A with strict minimal enrichment.

Reasoning:

- v0.45 debug summary is intentionally based on the `opponent_assumptions` payload.
- If debug summary re-queries the repository, it stops proving what Gemini saw.
- Adding only `role`, `archetype_id`, and `possible_items` is useful enough for development while staying compact.
- Existing v0.43 guardrails already prevent long sample dumps.
- v0.47 can add or tighten guardrails to say metadata is context-only and should not be listed unless useful.

Keep Option D as a future path if richer debug metadata becomes necessary.

## 7. Proposed Minimal Metadata Set

Recommended `possible_samples` fields for v0.47:

- `sample_id`
- `species_id`
- `label_en`
- `label_ko`
- `source`
- `source_type`
- `confidence`
- `prior_probability`
- `prior_probability_type`
- `evidence_basis`
- `is_user_confirmed`
- `possible_item`
- `role`
- `archetype_id`
- `possible_items`
- `calculation_usage`
- `limitations`

Debug summary should use:

- `sample_id`
- `species_id`
- `role`
- `archetype_id`
- `confidence`
- `possible_items`
- `is_user_confirmed`
- `used_for_damage: false`
- `used_for_speed: false`

Explicitly excluded:

- full `stats`
- full `sp_distribution`
- `source_url`
- `source_note`
- full `update_policy`
- `coverage_probability` details
- `prior_probability` details beyond existing null and type
- long `reviewer_notes`

Important note:

- Current `possible_stats` in `possible_samples` already contains a stats subset/full dict. v0.47 should avoid expanding stat exposure further and may consider a later separate design to reduce or remove `possible_stats` if it is no longer needed.

## 8. LLM Guardrail Impact

Metadata enrichment must preserve:

- A sample is not confirmed.
- A sample role/archetype is estimated context.
- `possible_items` are possible assumptions, not confirmed held items.
- Metadata does not prove the opponent item, role, moves, stats, or set.
- Do not list sample metadata unless it helps explain uncertainty.
- Keep sample visibility to one concise line unless the user asks specifically for sample details.
- Never use sample metadata as a direct damage or Speed calculation input.
- Never infer final turn order, KO, OHKO, 2HKO, or survival from sample metadata.

Suggested contract addition for v0.47:

- "Opponent sample role, archetype, and possible_items are context-only metadata, not confirmed opponent information."
- "Do not enumerate sample metadata by default; summarize only the uncertainty impact."

## 9. Debug Summary Impact

After minimal enrichment, debug summary should show:

- non-null `role`
- non-null `archetype_id`
- legal-only `possible_items`
- `used_for_damage: false`
- `used_for_speed: false`
- `calculation_usage: context_only`
- `not_confirmed: true`
- no full stats dump
- no full payload export

Expected Rotom-Wash summary improvement:

```json
{
  "sample_id": "rotom_wash_defensive_pivot_repo_v42",
  "species_id": "rotom-wash",
  "role": "defensive_pivot",
  "archetype_id": "rotom_wash_defensive_pivot_repo_v42",
  "confidence": "estimated",
  "possible_items": ["leftovers", "sitrus-berry"],
  "is_user_confirmed": false,
  "used_for_damage": false,
  "used_for_speed": false
}
```

## 10. Tests Plan

Future implementation should test:

- Enriched metadata appears in `opponent_assumptions.possible_samples`.
- `role` is present for repo-native samples.
- `archetype_id` is present for repo-native samples.
- `possible_items` is a list.
- `possible_items` remains legal-only for repo-native samples.
- Debug summary populates `role`, `archetype_id`, and `possible_items`.
- Full stats are not added to debug summary.
- No additional full stats or SP distribution exposure is introduced.
- Prompt/contract guardrails prevent sample metadata dumps.
- Sample metadata is not used for `damage_estimate`.
- Sample metadata is not used for `speed_context`.
- Existing v0.43 sample visibility tests remain valid.
- Existing v0.45 debug summary tests remain valid.

## 11. v0.47 Candidate

Recommended:

- `v0.47 - Opponent Assumptions Minimal Metadata Enrichment Implementation`.

Include:

- Minimal metadata fields in `possible_samples`.
- Debug summary role/archetype/possible_items populated.
- Tests for metadata presence and legal-only possible items.
- Contract/docs update.
- No full stats expansion.
- No UI.
- No damage/speed integration.

Alternative:

- `v0.47 - Developer Debug Object Separate from LLM Payload Design`.

Use the alternative only if T1/T2 decide that any new metadata in the Gemini payload is too risky.

## 12. Out of Scope

- Code implementation.
- Fixture changes.
- Sample additions.
- Repository sample data changes.
- UI changes.
- Damage/speed integration.
- User-confirmed treatment changes.
- Calculation mode.
- Bayesian update.
- Turn Engine.
- Full stats exposure.
- Full payload export.
- Scraping or build script.
- logs, `.env`, secrets, API keys, or handoff capsule commits.
