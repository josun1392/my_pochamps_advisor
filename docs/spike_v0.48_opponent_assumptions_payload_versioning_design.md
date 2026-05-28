# v0.48 Opponent Assumptions Payload Versioning Design

## 1. Current State

- `opponent_assumptions` was introduced as a top-level payload section in v0.38.
- The current mode constant is still `multi_sample_assumption_v0.38`.
- Since v0.38, the payload has evolved:
  - v0.42 added repo-native sample fixture data.
  - v0.43 improved sample visibility guardrails.
  - v0.45 added developer debug summary helpers.
  - v0.47 added minimal metadata to `possible_samples`.
- The payload remains:
  - `context_only`
  - not confirmed battle information
  - not used by `damage_estimate`
  - not used by `speed_context`
- Tests and contract docs now match the expanded structure.
- The `mode` name no longer fully communicates the current payload shape.

## 2. Problem Definition

- `mode: multi_sample_assumption_v0.38` is historically accurate but stale.
- Future implementation may incorrectly assume the payload is still the original v0.38 shape.
- Metadata enrichment needs a clear compatibility story:
  - which fields are additive
  - which fields are required
  - which old payload shapes remain valid
- Debug summary helpers need to know what payload shape they are summarizing.
- Renaming `mode` directly could break tests and any downstream code that uses the current mode string.
- Versioning should make evolution explicit without implying a battle-math behavior change.

## 3. Versioning Goals

- Preserve backward compatibility.
- Clearly distinguish high-level behavior from payload shape.
- Treat additive metadata differently from breaking schema changes.
- Make prompt, contract, tests, and debug summary semantics easier to reason about.
- Avoid confusing sample metadata evolution with deterministic calculation integration.
- Keep future sample expansion, debug export, and UI/debug tooling from depending on stale assumptions.

## 4. Options Comparison

### Option A - Keep mode unchanged, add schema_version

Example:

```json
{
  "mode": "multi_sample_assumption_v0.38",
  "schema_version": "opponent_assumptions_v0.47"
}
```

Pros:

- Least likely to break existing tests and downstream code.
- Makes current payload shape explicit.
- Works well for additive version metadata.
- Easy to implement in v0.49.

Cons:

- `mode` and `schema_version` may look inconsistent.
- Requires docs to explain that `mode` is historical behavior while `schema_version` is current shape.

### Option B - Rename mode to latest version

Example:

```json
{
  "mode": "multi_sample_assumption_v0.47"
}
```

Pros:

- Simple to read.
- Makes the current version visible in one field.

Cons:

- Breaks tests that assert `multi_sample_assumption_v0.38`.
- Could break downstream code.
- Makes every additive field look like a mode change.
- It is unclear whether v0.47 refers to product version, schema version, or metadata version.

### Option C - Add explicit feature flags

Example:

```json
{
  "mode": "multi_sample_assumption_v0.38",
  "schema_version": "opponent_assumptions_v0.47",
  "payload_features": {
    "minimal_metadata": true,
    "debug_summary_supported": true,
    "context_only": true
  }
}
```

Pros:

- Clear feature-level semantics.
- Useful for debug summaries.
- Future extensions can add flags without renaming mode.

Cons:

- Slightly more payload surface.
- LLM should not recite feature flags in advice.

### Option D - Introduce contract_version and keep mode semantic

Example:

```json
{
  "mode": "multi_sample_assumption",
  "contract_version": "1.0",
  "metadata_version": "minimal_v1"
}
```

Pros:

- Clean long-term separation of behavior, contract, and metadata.
- Avoids product-version naming.

Cons:

- More migration work.
- Renames the current mode anyway unless both old and new fields coexist.
- Slightly heavy for the current project stage.

## 5. T3 Recommendation

Recommended v0.49 path:

- Use Option A plus a small part of Option C.
- Keep `mode: multi_sample_assumption_v0.38`.
- Add `schema_version: opponent_assumptions_v0.47`.
- Add `metadata_version: minimal_metadata_v1`.
- Add compact `payload_features`.

Recommended shape:

