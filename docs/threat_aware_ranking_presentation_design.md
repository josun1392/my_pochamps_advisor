# Threat-Aware Ranking Presentation Design

## Implementation status

Implemented in `llm/advisor_threat_presentation.py`. The selected-only projector consumes the frozen completion evidence bundle, validates the existing application-owned tier, and returns a detached bounded DTO. For danger tiers it chooses the first matching frozen pair as an explanation witness; it does not calculate damage, action order, KO, probability, or a second threat ordering. `build_recommendation_presentation_model(...)` attaches only an available DTO to the validated selected candidate, and the existing formatter validates that DTO against the selected action before appending at most one threat sentence plus one partial-set scope note. Neutral, missing, malformed, self-preempted-only, and incomplete safety evidence remain silent. Provider payloads and prompts remain unchanged.

## Closure status and end-to-end boundary

The canonical downstream chain is trusted known opponent move authority, frozen opponent candidate, incoming mechanics, frozen pair evidence, known-threat summary, application-owned threat tier, eligibility, base rank and stable order, validated selected candidate, then this projector and formatter. The provider's minimal selection response neither creates nor changes any mechanics, tier, witness, ranking reason, or presentation text.

The actual DTO is bounded to selected-candidate reference, tier, adjustment kind, application reason code, optional canonical move-ID display fallback, text, optional scope note, and availability status. It deliberately excludes session and pair IDs, full summaries, snapshots, provenance, roll arrays, and exact-probability fractions. Existing selected-candidate text already displays canonical move IDs, so the projector uses the same no-network ID fallback when no richer display metadata is passed into the bounded path.

The six tier/reason mappings are one-to-one. Danger tiers choose the first matching frozen pair for the selected candidate only; no probability, damage maximum, alphabetic sort, provider prose, or other self candidate can affect the witness. Partial danger shows exactly one scope note; partial neutral and partial all-known-preempted remain silent. Complete-set rewards require four trusted moves, zero unknown slots, complete known-threat evaluation, and global completeness. A raw OHKO that is deterministically preempted is not rendered as executed or unresolved danger.

Exact probability remains supplemental to the existing formatter and cannot select a tier, witness, or wording category. `blocked` remains a move-success mechanics state, while `preempted` is a queued action lost to a faster allowed guaranteed KO. Ties and unknown order use only unresolved wording, never a probabilistic speed claim.

Existing actual ranking grounding remains the upstream validation: `partial-known-confirmed-threat-ranking` and `partial-known-neutral-no-safety-reward` passed together in round 1 using two approved calls with retry/fallback/repair at 0/0/0. This downstream closure performs no provider calls and verifies that no presentation authority returns to the provider.

Unsupported presentation scope remains non-selected details, pair or candidate comparison UI, a full opponent panel, free-form LLM rewrites, tactical/switch advice, expected-value wording, unknown-move prediction, probability-weighted wording, and raw diagnostics.

## Existing presentation inventory

`build_recommendation_presentation_model(...)` creates the validated selected-candidate model after response completion. `format_recommendation_presentation_text(...)` renders only that validated model. The provider response remains the three-field minimal selection contract: status, selected candidate ID, and bounded explanation code. Existing exact KO-probability formatting is selected-candidate evidence and remains separate from ranking cause.

## Authority and DTO

Future presentation consumes an application-owned, detached DTO after deterministic ranking. It never recomputes damage, action order, move success, KO, probability, pairs, summaries, or tier.

Required bounded fields are `candidate_id`, `threat_tier`, `threat_adjustment_kind` (`penalty`, `neutral`, or `bounded_reward`), `primary_reason_code`, optional `supporting_opponent_move_id`, text, and one optional scope note. Raw pair arrays, rolls, fractions, provenance, session IDs, snapshots, provider text, and ranking tuples are excluded.

## Tier wording and witness rule

`executed_guaranteed_ohko`, `unresolved_guaranteed_ohko_exposure`, and `executed_possible_ohko` produce one penalty witness. Choose the first frozen opponent candidate/pair matching the already-resolved tier; this is a deterministic explanation witness, not a threat ranking or best-response choice. Never choose by probability, damage, alphabetic name, or provider prose.

Guaranteed wording says only executable guaranteed one-hit risk. It says an opponent acts first only when pair order proves that fact. Unresolved wording states that order is unresolved; possible wording says only one-hit possibility. A raw OHKO that is deterministically self-preempted is not a primary executed-danger explanation.

`neutral_no_positive_threat_evidence` normally emits no threat text. It is never rendered as safety. `complete_set_no_guaranteed_ohko` and `complete_set_all_actions_preempted` require complete trusted four-move scope and complete supported mechanics; their copy says “current confirmed four moves” and “supported deterministic calculation range”, never safety, survival, or victory.

## Scope, terminology, and probability

For a surfaced partial-set explanation, show exactly one concise note: “상대의 아직 확인되지 않은 기술은 이 판단에 포함되지 않습니다.” Unknown movesets have no threat-specific claim. Complete but mechanically unsupported scope cannot receive complete-set safety copy.

Use `blocked` only for mechanics that prevent a move’s execution; use `preempted` only when a faster allowed guaranteed OHKO prevents the queued action through fainting. Ties and unknown order are not rendered as 50/50. Exact KO probability may be shown only by its existing supplemental formatter and must never be phrased as the reason for a ranking tier.

## Provider and UI boundary

The provider receives no threat DTO or witness and generates no threat explanation, uncertainty note, or safety claim. Initial UI scope is one selected-candidate ranking note plus, when needed, one partial-scope note. Non-selected pair-by-pair detail, tactical advice, switch advice, unknown-move prediction, and free-form LLM paraphrase remain out of scope.

## Failure and implementation boundary

Missing threat presentation evidence preserves the existing selected presentation. Malformed tier/reason/scope evidence suppresses threat-specific text and never changes ranking or selectability. A later bounded implementation may project this DTO between validated completion and the selected-candidate formatter; it must add no provider schema or ranking behavior.