```json
{
  "mode": "multi_sample_assumption_v0.38",
  "schema_version": "opponent_assumptions_v0.47",
  "metadata_version": "minimal_metadata_v1",
  "calculation_usage": "context_only",
  "payload_features": {
    "possible_samples": true,
    "minimal_metadata": true,
    "debug_summary_supported": true,
    "full_stats_excluded": true,
    "damage_speed_integration": false
  }
}
```

Rationale:

- Preserves existing mode compatibility.
- Makes the current shape explicit.
- Allows debug tooling to display version information.
- Avoids implying that opponent samples are now calculation inputs.
- Keeps versioning additive and low-risk.

## 6. Proposed Fields

### `mode`

Keep as:

- `multi_sample_assumption_v0.38`

Meaning:

- Historical/high-level behavior label.
- Indicates multi-sample, context-only opponent assumptions.

### `schema_version`

Candidate:

- `opponent_assumptions_v0.47`

Meaning:

- Current payload shape, including minimal metadata enrichment.

### `metadata_version`

Candidate:

- `minimal_metadata_v1`

Meaning:

- Shape of `possible_samples` metadata:
  - `role`
  - `archetype_id`
  - `possible_items`
  - `calculation_usage`
  - no full stats
  - no SP distribution

### `payload_features`

Candidate:

```json
{
  "possible_samples": true,
  "minimal_metadata": true,
  "debug_summary_supported": true,
  "full_stats_excluded": true,
  "damage_speed_integration": false
}
```

Meaning:

- Developer-readable feature facts.
- Should not be turned into normal Gemini advice.

## 7. Compatibility Policy

- `mode` remains unchanged in v0.49 to reduce breakage.
- `schema_version`, `metadata_version`, and `payload_features` should be additive.
- Old payloads without `schema_version` should still be accepted by helper code.
- Debug summary can render missing schema fields as:
  - `"schema_version": "legacy"` or `null`
  - `"metadata_version": "legacy"` or `null`
- Prompt text does not need to mention version fields.
- Gemini should not discuss version fields in battle advice.
- Tests should explicitly cover:
  - new payload fields present
  - legacy payload missing fields handled safely

## 8. Tests Plan

Future implementation should test:

- `schema_version` field present.
- `metadata_version` field present.
- `mode` remains `multi_sample_assumption_v0.38`.
- `payload_features.possible_samples` is `true`.
- `payload_features.minimal_metadata` is `true`.
- `payload_features.debug_summary_supported` is `true`.
- `payload_features.full_stats_excluded` is `true`.
- `payload_features.damage_speed_integration` is `false`.
- Old payload without `schema_version` is still handled.
- Debug summary includes schema/metadata versions safely.
- Debug summary renders legacy version info without crashing.
- LLM prompt does not force version text into user advice.
- Existing `opponent_assumptions` regression tests remain valid.
- Existing debug summary tests remain valid.

## 9. Docs / Contract Impact

Update `docs/advisor_payload_contract.md` to explain:

- `mode` is a high-level historical behavior label.
- `schema_version` is the current payload shape.
- `metadata_version` is the `possible_samples` metadata shape.
- `payload_features` is developer/debug-oriented.
- Version fields are not user-facing battle advice.
- Version fields do not mean sample stats affect damage, Speed, KO, survival, or turn order.

Prompt impact:

- No new prompt requirement to recite versions.
- Keep existing concise sample visibility guardrail.
- Keep metadata context-only guardrail.

Debug summary impact:

- Include `schema_version`.
- Include `metadata_version`.
- Optionally include `payload_features`.
- Preserve no full payload export and no secrets.

## 10. v0.49 Candidate

Recommended:

- `v0.49 - Opponent Assumptions Payload Versioning Implementation`.

Include:

- Additive `schema_version`.
- Additive `metadata_version`.
- Optional additive `payload_features`.
- Debug summary version fields.
- Tests.
- Docs.
- No mode rename unless a migration test proves it is safe.

Alternative:

- `v0.49 - Payload Versioning Test Harness Design`.

Use the alternative if T1/T2 want version compatibility tests before adding payload fields.

## 11. Out of Scope

- Code implementation.
- Actual payload version fields.
- Fixture changes.
- Sample additions.
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
