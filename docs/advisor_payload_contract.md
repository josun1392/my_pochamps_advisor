# Advisor Payload Contract

## v14.22 teardown lifecycle

Closing state and advice tokens remain window-local and never enter payloads,
responses, prompts, UI text, or logs.

## v14.21 adversarial lifecycle

Terminal claims and cleanup markers are MainWindow-only. They are not provider
payload, response, prompt, UI text, or logging fields. Duplicate/stale callback
ordering cannot bypass structured validation or expose provider content.

## v14.20 request-token lifecycle

Advice request tokens are MainWindow-only lifecycle identifiers. They are
captured by worker callbacks to suppress stale same-owner and cross-mode UI
updates; they are absent from the seven-field provider payload, six-field
response, prompts, presentation text, and usage logging. This does not alter
provider call policy or validation contracts.

## v14.19 runtime boundary inventory

The production structured path consumes a seven-field payload only at the
provider boundary, adapts the exact six-field response before semantic
completion, and formats only the validated presentation model for the shared
panel. `resolved` alone may expose a validated exact pair; insufficient-context,
no-usable-candidate, schema, semantic, preparation, and provider failures do
not. The structured runtime does not fall back to legacy/freeform advice. Panel
owner checks suppress cross-mode stale results, while same-owner request-token
suppression remains a documented implementation gap. Provider budget is zero.

## v14.18 offline evidence closure

The ten-fixture inventory is pure and sanitized. It records fixture identity,
expected terminal/acknowledgement/semantic boundaries, selectable and pair
expectations, provider-independent evaluability, and evidence category only.
`clear_resolved` and `insufficient_context` have v14.17 actual-provider pass
evidence; `no_selectable_candidates` is preparation-blocked; all other fixture
records are offline-only. The earlier v14.15 `invalid_claim` is retained as a
sanitized historical category, not provider text. The actual-provider budget is
zero, default runner execution remains suspended, and no payload or response
shape is changed.

## v14.16 fixed-fixture evaluation

The pure fixed-fixture runner reuses UI preparation, six-field response
adaptation, semantic completion, and presentation mapping. It records only
sanitized statuses, exact pair outcomes, failure codes, and aggregate counts.
Blocked preparation never invokes the adapter. Claim guidance now makes the
exact supported `kind`/`claim` object shape and non-empty claim requirement
explicit; the seven-field payload, six-field response, and validator are not
broadened.

## v14.15 three-fixture validation

The resolved fixture admitted an exact selectable `hyper-beam` / slot 1 pair.
The insufficient-context fixture produced sanitized `invalid_claim` at the
first claim-structure allowlist rule; it admitted no pair. A no-usable fixture
with zero selectable candidates was blocked before provider use. These outcomes
do not alter the seven-field payload, six-field response, exact-set checks, or
claim validator. Across the sample there were two calls, no retry/fallback/
repair, and no raw request/response persistence or display.

## v14.14 semantic guidance

Provider guidance forbids partial-context claims for resolved evidence and
requires exact selectable alternative move+slot pairs. It does not alter the
seven-field payload, six-field response, or validator.

## v14.13 semantic completion diagnosis

A resolved candidate cannot claim missing/unavailable/incomplete partial
context. That contradiction is retained as sanitized
`claim_evidence_contradiction`; exact-set, slot, and alternative validation
remain unchanged.

## v14.12 single-call smoke result

The one-call structured smoke completed as sanitized
`response_validation_failed`; no move/slot was admitted. Raw provider data is
not retained, and retry/fallback remains absent.

## v14.11 coexistence UX boundary

The shared advice panel receives an owner-tagged legacy freeform result or a
validated structured presentation, never raw provider data. The active owner
suppresses stale cross-mode completion; both actions are disabled while active.
Structured failure text is sanitized and legacy parsing remains unchanged.

## v14.10 structured stabilization

Structured response decoding accepts only a valid decoded six-field mapping.
Missing candidates/content, invalid/fenced/array JSON, unknown fields, safety,
HTTP, timeout, and network outcomes are sanitized without retaining raw body.
Usage is separate and allowlisted; logging stays disabled by default. One call
maximum and no retry/fallback/repair/legacy fallback remain mandatory.

## v14.9 structured recommendation coexistence

The separate structured path accepts only the seven approved request fields,
performs at most one schema-requested provider call, and admits only decoded
provider-neutral mappings through the response adapter and offline completion.
Validated presentation is formatted for the existing text panel; raw request or
response data, provider/repository/UI objects, credentials, tracebacks, and
network details are excluded. The legacy selected-move freeform path remains
unchanged. No retry or fallback exists; usage metadata is returned separately.
The sanitized structured usage logger is disabled by default, and protected
token logs are not read or written by this closure.

## v14.8 offline provider cycle and presentation model

`run_offline_recommendation_cycle` composes the existing UI preparation,
injected fake-provider adapter, and offline completion contracts without
network access. A non-ready preparation never invokes the provider. Provider
failures preserve prepared deterministic evidence; parser/semantic failures
preserve a sanitized completed failure and never retain raw provider output.

`build_recommendation_presentation_model` accepts only completed-cycle
mappings. It copies validated fields for `resolved`, `insufficient_context`,
and `no_usable_candidate`; failure maps omit the recommended pair while
retaining ordered candidate summaries and sanitized errors. Presentation output
contains no provider, repository, UI, secret, raw-response, traceback, network,
or token-log object. No actual provider/UI integration is wired.

## v14.7 offline provider adapters

Ready prepared cycles produce only the seven approved serialized request fields.
Decoded structured responses accept only the three provider-neutral statuses;
`validation_failed` remains local-only. Fake-provider failures preserve copied
evidence and never retain raw response data. No actual provider/network/UI
integration is wired.

## v14.6 offline UI preparation

The pure UI preparation adapter retains all ordered move slots, copies only
trusted deterministic snapshot fields, and composes the existing prepare-cycle
contract. `selected_move_index` does not reduce candidates; unsupported,
provider, and UI fields are excluded; repositories are input-only. No provider
adapter or validated UI result presentation is wired.

## v14.5 pure recommendation cycle

`prepare_recommendation_cycle` is a provider-neutral composition of candidate
slots, evidence, and request contracts. `complete_recommendation_cycle` reuses
the offline response parser. Non-ready cycles have no recommendation request;
parser failures preserve deterministic evidence and expose only sanitized
errors. Repository objects and raw responses are not output. The selected-move
provider/UI path remains unchanged and no provider/UI orchestration is wired.

## v14.4 offline response parser

Already-decoded offline response mappings are validated against the v14.3
request contract. Resolved and alternative recommendations require exact
selectable move-plus-slot pairs. Structured deterministic claims require
emitted compatible evidence; recursive forbidden-content checks and sanitized
failure codes protect credentials, raw data, provider/model/network fields,
and unsupported inference. Provider/UI integration is excluded.

## v14.3 offline recommendation request

The provider-neutral request retains every candidate's exact move-plus-slot
identity in `candidate_exact_set` and only eligible/eligible-with-warnings
pairs in `selectable_candidate_exact_set`. It preserves deterministic
comparison summaries and known limitations through deep-copy boundaries.
Readiness is `ready`, `no_candidates`, `no_selectable_candidates`, or
`invalid_evidence_bundle`; only `ready` may be used as an offline request.
Serialization is JSON-safe and rejects nested secret-like keys. Provider/UI
integration, ranking, model/network fields, and raw prompt/response data are
excluded.

## v14.2.1 deterministic candidate adapter

Candidate summaries adapt only deterministic production-context outputs. They
do not fabricate zero damage; absent deterministic damage is unavailable and
status moves remain not applicable. Registered moves use registry dispatch,
with no missing-context metadata fallback; environment alone may emit effective
type. Ordinary moves retain metadata mechanics only through the production
context, and only fields emitted by that context are summarized. All ten
dynamic families are exercised through candidate evaluation. Slot aggregation
preserves order, original indexes, duplicates, empty-slot omission, and failure
isolation; evidence bundles and summaries deep-copy their boundaries. No new
damage, hit-chance, move-order, healing, recoil, or self-consequence calculator
is introduced. Provider/UI integration is excluded.

## v13.31 production registry dispatch

The deterministic production context routes a registered canonical dynamic move
through exactly one registry-selected resolver. Ordinary unregistered moves
retain their metadata power/type path. Registered moves with missing required
trusted context emit only their selected unavailable assessment and never use
metadata as a dynamic-power or dynamic-type fallback. Environment is the only
family allowed to override effective type; all other dynamic families are
power-only. This corrects dispatch only: formulas and the ten-family/30-move
inventory are unchanged.

## v13.28 dynamic move registry

The registry maps each dynamic move identity to one assessment family. A
resolved family supplies only its effective power/type override; unavailable
results do not permit metadata fallback.

## v13.27 consecutive-use power

`consecutive_use_power_assessment` is derived only from explicit current-chain
stage snapshots, with scope `explicit-consecutive-use-move-power-only`.

## v13.26 battle-counter power

`battle_counter_power_assessment` is emitted only for Rage Fist and Last
Respects from explicit current-battle counters. It includes move, rule, counter,
effective power, status, and `explicit-current-battle-counter-move-power-only`.

## v13.4 Exact HP And KO Assessment

With limited context enabled, `current_hp_context.current_hp` carries only
user-confirmed exact current/max HP snapshots. It is distinct from visible
`hp_percent` and final-stat maximum HP. A resolved v13.3 damage estimate may
produce separate `hp_assessments`: percentage, 16-roll OHKO, and 256-pair
within-two-hits results. These include no recovery, chip, hazards, survival,
accuracy, critical, modifier, or between-turn semantics and do not replace
legacy `ko_context`.
For `current_hp=0`, the target is already fainted: percentage may remain, but
`hp_assessments` omits OHKO/two-hit entries and records `not_applicable`.

## v13.3 Limited Damage Result

`deterministic_calculation_context.damage_estimates` is separate from legacy
`damage_estimate` and may contain a resolved `base_damage_stage_only` range
only when trusted final stats/stages and selected move id/category/power are
available. It uses the documented project level-50 rule and excludes STAB,
type effectiveness, critical, burn, item, ability, weather, terrain, screens,
spread, priority, and KO work. Its exact acknowledgement is a
`Damage estimate` line in `[Deterministic Results]`, not `[Trusted Context]`.

## v13.2 Deterministic Calculation Context

With limited context enabled, `deterministic_calculation_context` is generated
only from normalized v13.1 final-stat context and v12 current-stage context.
It separates `effective_stats` from `speed_comparison`; its scope is
`final_stat_plus_stage_only` / `stage_only`, so it does not resolve priority,
items, abilities, weather, terrain, Tailwind, Trick Room, RNG, or final move
order. Its acknowledgement belongs in `[Deterministic Results]`, separate from
the exact user-confirmed `[Trusted Context]` inputs.

## v13.1 Final Stat Context

With limited context enabled, direct user-confirmed entries may map to
`final_stat_context.current_final_stats`. Each is a stage-unmodified final
stat with side, canonical stat ID, positive integer value,
`source=user_confirmed_final_battle_stat`, and `confidence=known`. HP is
maximum HP, not current HP. The context does not infer build inputs or apply
stages/modifiers; its structured acknowledgement is exact-compared.

## v12 Phase Closure

The v12 trusted-context categories are normalized independently and are only
included when limited context is enabled: current condition, current ability,
current stat stage, current field state, and observed item event. Their
structured acknowledgement entries are generated from the normalized payload
and exact-compared by the deterministic parser. Existing known current items
remain `item_profiles`/item-context data and do not gain a new acknowledgement
category through v12 closure.

These contexts are not deterministic calculation results. They do not establish
transition timing, source, duration, resolved mechanics, exact stats/damage/HP,
final order, RNG, or post-turn state. See `docs/V12_PHASE_REVIEW.md` for the
v13 calculation-boundary entry point.

## v12.79 Current Field State Context

With the limited-context gate enabled, a validated user-confirmed field
snapshot may map to `field_state_context.current_field`. It contains weather,
terrain, optional global effects, optional side effects, `status=user_confirmed`,
`source=user_confirmed_current_field_state`, and `confidence=known`.

It is a current identity snapshot only. It does not establish how or when a
field began or ended, duration, source move/ability/item, resolved effects,
exact damage/HP/effective speed/final order, RNG, or post-turn state. Explicit
weather or terrain `none` is confirmed current absence, not an end event.
Structured advice exact-compares `Current weather`, `Current terrain`,
`Current global field effect`, and `Current side field effect` entries against
the normalized snapshot. This context is not connected to calculation inputs.

## v12.78 Current Stat Stage Context

With the limited-context gate enabled, validated
`current_stat_stage_confirmations` may map to
`stat_stage_context.current_stages`. Each entry has `side`, canonical `stat`,
integer `stage` in -6..+6, `status=user_confirmed`,
`source=user_confirmed_current_stat_stage`, and `confidence=known`. There is
at most one entry for each side/stat pair.

This context is a user-confirmed current stage only. It does not establish when
or why the stage changed, its ability/item/move source, exact final stats,
damage, HP, speed tie, final order, RNG, resolved effect, or post-turn stage.
It is not connected to damage or speed calculation. Structured advice requires
`Current stat stage | side | stat | signed stage` and exact-compares normalized
entries alongside condition, ability, and observed-item-event contexts.

## v12.77 Fixed Ability Smoke Fixture

The sanitized smoke CLI additionally accepts the fixed allowlisted fixture
`current-condition-ability-item-event`. It sends raw user-confirmed self
`burn`, opponent condition `unknown`, self `intimidate`, opponent ability
`unknown`, and opponent Focus Sash activation input through the same production
normalization path. Confidence is not present in raw fixture entries.

The normalized payload drives the exact structured acknowledgement set:
current condition self/opponent, current ability self/opponent, and observed
item event opponent. This fixture does not expand arbitrary input support or
change CLI output schema/exit codes. It remains a trusted-context identity
fixture, not evidence of ability activation, resolved mechanics, exact
outcomes, or current species ability inference.

## v12.75 Known Ability Trusted Context

With the limited-context gate enabled, validated
`current_ability_confirmations` map to
`ability_context.current_abilities`. Every entry is a side-keyed
`user_confirmed_current_ability` identity with `status=user_confirmed` and
`confidence=known`; at most one exists per side. `unknown` means the current
ability is not known. `none`, candidate lists, species/cache metadata, and
future event/resolution fields are rejected.

When ability context exists, the prompt requires a compact structured line:

```text
Current ability | <side> | <ability>
```

This line is exact-set validated together with current conditions and observed
item events from the normalized payload. It establishes only a current ability
identity. It does not establish activation, triggering, suppression,
replacement, copying, restoration, immunity/prevention resolution, boosted
stats, exact modifiers/damage/HP, RNG, final order, or post-turn state. With
the gate off, ability state remains in session but is omitted from payload,
prompt, acknowledgement expectations, and CLI evaluation.

## v12.74 Current Ability Payload Foundation

When the limited-context gate is enabled, validated user-confirmed current
ability entries may form the intermediate payload foundation
`ability_context.current_abilities`. Entries are side-keyed and contain only
`side`, canonical `ability`, `status=user_confirmed`,
`source=user_confirmed_current_ability`, and `confidence=known`. Raw UI
confirmations are removed before payload serialization.

This foundation is not yet provider prompt context. `_build_ui_selected_prompt`
removes `ability_context` before serializing its prompt payload, so no ability
guard, readback instruction, or structured acknowledgement line is present.
`unknown` is valid; `none`, candidate lists, possible species ability sources,
event/suppression/replacement fields, resolved effects, exact outcomes, RNG,
and final order remain rejected.

## v12.73 Known Current Ability Foundation

`normalize_user_confirmed_current_ability(...)` is validation-only and does
not add an ability field to the advisor payload. It accepts only
`user_confirmed_current_ability` with `status=user_confirmed`, self/opponent
side, one normalized lowercase-kebab-case ability identity, and normalized
`confidence=known`. `unknown` is allowed as an explicit unknown identity;
`none` is rejected to avoid conflating a current ability identity with
suppression or replacement state.

Species/cache ability lists, hidden ability metadata, common sets, selected
species defaults, move interactions, damage/speed/item inference, and model
guesses are not current ability sources. Activation, suppression, replacement,
copy, resolved effect, exact damage/stat/HP, immunity/prevention, RNG, final
order, and post-turn state are rejected and remain future contracts. No ability
payload context, prompt wording, or structured acknowledgement entry exists in
this phase.

## v12.72 Structured Acknowledgement Matrix Status

When normalized `condition_context.current_conditions` or
`item_event_context.observed_events` exist under the limited-context gate, the
prompt requires a short `[Trusted Context]` acknowledgement followed by
`[Advice]`. Expected acknowledgement entries are generated from those normalized
payload contexts, not UI raw confirmations. Each entry preserves category, side,
identity, and item-event type where applicable.

The acknowledgement validator requires the expected ordered exact set and
rejects missing, extra, duplicate, swapped, category-changed, identity-changed,
or event-type-changed entries. A normal response with no enabled trusted context
does not require a block; if one is supplied with entries, those entries are
rejected as extra. The acknowledgement is readback only and must not replace an
actionable `[Advice]` body or expose raw source/status/confidence metadata.

`none` means user-confirmed current absence of a major condition and `unknown`
means the specific condition is unavailable. Neither establishes a removal,
recovery, application, trigger, exact effect, post-turn state, RNG, or order.
Observed item events remain observations and do not establish resolved effects,
exact recovery/HP, current possession, consumption, or final order.

Status: `STRUCTURED ACKNOWLEDGEMENT PHASE: READY - LIMITED ACTUAL EVIDENCE`.
The v12.72 offline matrix is green and v12.71 supplied 2/2 assessable semantic
PASS responses; this status does not authorize an additional provider call.

**Milestone:** v0.38 - Opponent Possible Sample Payload
**Payload mode:** `ui-selected-pokemon-v0.18`
**Status:** Current contract for the PySide6 UI to Gemini LLM advisor path.

## Purpose

The advisor payload is the boundary between deterministic UI / engine state and the Gemini natural-language recommendation layer. This contract prevents the LLM from treating incomplete UI metadata as confirmed battle math.

The current app can send selected Pokemon identity, HP percent, user-confirmed move metadata, optional user-confirmed final stats for the active Pokemon, top-level item profiles, context-only opponent sample assumptions, raw/effective Speed comparison context, limited Quick Claw speed-order item context, limited Light Ball species-stat item context, damage estimates for the user's confirmed moves, additive limited KO context, explicitly labeled opponent move information, and damage estimates for user-confirmed opponent known moves. Every damage estimate includes an `assumption_profile` describing the stat/item model used. Supported attacker-side damage items may be applied only when `damage_estimate.item_effects` marks them as applied. v0.23 connects the normal item selector to the Champions legal item repository: normal UI options include Unknown, No item, and legal fixture items. Damage-supported but non-legal/debug items such as Choice Band, Choice Specs, and Life Orb are not normal selector options. v0.28 adds `speed_context` for raw Speed comparison only when both active Pokemon have user-confirmed final Speed. v0.30 extends `speed_context` with Choice Scarf effective Speed when Choice Scarf is user-confirmed. v0.98 adds move-level `speed_order_context` for user-confirmed legal Quick Claw as limited advice context only. v3.1 makes move-level `species_stat_item_context` a sibling explanation for user-confirmed legal Light Ball on Pikachu when the supported modifier is applied in `damage_estimate.item_effects`. v0.38 adds `opponent_assumptions` as context-only possible opponent sample profiles. The app does not yet send EV/IV/nature breakdowns, final battle KO truth, final turn order, candidate move damage estimates, sample-based damage or Speed calculations, or Turn Engine state.

v11.1 status note: the controlled UI-selected `battle_state_context` Gemini smoke
passed with exactly one actual Gemini call and zero retries. This does not
change the payload contract. The supported UI battle-state source remains
self/opponent species and HP percent only, sourced as `visible_ui`; status,
boosts, item, field state, and `known_conditions` remain unknown or `[]`.

v11.2 status note: the actual smoke phase is closed as PASS. This closure
records the v11.1 one-call/no-retry result, payload/prompt/response boundary
PASS, and sanitized token/cost summary. It does not change the payload contract
or add new battle-state sources.

v11.3 status note: user-confirmed item boundary is design-only. No contract
change is made. Future item support should use the existing known-value envelope
only for direct `user_confirmed` or explicitly allowed `explicit_input` item
sources; hidden, inferred, legality-derived, damage-derived, and context-derived
items remain unknown.

v11.4 status note: `battle_state_context.item` source policy is now locked by
contract/helper tests. Known item values may use only `user_confirmed` or
`explicit_input`. `visible_ui`, `calculated_from_visible`, legality-gate,
resist-berry, context-derived, hidden, usage/meta/common-set, and damage-reverse
item sources must not become known items. UI item integration is still not
connected.

v11.5 status note: user-confirmed item source adapter design is documentation
only. Existing UI-selected battle-state extraction remains species/HP-only. A
future item adapter should require explicit opt-in, read only trusted
`item_profiles` metadata, map direct `status=user_confirmed` user input to
`user_confirmed`, reserve `explicit_input` for a direct explicit input surface,
and keep missing, ambiguous, legality-derived, resist-berry-derived,
damage-derived, or inferred items unknown.

v11.6 status note: the UI-selected battle-state source adapter now has an
explicit opt-in item path. Default calls still extract species/HP only and keep
items unknown. When `include_user_confirmed_items=True`, only
`item_profiles` entries with `status=user_confirmed`, `source=user_input`, and
non-empty `item_id` become `battle_state_context.item` values with
`source=user_confirmed`. Runtime UI checkbox mapping and payload builder call
flow are not connected to this opt-in yet.

v11.7 status note: a mocked offline prompt fixture now verifies known
user-confirmed items in `battle_state_context`. The fixture confirms that
self/opponent known items are preserved in payload and serialized prompt, the
existing battle-state guard remains present, field state and `known_conditions`
stay unknown/empty, and no item consumption, post-turn HP, RNG, speed tie, Quick
Claw, or full outcome fields are created. UI runtime mapping remains unchanged.

v11.8 status note: user-confirmed item UI mapping is design-only. The
recommended future mapping is to call
`build_battle_state_context_from_ui_selected_state(battle_input,
include_user_confirmed_items=enable_battle_state_context)` at the existing
battle-state generation point. Checkbox off remains the hard gate and must omit
`battle_state_context` entirely, even if top-level `item_profiles` contain
user-confirmed items. No payload contract or runtime behavior changes are made
in v11.8.

v11.9 status note: the existing limited-context checkbox battle-state path now
passes `include_user_confirmed_items=enable_battle_state_context` when it
auto-generates `battle_state_context`. Checkbox off still omits
`battle_state_context` entirely. Checkbox on can include known
`user_confirmed` item values only from valid `item_profiles` metadata; malformed
or forbidden metadata remains unknown. UI copy and prompt guard wording are
unchanged.

v11.10 status note: the limited-context UI copy now mentions user-confirmed
items as possible context when the existing checkbox is enabled. This is a
copy-only update: payload contract shape, checkbox behavior/default, payload
builder call flow, and prompt guard wording are unchanged.

v11.11 status note: a mocked UI-selected offline smoke now covers the existing
checkbox off/on path for user-confirmed battle-state items. Checkbox off omits
`battle_state_context`; checkbox on can serialize valid user-confirmed item
envelopes, while malformed or forbidden metadata remains unknown. This does not
change payload contract shape, UI copy, checkbox behavior/default, payload
builder call flow, or prompt guard wording.

v11.12 status note: the user-confirmed item phase is closed as PASS for design,
contract/helper tests, source adapter, prompt/offline fixture, UI mapping, UI
copy, and mocked UI-selected offline smoke. No contract shape change is made in
closure. Known items remain limited to allowed user-confirmed/explicit sources,
and known item context does not imply activation, consumption, post-turn HP,
RNG, speed tie, Quick Claw activation, selected opponent move, or full outcome.

v12.0 status note: controlled user-confirmed item Gemini smoke is design-only.
No contract shape or runtime behavior changes are made. Any future v12.1
provider execution requires explicit T1 approval, exactly one actual Gemini
call, retry count 0, no second provider call, sanitized token/cost reporting
only, and preservation of the existing user-confirmed item boundary.

v12.1 status note: the controlled user-confirmed item Gemini smoke passed after
explicit T1 approval. Exactly one actual Gemini call was made with retry count
0, no second provider call, and no Vertex AI call. Payload and prompt
boundaries passed for user-confirmed self/opponent item context, and the
response safety scan found no forbidden activation, consumption, post-turn HP,
RNG, speed tie, Quick Claw, selected move, hidden item, damage reverse, or full
outcome claims. No payload contract shape change is made.

v12.2 status note: the user-confirmed item actual smoke is closed as PASS.
Closure records T1 approval, exactly one actual Gemini call, retry count 0, no
second provider call, no Vertex AI call, payload boundary PASS, prompt boundary
PASS, response safety scan PASS, forbidden matches none, and sanitized
token/cost summary only. No payload contract shape or runtime behavior change is
made.

v12.3 status note: field state source design is documentation-only. Current
runtime behavior remains unchanged: weather, terrain, screens, hazards, and
room stay unknown in the UI-selected path. Future known field values should be
limited to explicit/user-confirmed sources first, with `visible_ui`,
`battle_log_observed`, and `parser_observed` reserved for later designs after
real sources exist. Damage, KO context, turn order, opponent move context,
species/common/meta, item effects, legality gate, resist berry context, hidden
guesses, and model guesses must not create known field state. No payload
contract shape change is made.

v12.4 status note: field state source contract tests now lock the initial field
source policy. Helper normalization preserves `explicit_input` and
`user_confirmed` field values and normalizes forbidden field sources to unknown.
Payload validation accepts only `explicit_input` and `user_confirmed` for known
field values and rejects `visible_ui`, `calculated_from_visible`,
`context_derived`, damage/KO/turn/order/opponent-move-derived, species/common,
item-effect, legality-gate, resist-berry, hidden, and model guesses as field
sources. Known field values do not create duration, expiration, post-turn,
`damage_estimate`, or `ko_context` changes.

v12.5 status note: field helper normalization now validates field values by
field key while preserving the v12.4 contract shape. `weather`, `terrain`, and
`room` known values remain limited to `explicit_input` or `user_confirmed`.
`screens` and `hazards` keep side-specific values inside the existing known
envelope. Malformed helper inputs normalize to unknown, and malformed direct
known field envelopes are rejected by payload validation. No UI integration,
prompt guard wording change, payload builder call-flow change, duration,
expiration, post-turn, `damage_estimate`, or `ko_context` behavior change is
made.

v12.6 status note: a mocked offline prompt fixture now verifies known field
state in `battle_state_context`. The fixture confirms known weather, terrain,
room, side-specific screens, and side-specific hazards are preserved in payload
and serialized prompt, the existing battle-state guard remains present, unknown
field context stays unknown, existing limited contexts coexist, and mocked
responses avoid duration, expiration, post-turn field state, damage precision,
hidden field, damage-derived field inference, and full outcome claims. No
prompt guard wording, UI integration, payload builder call-flow, provider, or
payload contract shape change is made.

v12.7 status note: field state UI source inventory is documentation-only. The
current UI-selected path has no weather, terrain, screens, hazards, room, or
field-condition input/display source. `battle_input` does not contain
`field_profiles`, and the UI battle-state adapter still reads only species/HP
plus optional trusted item profiles. The item profile metadata pattern can be
reused by a future `field_profiles` design, but no payload contract shape,
runtime mapping, UI behavior, prompt guard wording, provider behavior,
`damage_estimate`, or `ko_context` change is made.

v12.8 status note: Field Profile Dialog design is documentation-only. It
proposes a future user-confirmed `field_profiles` input surface for weather,
terrain, room, side-specific screens, and side-specific hazards. The design
distinguishes `unknown` from user-confirmed `none`, reuses the item profile
`status=user_confirmed` plus `source=user_input` metadata pattern, and keeps
known field state as current context only. No payload contract shape, runtime
mapping, UI behavior, prompt guard wording, provider behavior,
`damage_estimate`, or `ko_context` change is made.

v12.9 status note: Field Profile Dialog contract tests lock future
`field_profiles` metadata before UI implementation. Trusted dialog metadata is
`status=user_confirmed`, `source=user_input`, and a valid `value`, which maps
to `source=user_confirmed` known field envelopes. `unknown` remains
unconfirmed/missing/malformed input, while trusted `none` is known absence.
Both-side empty screens/hazards values are accepted as user-confirmed known
absence; single-side empty or malformed side-specific values remain unknown.
No Field Profile Dialog UI, runtime field mapping, payload builder call-flow,
prompt guard wording, provider behavior, `damage_estimate`, or `ko_context`
change is made.

v12.10 status note: Field Profile Dialog UI is implemented as a standalone
dialog that returns the v12.9 `field_profiles` metadata shape for weather,
terrain, room, side-specific screens, and side-specific hazards. `unknown`
remains unconfirmed/not-entered metadata, while `none` remains user-confirmed
known absence. The dialog is not wired into `battle_input`,
`battle_state_context`, prompt generation, payload builder call flow, or the
limited-context checkbox path. No provider behavior, prompt guard wording,
`damage_estimate`, or `ko_context` change is made.

v12.11 status note: Field State UI Mapping Design is documentation-only. It
proposes session-local `MainWindow` storage for future `field_profiles`, keeps
the existing limited-context checkbox as the hard gate, and recommends a future
`include_user_confirmed_fields=False` helper flag parallel to
`include_user_confirmed_items`. Checkbox off should omit both
`battle_state_context` and field-profile data from the provider payload path.
Checkbox on may map only valid user-confirmed field metadata into
`battle_state_context.field`; missing, unknown, malformed, untrusted, forbidden,
`context_derived`, or `calculated_from_visible` metadata stays unknown or is
rejected by direct payload validation. No contract shape, runtime mapping,
payload builder call-flow, prompt guard wording, provider behavior,
`damage_estimate`, or `ko_context` change is made.

v12.12 status note: Field State UI Mapping Tests lock the helper/client
boundary for future field-profile mapping. The UI-selected battle-state adapter
now has default-off `include_user_confirmed_fields=False`; field profiles are
ignored unless explicitly enabled, and automatic prompt generation enables that
field opt-in only when `enable_battle_state_context=True`. UI-only
`field_profiles` are removed from default advice payloads and can reach the LLM
only as normalized `battle_state_context.field` entries. Valid user-confirmed
field metadata maps to known field envelopes; missing, `unknown`, malformed,
`context_derived`, and `calculated_from_visible` metadata remains unknown.
Trusted `none` remains known absence. No FieldProfileDialog button integration,
MainWindow storage UI, prompt guard wording change, provider call,
`damage_estimate`, or `ko_context` change is made.

v12.13 status note: Field State UI Mapping Implementation confirms the
field-profile mapping path as active under the existing limited-context
checkbox. When `_build_ui_selected_prompt(...)` auto-generates
`battle_state_context`, it passes
`include_user_confirmed_fields=enable_battle_state_context`; checkbox off still
omits `battle_state_context`, and top-level `field_profiles` are removed from
the default advice payload. Checkbox on can normalize valid user-confirmed
`field_profiles` into `battle_state_context.field`. Missing, `unknown`,
malformed, `context_derived`, and `calculated_from_visible` metadata remains
unknown. No FieldProfileDialog button integration, MainWindow storage UI, prompt
guard wording change, provider call, `damage_estimate`, or `ko_context` change
is made.

v12.14 status note: FieldProfileDialog Button Integration Design is
documentation-only. It recommends adding a future secondary field-state button
inside `LLMAdvicePanel` near the existing limited-context checkbox, with
`MainWindow` owning session-local `field_profiles` state. The design keeps the
limited-context checkbox as the payload hard gate: opening or saving field
profiles must not send field data unless `enable_battle_state_context=True`.
No button integration, MainWindow storage field, payload contract shape,
payload builder call-flow, prompt guard wording, provider behavior,
`damage_estimate`, or `ko_context` change is made.

v12.15 status note: FieldProfileDialog Button Integration Tests lock the future
button/session-state behavior with a test-only seam. Apply stores
`field_profiles`, Cancel preserves prior state, Reset unknown plus Apply stores
the default unknown profile shape, and saved field profiles remain gated by the
existing limited-context checkbox. Checkbox off still omits both
`battle_state_context` and top-level `field_profiles`; checkbox on can map saved
profiles into `battle_state_context.field`. No user-facing button,
`MainWindow._field_profiles` implementation, payload contract shape, payload
builder call-flow, prompt guard wording, provider behavior, `damage_estimate`,
or `ko_context` change is made.

v12.16 status note: FieldProfileDialog Button Integration adds a user-facing
secondary `Field state` button in `LLMAdvicePanel` and MainWindow-owned
session-local `field_profiles` storage. Saved profiles are copied into the
UI-selected battle input, then remain controlled by the existing
limited-context checkbox gate. Checkbox off omits `battle_state_context` and
top-level `field_profiles`; checkbox on can normalize valid saved profiles into
`battle_state_context.field`. No new checkbox, payload contract shape change,
prompt guard wording change, provider behavior, `damage_estimate`, or
`ko_context` change is made.

v12.17 status note: Limited Context Copy Update for Field State updates only
the limited-context checkbox tooltip/status copy and related tests. The copy now
mentions user-confirmed field state as current weather/terrain/room/screens/
hazards context, and says it does not confirm turn count, expiration, post-turn
result, exact damage, or full turn outcome. No checkbox behavior/default,
FieldProfileDialog behavior, field mapping behavior, payload contract shape,
payload builder call-flow, prompt guard wording, provider behavior,
`damage_estimate`, or `ko_context` change is made.

v12.18 status note: Field State UI End-to-End Offline Smoke verifies the
UI-selected field-state path with mocked provider calls only. Saved
`field_profiles` stay omitted when the limited-context checkbox is off; when the
checkbox is on, they normalize into `battle_state_context.field` while
top-level `field_profiles` stays absent from the prompt payload. Existing
`turn_pipeline`, `turn_order_context`, `opponent_move_context`, user-confirmed
item context, and `battle_state_context` coexist. The mocked response safety
check avoids duration, expiration, post-turn state, exact damage, full outcome,
damage-inferred field, and hidden-field claims. No payload contract shape,
prompt guard wording, provider behavior, `damage_estimate`, or `ko_context`
change is made.

v12.19 status note: Field State UI Phase Closure is documentation-only and
closes the v12.3-v12.18 offline field-state UI path. Current behavior remains:
`FieldProfileDialog` stores user-confirmed `field_profiles` in
`MainWindow._field_profiles`; the existing limited-context checkbox is the hard
gate; checkbox off omits `battle_state_context` and top-level `field_profiles`;
checkbox on can normalize valid field profiles into `battle_state_context.field`
without top-level leakage. Known fields remain current context only, unknown
remains unknown, and trusted `none` remains user-confirmed absence. No contract
shape, production code, prompt guard wording, provider behavior,
`damage_estimate`, or `ko_context` change is made.

v12.20 status note: Controlled Field State Gemini Smoke Design is
documentation-only. It designs a future actual-provider smoke for the
checkbox-gated user-confirmed field-state path, requiring separate T1/T2
approval, exactly one actual Gemini call, retry count 0, no second provider
call, no Vertex AI call, pre-call payload/prompt checks, response safety checks,
and sanitized token/cost reporting only. No actual provider call is made in
v12.20, and no contract shape, production code, prompt guard wording,
FieldProfileDialog behavior, field mapping behavior, payload builder call-flow,
`damage_estimate`, or `ko_context` change is made.

v12.24 status note: Controlled Field State Gemini Smoke passed after explicit
T1/T2 approval. Exactly one actual Gemini call was made with retry count 0, no
second provider call, and no Vertex AI call. The pre-call prompt payload
contained gated `battle_state_context.field` values for user-confirmed rain,
electric terrain, Trick Room, side-specific screens, and side-specific hazards,
with no top-level `field_profiles` leakage. The sanitized response scan found
no duration, expiration, post-turn state, exact damage, full outcome,
damage-inferred field, hidden field, or hidden item claims. No payload contract
shape, production code, prompt guard wording, FieldProfileDialog behavior,
field mapping behavior, payload builder call-flow, `damage_estimate`, or
`ko_context` change is made.

v12.25 status note: Field State Actual Smoke Closure is documentation-only and
closes the v12.20-v12.24 actual validation phase as PASS. The final supported
field-state payload behavior remains unchanged: user-confirmed
`field_profiles` may normalize into gated `battle_state_context.field` only
when the existing limited-context path is enabled, top-level `field_profiles`
does not leak, known field values are current context only, and duration,
expiration, post-turn state, exact damage, full outcome, hidden field, and
damage-inferred field claims remain out of scope. No payload contract shape,
production code, prompt guard wording, FieldProfileDialog behavior, field
mapping behavior, payload builder call-flow, `damage_estimate`, or `ko_context`
change is made.

v12.26 status note: Item Activation/Consumption Boundary Design is
documentation-only and does not change payload shape or runtime behavior.
Current known item context remains user-confirmed/current context only. It does
not imply item activation, item consumption, resolved item effects, post-turn
item state, exact post-turn HP, exact damage, resolved turn order, hidden item
inference, opponent set/item inference, or LLM/model guesses. Future fields
such as `item_event_context`, `observed_item_events`, `resolved_item_effects`,
and `post_turn_item_state` require separate design, source contracts, tests,
and approval before implementation.

v12.27 status note: Item Activation/Consumption Contract Tests lock the v12.26
boundary. Valid known item context remains unchanged and still means
user-confirmed/current context only. Malformed `battle_state_context` payloads
that include item-event or resolved-effect fields such as `item_activated`,
`item_consumed`, `resolved_item_effect`, `post_turn_item_state`,
`post_turn_hp_from_item`, `quick_claw_activated`, `focus_sash_triggered`, or
`berry_consumed` are rejected by contract. Forbidden inference sources such as
damage reverse, species/common-set, hidden-state/model guesses, turn-order
context, opponent-move context, legality gate, and resist berry inference do not
become known items or item events. No prompt guard wording, damage behavior,
payload filtering, item activation, item consumption, resolved effect, or
post-turn item state behavior is implemented.

v12.28 status note: Item Activation/Consumption Prompt Fixture adds offline
mocked prompt/response coverage for the v12.26-v12.27 boundary. Generated
prompts may include known user-confirmed item names and current item context,
but prompt payloads must not serialize item-event fields such as
`item_activated`, `item_consumed`, `resolved_item_effect`,
`post_turn_item_state`, `quick_claw_activated`, `focus_sash_triggered`,
`berry_consumed`, `recovery_applied`, `damage_reduction_applied`, `rng_roll`,
`speed_order_override`, or `post_hit_hp_1`. Safe mocked response wording may say
known items can matter strategically and that Focus Sash or Quick Claw may
matter if conditions occur, but activation/consumption is not confirmed or
resolved from current context. No prompt guard wording, provider behavior,
damage behavior, payload filtering, item activation, item consumption, resolved
effect, or post-turn item state behavior is implemented.

v12.29 status note: Item Activation/Consumption Phase Closure is
documentation-only and closes the v12.26-v12.28 boundary phase as PASS. The
final supported behavior remains: known item means user-confirmed/current
context only; it does not imply item activation, item consumption, resolved item
effect, post-turn item state, post-turn HP, exact damage modifier application,
Speed/order override, hidden item inference, or opponent set/item inference.
Observed activation, observed consumption, resolved item effects, and post-turn
item state remain future-only and require separate source inventory, design,
contract tests, prompt tests, and approval.

v12.30 status note: Item Event Source Inventory is documentation-only and does
not change payload shape or runtime behavior. The only current item-event source
boundary remains `user_confirmed_current_item` -> `known_item` only. Future
trusted source candidates are `explicit_user_event_confirmation`,
`battle_log_observed`, `parser_observed`, `imported_replay_observed`, and
`future_turn_engine_resolved`; they require separate source contracts, payload
contracts, tests, and approval before observed activation, observed
consumption, resolved item effects, or post-turn item state can appear in the
payload.

v12.31 status note: Item Event Source Contract Tests lock the v12.30
future-only boundary. Current known item payloads remain
`source=user_confirmed` known-item context only. Future item event fields such
as `item_event_context`, `observed_events`, `resolved_effects`,
`observed_activation`, `observed_consumption`, `item_event_type`,
`event_source`, `event_confidence`, `event_turn`, and `event_provenance` are
rejected by current `battle_state_context` validation. Future source names such
as `explicit_user_event_confirmation`, `battle_log_observed`,
`parser_observed`, `imported_replay_observed`, and
`future_turn_engine_resolved` are still future-only and do not create trusted
observed/resolved item events without a separate implementation.

v12.32 status note: Explicit User Item Event Confirmation Design is
documentation-only and does not change payload shape or runtime behavior. The
future `explicit_user_event_confirmation` source is intended to create observed
item event candidates only, such as `item_activation_observed` or
`item_consumption_observed`. It must not directly create resolved item effects,
post-turn item state, exact HP, exact damage, RNG results, resolved Speed/order,
hidden item inference, or full turn outcomes.

v12.33 status note: Explicit User Item Event Contract Tests add a helper-level
validator for future `explicit_user_event_confirmation` candidates. A valid
candidate may use `source=explicit_user_event_confirmation`,
`status=user_confirmed`, and one of the observed event types
`item_activation_observed`, `item_consumption_observed`,
`item_recovery_observed`, `item_prevention_observed`, or
`item_reveal_observed`. This remains an observed-candidate contract only: it is
not mapped into current prompt payloads as trusted `item_event_context`, and it
must not create `resolved_item_effect`, `post_turn_item_state`, exact HP, exact
damage, RNG rolls, or Speed/order overrides.

v12.34 status note: Explicit User Item Event Dialog UI Tests are test-only and
do not change payload shape or runtime behavior. The future dialog contract
locks Apply/Cancel/Reset/session-local behavior with a fake controller seam,
but no real dialog, button, MainWindow wiring, or `item_event_context` mapping
is implemented. Generated prompt payloads still omit `item_event_confirmations`
and trusted `item_event_context`.

v12.35 status note: Explicit User Item Event Dialog Implementation adds the
standalone `ItemEventDialog` widget and dialog unit tests only. The dialog can
return validated explicit user observed event candidates with
`source=explicit_user_event_confirmation` and `status=user_confirmed`, but it
does not add LLMAdvicePanel buttons, MainWindow session wiring,
`item_event_context` payload mapping, or observed event prompt mapping.
Generated prompt payload shape remains unchanged.

v12.36 status note: Explicit User Item Event Button Integration Tests are
test-only and do not change payload shape or runtime behavior. The future
button/session-local wiring contract is locked with a fake controller seam, but
no real LLMAdvicePanel Item Event button, MainWindow `_item_event_confirmations`
wiring, `item_event_context` payload mapping, or observed event prompt mapping
is implemented. Generated prompt payloads still omit item event confirmations.

v12.37 status note: Explicit User Item Event Button Integration adds the real
LLMAdvicePanel `Item event` button and MainWindow `_item_event_confirmations`
session-local UI state. This is UI-only wiring: `_item_event_confirmations` is
not added to `battle_input`, `item_event_context` remains unmapped, and observed
item event prompt mapping is still future-only.

v12.38 status note: Item Event Payload Mapping Design is design-only. It
proposes a future limited-context-gated path from `_item_event_confirmations` to
`item_event_context.observed_events`, but current payload shape is unchanged and
`item_event_context` remains unmapped until future tests and implementation.

v12.39 status note: Item Event Payload Mapping Tests lock the future mapping
contract with a test-only helper seam. The limited context gate must omit item
event context when off; when on, only validated explicit user-confirmed observed
events may enter future `item_event_context.observed_events`, with
`confidence=observed`. Resolved, post-turn, exact HP/damage, RNG, and
Speed/order fields remain forbidden. Runtime mapping and prompt serialization
are still pending.

v12.40 status note: Item Event Payload Mapping Implementation connects
session-local confirmations to `battle_input` only under the existing limited
context gate. The raw UI field is removed before provider payload serialization;
valid events normalize into `item_event_context.observed_events` with
`confidence=observed`. Invalid events are omitted, and resolved/post-turn/exact
HP/damage/RNG/Speed-order fields remain forbidden. No new natural-language
prompt wording was added.

v12.41 status note: Observed Item Event Prompt Fixture adds a minimal guard
only when `item_event_context` is present. It states that explicit user-confirmed
events are observed context only, not resolved mechanics, exact calculations,
post-turn state, RNG, or resolved order. Offline fixtures capture the production
prompt with mocked provider and logging functions; runtime provider behavior is
unchanged.

v12.42 status note: The Item Event Payload Mapping phase is `CLOSED - PASS`.
v12.38-v12.41 established the design, contract tests, limited-context-gated
mapping, and offline prompt fixture. Current scope remains explicit
user-confirmed observed events only; resolved effects, post-turn state, exact
HP/damage, RNG, and Speed/order behavior remain outside this phase.

v12.49 status note: The item-event prompt guard adds a compact response
contrast/readback instruction only when normalized non-empty
`item_event_context.observed_events` is present. It distinguishes known current
items from observed events and requests side/item/event-type acknowledgement;
the payload contract and resolved/post-turn/exact/RNG/Speed-order boundaries are
unchanged.

v12.50 status note: Offline production-path validation passes for the v12.49
contrast/readback guard. The instruction is present only for valid observed
events, absent for disabled/absent/invalid/known-item-only paths, and coexists
with trusted damage context. This is readiness evidence only; it does not
authorize an actual provider re-smoke.

v12.52 status note: When valid observed events and current known item context
coexist, the item-event prompt guard also requests side/item user-confirmed
current-known readback and explicitly keeps it separate from observed event
meaning. Event-without-known-item paths retain observed readback without
inventing a known item. Payload shape and existing item-event boundaries are
unchanged.

v12.54 status note: The v12.26-v12.53 Item Event phase is `CLOSED - PASS`.
Known current-item, explicit observed-event, limited-context gate, invalid
omission, prompt attribution, and final actual smoke boundaries are closed.
Future lifecycle, automated source, and resolved-calculation features remain
separate scopes and do not alter this payload contract.

v12.55 lifecycle note: Session-local item event summary, edit/delete,
duplicate, ordering, and explicit reset behavior do not change the payload
contract. The limited-context gate and observed-only mapping remain unchanged.

v12.56 integration note: Lifecycle mutations are verified through the existing
limited-context mapping and observed-only prompt guard. Clear/delete omit the
context when no valid events remain; checkbox off preserves session state while
omitting it from payload. No payload shape or prompt contract changed.

v12.57 status/condition note: `normalize_user_confirmed_current_condition(...)`
is validation-only. It recognizes only user-confirmed current major-condition
facts and does not map them into the existing payload or prompt. Event,
resolved, post-turn, exact, RNG, and order semantics remain excluded.

v12.58 status/condition note: The UI stores valid current conditions in
`battle_input["current_condition_confirmations"]` only behind the existing
limited-context gate. The advisor payload filter removes that candidate field,
so `condition_context` and condition-specific prompt wording remain unmapped.

## Item Context Guard Registry

v3.4 centralizes available item context mention labels, item-specific prompt guard text, and forbidden wording metadata in `ADVICE_ITEM_CONTEXT_GUARD_METADATA` beside `ADVICE_ITEM_CONTEXT_KEYS`.

The registry is used only for prompt guard generation and tests. It does not change default advice payload filtering:

- `available=true` item contexts remain visible in default advice payload.
- unavailable, deferred, blocked, unsupported, unconfirmed, non-triggered, or absent item contexts remain debug/enriched-only.
- `speed_context` remains the top-level Choice Scarf Speed exception and is not part of `ADVICE_ITEM_CONTEXT_KEYS`.
- Light Ball no-item residue guard and Chilan Berry Normal-type limited labels are now registry-backed.
- Choice Scarf `speed_context` protection remains separate from move-level `speed_order_context`.

## Turn State Snapshot Contract

v4.1 adds a standalone `core.turn_state` contract for future Turn Engine / Battle State work. The contract defines `PokemonBattleSlot`, `BattleState`, `TurnInput`, and `TurnSnapshot` with safe dictionary serialization and minimal validation.

v4.3 adds optional payload adapter support for this contract. When a caller explicitly supplies a snapshot, the default advice payload may include a top-level `turn_snapshot` section.

v4.5 adds a UI-selected `battle_input` adapter in `llm.advisor_turn_snapshot`. The strict helper `build_turn_snapshot_from_battle_input(...)` converts existing UI-selected dictionaries into a `TurnSnapshot`, while `try_build_turn_snapshot_from_battle_input(...)` returns `None` on validation failure so user-facing advice can fall back to the previous payload flow. `run_ui_selected_advice(...)` now attempts this snapshot build and passes the result to the optional v4.3 payload adapter.

If no snapshot is supplied, the advisor payload remains unchanged.

When `turn_snapshot` is present:

- it is selected/pre-turn known state only
- it is not full turn simulation
- it does not perform item trigger evaluation
- it does not simulate item consumption
- it does not update post-damage HP
- it does not simulate guaranteed move order
- it does not resolve exact status or volatile condition outcomes

The adapter remains intentionally disconnected from current calculator behavior:

- current damage estimates are unchanged
- raw damage rolls are unchanged
- Q12 multipliers are unchanged
- `ko_context` remains limited damage-roll context
- item-context filtering is unchanged
- item trigger evaluation, item consumption, HP updates, and speed/order simulation are not implemented

The v4.5 UI mapping is intentionally minimal:

- active player/opponent species id/name, slot index, HP percent, known item id/status, and selected player move can be mapped
- stat stages, major status, volatile conditions, weather, terrain, field conditions, and turn number stay empty or `None`
- `system_default_none` and explicit no-item profiles serialize as battle-state `absent`
- unknown or unconfirmed item profiles serialize as `unknown`

Future milestones can use the snapshot contract as the bridge between UI selected state, deterministic trigger results, and LLM payload generation.

## Turn Event Contract

v5.1 adds a standalone `core.turn_event` contract for future Minimal Turn Engine work. The contract defines `TurnEvent` and `TurnPipelineResult` with safe dictionary serialization and minimal validation.

This is a contract layer only:

- `TurnEvent` can represent a candidate trigger, a known modifier, a not-simulated event, a blocked event, or an unavailable event
- `TurnPipelineResult` can group event candidates with references to existing `damage_estimate` and `ko_context` surfaces
- default pipeline simulation status is `none`
- `full` remains a schema-reserved value only and is not used by v5.1 behavior

The v5.1 contract is intentionally disconnected from runtime advice behavior:

- it is not connected to `advisor_client.py`
- it is not inserted into the LLM payload
- it does not evaluate item triggers
- it does not consume items
- it does not update HP or post-turn state
- it does not simulate move order, speed ties, or random activation
- it does not change damage estimates, raw rolls, Q12 multipliers, `ko_context`, item contexts, or payload filtering

v5.3 adds `llm.advisor_turn_events` as a fixture/helper-level mapper from already-built advisor context dictionaries to `TurnEvent` candidates. It maps only `available=true` contexts for the first pass:

- Light Ball `species_stat_item_context` -> `damage` / `known_modifier` / `known`
- Quick Claw `speed_order_context` -> `pre_move` / `candidate` / `possible`
- Focus Band or Focus Sash `survival_context` -> `on_damage_before_ko` / `candidate` / `possible`
- Chilan Berry `chilan_berry_context` -> `on_damage_before_ko` / `candidate` / `possible`

Unavailable, blocked, or deferred contexts do not create events in v5.3. The mapper does not create `TurnPipelineResult`, does not connect to `advisor_client.py`, and does not insert events into the LLM payload.

v5.4 expands fixture coverage for the same helper without changing payload exposure. Tests now verify unknown and malformed contexts, contradictory unavailable/blocked/deferred item statuses, stable event ordering, and non-overstated event summaries/limitations. The policy remains: only usable `available=true` contexts produce mapper events, and those events remain outside the LLM payload.

v5.5 adds `build_turn_pipeline_result_from_advice_payload(...)` as a fixture/debug helper that bundles mapper events into `TurnPipelineResult`. It preserves optional `selected_move_id`, `input_snapshot`, `damage_estimate_ref`, and `ko_context_ref` as references only. The helper defaults `simulated` to `limited`, includes limitations that it is not a full turn simulation, and remains disconnected from `advisor_client.py` and the LLM payload.

v5.6 adds `scripts/spike_turn_pipeline_debug.py` and `docs/debug_turn_pipeline_sample_v5.6.md` as a local dry-run/debug report for fixture TurnPipelineResult output. The report prints JSON to stdout, records event stage/status/certainty/limitations, and does not call Gemini, Vertex AI, `advisor_client.py`, or LLM payload wiring.

v5.8 adds optional payload adapter support for `TurnPipelineResult`. When a caller explicitly supplies a pipeline result, the default advice payload may include a top-level `turn_pipeline` section. The adapter is default-off and explicit-only:

- absent or `None` `turn_pipeline` preserves the existing advice payload
- supplied `TurnPipelineResult` or mapping values are normalized before insertion
- `simulated="full"` is rejected
- pipeline limitations are required
- prompt limitations are added only when `turn_pipeline` is present
- `run_ui_selected_advice(...)` does not auto-generate `TurnPipelineResult`
- `build_turn_pipeline_result_from_advice_payload(...)` remains disconnected from runtime advice flow

When `turn_pipeline` is present, it remains a limited planning/debug summary:

- it is not full turn simulation
- it does not resolve RNG
- it does not simulate item consumption
- it does not update post-turn HP
- it does not guarantee move order
- it does not provide exact item trigger results
- it does not resolve exact status or volatile outcomes
- it does not replace `damage_estimate`, `ko_context`, or existing item contexts

v5.9 strengthens the prompt and contract guard for this field. When `turn_pipeline` is present, candidate events must remain candidate events, not resolved outcomes. The LLM must not describe pipeline events as consumed items, final HP, guaranteed order, confirmed triggers, resolved RNG, resolved speed ties, exact status resolution, or replacement evidence for `damage_estimate`, `ko_context`, or existing item contexts. When `turn_pipeline` is absent or `None`, the extra prompt guard is not added and the payload remains unchanged.

v6.1 adds `build_optional_turn_pipeline_for_advice_payload(...)` as an explicit/default-off generation helper. It accepts an already-built advice payload and returns `None` unless `enable_turn_pipeline=True`. When enabled, it produces a limited `TurnPipelineResult` through the existing mapper helper, does not mutate the input payload, and can be passed manually to `build_ui_advice_payload(..., turn_pipeline=...)`. It does not auto-generate inside `advisor_client.py`, does not connect to the UI-selected advice flow, and does not call Gemini or Vertex AI.

v6.2 verifies the manual fixture path that combines the explicit helper with the optional payload adapter. With generation disabled, the helper returns `None` and the payload remains unchanged. With generation enabled, callers may manually pass the limited result to `build_ui_advice_payload(..., turn_pipeline=...)`, which adds top-level `turn_pipeline` while preserving `damage_estimate`, `ko_context`, and existing item contexts. The prompt guard remains conditional on explicit `turn_pipeline` presence.

v6.4 strengthens the advice payload builder smoke coverage for this explicit path. Tests verify omitted/default and explicit disabled flags, manual enabled generation, top-level `turn_pipeline` insertion, prompt guard present/absent behavior, and preservation of `damage_estimate`, `ko_context`, and existing item contexts. This remains fixture/dev-only and does not auto-generate inside `run_ui_selected_advice(...)`.

v6.6 adds a no-actual-Gemini dry-run flag near the UI-selected advice flow. `run_ui_selected_advice(..., enable_turn_pipeline=False)` remains default-off, and the UI worker still calls it without enabling TurnPipeline. When tests explicitly pass `enable_turn_pipeline=True`, `_build_ui_selected_prompt(...)` builds a limited TurnPipeline from the already-built advice payload and inserts it through the existing optional adapter. The prompt guard appears only in the explicit path. Tests mock `call_gemini`; no real Gemini or Vertex AI call is made. This does not add a UI checkbox, does not make TurnPipeline user-facing by default, and does not implement full simulation, item consumption, HP updates, RNG, speed ties, or exact trigger resolution.

v6.8 locks the TurnPipeline payload shape with plain pytest dictionary assertions. Default, explicit-off, and `turn_pipeline=None` paths must omit top-level `turn_pipeline` and preserve the same payload shape. Explicit limited `TurnPipelineResult` or equivalent mapping input may add top-level `turn_pipeline`, with `simulated="limited"`, stable event ordering, required limitations, and conditional prompt guard wording. `damage_estimate`, `ko_context`, and existing item contexts remain present and unchanged. No external snapshot dependency or large golden JSON file is required.

v6.13 locks TurnPipeline prompt copy with plain pytest assertions. When `turn_pipeline` is absent, the TurnPipeline guard and UI copy labels remain absent. When `turn_pipeline` is present, prompt anchors must preserve limited planning/debug summary wording, candidate / not-resolved event wording, no full turn simulation wording, and conflict policy with `damage_estimate`, `ko_context`, and existing item contexts. Tests also protect against resolved-outcome wording such as guaranteed activation, consumed items, final HP, full turn simulation result, or resolved speed ties. The v6.12 UI copy labels remain design-only and are not wired into the UI.

v6.15 adds an offline end-to-end advice fixture for the TurnPipeline path. The fixture uses `run_ui_selected_advice(...)` with `call_gemini` and token logging patched in memory, then compares default-off and explicit-on prompts. Default-off prompts omit top-level `turn_pipeline` and omit the TurnPipeline guard. Explicit-on prompts include `turn_pipeline.simulated == "limited"`, candidate / not-resolved guard wording, and unchanged `damage_estimate`, `ko_context`, and item contexts. No actual Gemini, Vertex AI, or external provider call is made.

v6.18 adds a default-off developer UI flag in `LLMAdvicePanel` for this explicit path. The checkbox label is `턴 이벤트 후보 포함`, starts unchecked, has no persisted auto-enable setting, and only passes `enable_turn_pipeline=True` when the user checks it before pressing the existing advice button. Toggling the checkbox alone does not call Gemini, does not call Vertex AI, and does not generate a payload. When unchecked, `run_ui_selected_advice(...)` receives `enable_turn_pipeline=False` and the payload/prompt remains the default-off shape without top-level `turn_pipeline` or the TurnPipeline prompt guard.

## Turn Order Context Contract Draft

v7.2 defines a fixture-level payload contract for a future optional `turn_order_context` section. No runtime payload adapter is added in v7.2.

The draft context is deterministic and limited:

- `kind` must be `deterministic_turn_order_context`
- `confidence` may be `limited` or `unknown`
- `priority.priority_relation` may be `own_higher_priority`, `opponent_higher_priority`, `same_priority`, or `unknown`
- `speed.speed_relation` may be `own_faster_by_base_speed`, `opponent_faster_by_base_speed`, `equal_base_speed_tie_candidate`, `own_faster_by_confirmed_final_speed`, `opponent_faster_by_confirmed_final_speed`, `equal_confirmed_final_speed_tie_candidate`, `unknown_due_to_missing_speed_data`, or `unknown_due_to_missing_priority_or_move`
- `order_hint` may be `own_likely_before_opponent_if_same_priority`, `opponent_likely_before_own_if_same_priority`, `priority_overrides_speed`, `tie_or_unknown`, or `unknown`
- `candidate_modifiers[*].resolved` must be `false`
- `unsupported` must include unresolved boundaries such as speed tie resolution, RNG item activation, exact final order, item consumption, and post-turn HP update when applicable

The context must not include fields that imply resolved outcomes, including `final_order_resolved`, `item_consumed`, `post_turn_hp`, `speed_tie_resolved`, or `rng_item_activated`.

Prompt safety wording for future integration:

- This turn order context is limited planning context, not a resolved move order.
- Do not claim speed ties are resolved.
- Do not claim RNG items activate.
- Do not claim exact final order unless explicitly provided.
- Do not infer item consumption or post-turn HP from this context.

v7.3 adds `llm.advisor_turn_order_context.build_deterministic_turn_order_context(...)` as a standalone helper for this contract. It accepts known priority, base Speed, optional confirmed final Speed, and candidate modifiers. Confirmed final Speed takes precedence over base Speed when both sides are known. Candidate modifiers are normalized with `resolved=false`, and resolved fields such as `activated`, `final_order_resolved`, `item_consumed`, and `post_turn_hp` are not emitted. The helper is not connected to the runtime advice payload, prompt, UI, Gemini call path, or full Turn Engine.

v7.4 adds an optional explicit-only payload adapter for this contract. `build_ui_advice_payload(..., turn_order_context=..., enable_turn_order_context=True)` may insert top-level `turn_order_context` after validating the v7.2 contract. Omitted or disabled `enable_turn_order_context` preserves the previous payload shape, and `enable_turn_order_context=True` with no supplied context also preserves the previous shape. The adapter rejects forbidden resolved-outcome fields recursively, requires unresolved candidate modifiers, and requires unsupported boundaries for speed tie resolution, RNG item activation, exact final order, item consumption, and post-turn HP update. `turn_order_context` coexists with optional `turn_pipeline`; neither optional field overwrites the other. v7.4 does not add prompt integration, UI auto-connection, saved setting auto-enable, Gemini calls, resolved turn order, item consumption, post-turn HP update, or full Turn Engine behavior.

v7.6 locks the future prompt guard contract with focused tests. `_build_turn_order_context_prompt_guard(payload)` returns an empty string when top-level `turn_order_context` is absent and returns safety wording when it is present. The guard says `turn_order_context` is limited planning context, not a resolved move order, and forbids exact final move order, speed tie resolution, RNG item activation, item consumption, and post-turn HP inference. Tests also verify coexistence with the existing `turn_pipeline` guard. v7.6 does not insert this guard into `_build_ui_selected_prompt(...)`; runtime prompt integration remains a later step.

v7.7 wires the `turn_order_context` guard into `_build_ui_selected_prompt(...)` behind explicit keyword-only inputs. Default/off prompts remain unchanged. When a caller supplies `turn_order_context` and sets `enable_turn_order_context=True`, the prompt includes the guard immediately after the TurnPipeline guard area and includes top-level `turn_order_context` through the existing serialized advice payload JSON. No compact summary is added. v7.7 does not connect UI flags, call Gemini, or implement resolved turn order.

v7.8 adds an offline advice fixture for the explicit turn-order context path. The fixture builds prompts with `_build_ui_selected_prompt(...)`, replaces `call_gemini` and `_log_advisor_call` with in-memory fakes, and verifies default-off, explicit-on, and `turn_pipeline` coexistence paths without provider calls. The mocked response keeps exact final order uncertain, treats Quick Claw activation as unresolved, and does not claim item consumption, post-turn HP, full simulation, or resolved speed ties.

v7.10 connects the existing default-off developer checkbox to the turn-order context path. The same checkbox now maps to both `enable_turn_pipeline=True` and `enable_turn_order_context=True` when checked, and both flags remain false when unchecked. The runtime source extraction for `turn_order_context` is intentionally narrow: selected active base Speed, user-confirmed final Speed when available for both sides, and unresolved Quick Claw candidate modifier context. Move priority remains unknown because current move metadata does not expose priority. If no valid source exists, `turn_order_context` is omitted rather than emitted as an empty context. This remains default-off, has no saved auto-enable behavior, does not add a second checkbox, and does not implement resolved order, speed tie resolution, RNG resolution, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference.

v7.11 verifies the UI checkbox path offline. The fixture instantiates `LLMAdvicePanel`, reads the checkbox state, maps it to `enable_turn_pipeline` and `enable_turn_order_context`, and runs `run_ui_selected_advice(...)` with `call_gemini` and `_log_advisor_call` monkeypatched. The unchecked path omits both optional contexts and both guards. The checked path includes both contexts and both guards when source context exists. Checkbox toggling alone emits no advice request and makes no provider call.

## Opponent Move Context Contract Draft

v8.1 defines a fixture-level payload contract for a future optional top-level `opponent_move_context` section. No runtime helper, payload adapter, prompt integration, or UI behavior change is added in v8.1.

The draft context is limited and source-bound:

- `kind` must be `opponent_move_context`
- `confidence` may be `limited` or `unknown`
- `selected_opponent_move.status` may be `unknown` or `explicit`
- `known_opponent_moves[*].source` must be trusted, such as `user_confirmed`, `visible_ui`, or `explicit_input`
- `candidate_moves[*]` must remain unconfirmed and unselected
- `priority_move_candidates[*]` must remain unconfirmed and unselected
- `unsupported` must include hidden moveset inference, opponent set inference, selected opponent move inference, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, RNG resolution, and full turn resolution
- `safety_notes` must state that candidate moves are not confirmed selected moves

The context must not include fields that imply hidden inference or resolved outcomes, including `inferred_moveset`, `predicted_move`, `likely_move`, `will_use`, `usage_rate_guess`, `meta_set`, `EVs`, `IVs`, `nature`, `hidden_item`, `post_turn_hp`, `item_consumed`, `rng_resolved`, or `speed_tie_resolved`.

Allowed move metadata fields are:

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

Prompt safety wording for future integration:

- Opponent move context is based only on explicitly known or visible data.
- Do not infer hidden movesets.
- Do not treat candidate moves as confirmed selected moves.
- Do not infer the opponent's selected move unless explicitly provided.
- Do not infer EVs, IVs, nature, hidden item, weather, terrain, or boosts unless explicitly provided.

v8.2 adds `llm.advisor_opponent_move_context.build_opponent_move_context(...)` as a standalone helper for this contract. It accepts caller-provided `known_moves`, `candidate_moves`, and optional `selected_opponent_move`. Trusted known moves are normalized with `confirmed=True`; unconfirmed candidates are normalized with `confirmed=False` and `selected=False`; positive-priority candidates are copied into `priority_move_candidates` without becoming selected moves. Unsafe candidate semantics such as `confirmed=True`, `selected=True`, `will_use=True`, or `likely_selected=True` are omitted from helper output. Explicit selected moves require trusted source, `move_id`, and `name`; inferred, predicted, or likely selected moves are rejected. The helper does not generate moves from species/common sets/meta data and is not connected to the payload adapter, prompt, UI, Gemini, or full Turn Engine path.

v8.3 adds an explicit/default-off payload adapter for this contract. `build_ui_advice_payload(..., opponent_move_context=..., enable_opponent_move_context=True)` may insert top-level `opponent_move_context` after validating the v8.1 contract. Omitted or disabled `enable_opponent_move_context` preserves the previous payload shape, and `enable_opponent_move_context=True` with no supplied context also preserves the previous shape. A valid but empty helper context is omitted. Invalid contexts raise `ValueError`. The adapter rejects forbidden hidden-inference/resolved-outcome fields recursively and keeps candidate moves / priority candidates unconfirmed and unselected. `opponent_move_context` coexists with optional `turn_pipeline` and `turn_order_context`; no optional field overwrites the other. v8.3 does not add prompt guard, prompt integration, UI/source extraction, Gemini calls, selected move inference, hidden moveset inference, or full Turn Engine behavior.

v8.4 adds `_build_opponent_move_context_prompt_guard(payload)` and wires it into `_build_ui_selected_prompt(...)` after the `turn_order_context` guard. The guard is emitted only when top-level `opponent_move_context` is present. It says the context is based only on explicitly known or visible opponent move data, known moves are not necessarily the selected move unless `selected_opponent_move` is explicit, candidate moves are not confirmed moves or confirmed selected moves, hidden movesets / opponent sets / selected move must not be inferred, and EV/IV/nature, hidden item, weather, terrain, boosts, RNG results, item consumption, and post-turn HP must not be inferred unless explicitly provided. v8.4 does not add UI/source extraction or Gemini calls.

v9.1 connects `opponent_move_context` to the existing default-off limited-context UI developer checkbox. The same checkbox now maps to `enable_turn_pipeline=True`, `enable_turn_order_context=True`, and `enable_opponent_move_context=True` when checked; unchecked keeps all three false. Runtime source extraction reads only existing `opponent_moves` data from the UI-selected advice payload. UI-visible opponent move slots are converted into `visible_ui` candidate moves, Champions movepool entries remain `champions_movepool` candidate moves, candidate moves remain `confirmed=false` and `selected=false`, and `selected_opponent_move` remains unknown. Empty context is omitted. v9.1 does not add a new checkbox, does not persist auto-enable state, does not call Gemini or Vertex AI, and does not infer hidden movesets, opponent sets, selected moves, species/common-set/meta moves, EV/IV/nature, hidden items, weather, terrain, boosts, RNG, item consumption, post-turn HP, or full Turn Engine state.

v9.2 adds focused offline E2E coverage for the existing limited-context checkbox path. `tests/test_ui_turn_pipeline_flag_flow.py` verifies the checkbox defaults unchecked, toggling alone does not emit an advice request or call the provider, the unchecked advice path omits all three optional contexts and prompt guards, and the checked path includes `turn_pipeline`, `turn_order_context`, and `opponent_move_context` together when source data exists. The same fixture verifies UI-visible opponent moves remain `visible_ui` candidates, `known_opponent_moves` stays empty, candidates remain `confirmed=false` and `selected=false`, and `selected_opponent_move` remains unknown. A no-opponent-source path verifies `opponent_move_context` is omitted while the other checked contexts may still appear. v9.2 uses mocked `call_gemini` only and does not change production payload filtering, damage behavior, UI defaults, provider behavior, or inference boundaries.

v9.3 polishes the existing limited-context checkbox copy without changing behavior. The label is `제한 컨텍스트 포함`; the tooltip says the checkbox includes turn event candidates, turn-order helper context, and UI-visible opponent move candidates, while clarifying that the information is not a final turn result and that opponent move candidates are not confirmed moves. The status copy says the limited context is on and remains non-final. Tests lock these copy anchors and forbid wording that would imply confirmed turn result, confirmed move order, opponent selected move inference, hidden moveset inference, Quick Claw activation resolution, item consumption, or post-turn HP resolution. v9.3 does not call Gemini or Vertex AI and does not change payload filtering, damage behavior, UI defaults, checkbox wiring, or inference boundaries.

v9.4 closes the v9.0-v9.3 Opponent Move UI Integration phase as documentation only. The closed behavior is: the existing checkbox stays default-off; off omits `turn_pipeline`, `turn_order_context`, `opponent_move_context`, and related guards; on enables all three limited-context flags while each context still requires valid source data; UI-visible opponent moves become `visible_ui` candidates, not `known_opponent_moves`; candidates remain `confirmed=false` and `selected=false`; `selected_opponent_move` remains unknown unless a future explicit trusted source is added. The closure records that no actual UI-path Gemini smoke, `battle_state_context`, full Turn Engine, hidden moveset inference, opponent set inference, selected opponent move inference, RNG resolution, item consumption, post-turn HP update, damage formula change, `ko_context` change, or payload filtering change is included. The recommended next phase is v10.0 Battle State Context Design.

v10.0 designs a future optional top-level `battle_state_context` without implementation. The proposed shape is a visible/explicit state snapshot with `kind`, `confidence`, `self_active`, `opponent_active`, `field`, `known_conditions`, `unsupported`, and `safety_notes`. Known fields should carry source-tagged envelopes such as `visible_ui`, `explicit_input`, `user_confirmed`, or `calculated_from_visible`; unknown fields should remain explicit unknown values. The design forbids hidden item, EV/IV/nature, unobserved boost/status, weather/terrain, hazards/screens, room, RNG, item consumption, post-turn HP, selected opponent move, opponent set, hidden moveset, and damage reverse inference. It also states that `damage_estimate`, `ko_context`, `turn_pipeline`, `turn_order_context`, and `opponent_move_context` are context-only references and must not generate hidden battle state. v10.0 does not add payload adapter support, prompt guard code, UI extraction, provider calls, or production behavior. The recommended next phase is v10.1 Battle State Context Payload Contract.

v10.1 locks the future `battle_state_context` contract at fixture/test level only. `tests/test_advisor_payload_contract.py` defines a sample context with `kind`, initial `confidence` values limited to `unknown` or `limited`, required `self_active`, `opponent_active`, `field`, `known_conditions`, `unsupported`, and `safety_notes` sections, explicit unknown field envelopes, allowed source validation, forbidden source rejection, recursive forbidden hidden/resolved field rejection, and relationship boundary anchors. `partial` and `explicit` confidence remain future-only. The contract records that `damage_estimate`, `ko_context`, `turn_pipeline`, `turn_order_context`, and `opponent_move_context` must not create hidden battle state or resolved outcomes. v10.1 does not add a production helper, payload adapter, prompt guard, UI/source integration, provider call, or runtime `battle_state_context` behavior.

v10.2 adds a standalone `llm.advisor_battle_state_context.build_battle_state_context(...)` helper that normalizes caller-provided visible or explicit battle-state facts into the v10.1 shape. Empty or fully rejected input returns `confidence == "unknown"`; accepted visible or explicit source data returns `confidence == "limited"`; the helper never emits `partial` or `explicit`. Allowed sources are `visible_ui`, `explicit_input`, `user_confirmed`, and `calculated_from_visible`; forbidden sources such as `species_common_set`, `usage_based_guess`, `meta_inferred`, `hidden_state_guess`, and `damage_reverse_inference` become explicit unknowns or are omitted from list-style conditions. The helper always emits active-side and field keys, preserves unknown fields as `{"known": false, "value": "unknown"}`, removes forbidden hidden/resolved fields recursively, and does not use `damage_estimate`, `ko_context`, `turn_pipeline`, `turn_order_context`, or `opponent_move_context` as hidden-state or resolved-outcome sources. v10.2 does not add payload adapter support, prompt guard code, UI/source integration, provider calls, or full Turn Engine behavior.

v10.3 adds explicit/default-off payload adapter support for caller-provided `battle_state_context`. `build_ui_advice_payload(..., battle_state_context=..., enable_battle_state_context=True)` inserts a valid non-empty top-level `battle_state_context`; default, disabled, `None`, `{}`, and unknown-only helper outputs are omitted. The adapter validates the v10.1 top-level shape, allows only `unknown` / `limited` confidence, requires active-side and field sections, requires unsupported boundaries and safety notes, rejects forbidden sources, and rejects hidden/resolved fields recursively. It preserves helper output shape and coexists with `turn_pipeline`, `turn_order_context`, and `opponent_move_context` without overwriting them. The adapter does not generate battle state from `damage_estimate`, `ko_context`, `turn_pipeline`, `turn_order_context`, or `opponent_move_context`. v10.3 does not add prompt guard code, UI/source integration, provider calls, automatic battle-state generation, hidden-state inference, or full Turn Engine behavior.

v10.4 adds `_build_battle_state_context_prompt_guard(...)` and wires it into `_build_ui_selected_prompt(...)` after existing optional context guards. Prompts without top-level `battle_state_context` omit both the serialized context and the guard. Prompts with explicit valid `battle_state_context` include the serialized context and guard wording that unknown fields must remain unknown; hidden item, EV/IV/nature, boosts, status, weather, terrain, hazards, screens, and room must not be inferred; `damage_estimate` and `ko_context` must not be used for hidden-state reverse inference; `battle_state_context` is not a resolved turn simulation; and post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation, and full turn outcome must not be claimed. v10.4 does not add UI/source integration, UI checkbox behavior changes, provider calls, hidden-state inference, damage reverse inference, or full Turn Engine behavior.

v10.5 adds an offline mocked advice fixture for explicit `battle_state_context`. The fixture monkeypatches `call_gemini` and `_log_advisor_call`, captures default, explicit battle-state, and coexistence prompts, verifies top-level `battle_state_context` survives to the prompt payload, checks the v10.4 guard anchors, verifies recursive forbidden source/field absence, and confirms coexistence with `turn_pipeline`, `turn_order_context`, and `opponent_move_context`. Mocked responses avoid hidden-state certainty and resolved-outcome claims. No actual Gemini, Vertex AI, network, UI/source integration, UI checkbox behavior change, hidden-state inference, damage reverse inference, or full Turn Engine behavior is added.

v10.6 inventories current UI sources for future `battle_state_context` integration without changing the runtime contract. The current UI-selected advice path already exposes active self/opponent species and HP percent as visible UI facts, and item profiles as explicit/user-confirmed or unknown/default item state. These sources require a future source adapter before they feed the v10.2 helper. Status, boosts, weather, terrain, screens, hazards, room effects, and general known conditions have no current explicit UI source and must remain unknown. Existing damage, KO, turn pipeline, turn order, and opponent move contexts remain separate bounded contexts and must not be copied into battle state as hidden-state or resolved-outcome evidence.

v10.7 designs future UI integration for `battle_state_context` without changing the runtime contract. The existing limited-context checkbox should remain default-off; unchecked should omit `battle_state_context`, and checked should enable `enable_battle_state_context=True` alongside `turn_pipeline`, `turn_order_context`, and `opponent_move_context`. The first source adapter should use only visible self/opponent species and HP percent from UI-selected state. Status, boosts, item, field state, and `known_conditions` remain unknown for the first integration. User-confirmed item mapping is deferred to a separate design because it overlaps with existing item profiles and hidden/confirmed item boundaries.

v10.8 adds `build_battle_state_context_from_ui_selected_state(...)` as a narrow UI-selected source adapter. It reads only `pokemon.my_active.name_en`, `pokemon.my_active.hp_percent`, `pokemon.opponent_active.name_en`, and `pokemon.opponent_active.hp_percent`, converts accepted values into `visible_ui` source envelopes, and returns the existing `build_battle_state_context(...)` output. Missing or malformed species/HP values become explicit unknowns. The adapter does not read item profiles, damage estimates, KO context, turn pipeline, turn order context, opponent move context, common sets, meta data, or sample assumptions. v10.8 does not connect the existing checkbox, change payload builder call flow, change prompt guards, call providers, infer hidden state, or implement full Turn Engine behavior.

v10.9 connects the existing limited-context checkbox path to `battle_state_context`. The same checkbox remains default-off and now maps checked state to `enable_battle_state_context=True` alongside `turn_pipeline`, `turn_order_context`, and `opponent_move_context`. When enabled and no explicit battle-state context is supplied, `_build_ui_selected_prompt(...)` builds one through `build_battle_state_context_from_ui_selected_state(...)`. The resulting context includes only visible self/opponent species and HP percent; status, boosts, item, field state, and `known_conditions` remain unknown. The existing v10.4 prompt guard is reused. v10.9 does not add a new checkbox, change UI copy, change prompt guard wording, change the payload adapter contract, call providers, infer hidden state, or implement full Turn Engine behavior.

v10.10 updates only the existing limited-context checkbox copy. The label remains `제한 컨텍스트 포함`; tooltip/status copy now also says the checkbox includes the current Pokemon/HP snapshot. The copy keeps the non-final boundary and explicitly avoids selected-move, hidden item/status/boost/field inference, post-turn HP, item consumption, RNG, speed tie, Quick Claw activation, and full outcome certainty. v10.10 does not change payload shape, checkbox behavior, prompt guard wording, source adapter behavior, provider behavior, or inference boundaries.

v10.11 adds an offline UI-selected smoke for the existing limited-context checkbox path. With the checkbox off, the captured prompt payload omits `battle_state_context` and the battle-state guard. With the checkbox on, the captured prompt payload includes top-level `battle_state_context` alongside `turn_pipeline`, `turn_order_context`, and `opponent_move_context`; self/opponent species and HP percent remain `visible_ui`, while status, boosts, item, field state, and `known_conditions` remain unknown or `[]`. The smoke uses monkeypatched `call_gemini` and `_log_advisor_call` only. v10.11 does not change payload shape, UI behavior, UI copy, prompt guard wording, source adapter behavior, provider behavior, or inference boundaries.

v10.12 closes the battle-state UI phase without changing the payload contract. The supported UI path remains the existing limited-context checkbox: off omits `battle_state_context`, on enables it with the other limited contexts and extracts only visible self/opponent species plus HP percent. All status, boost, item, field, and known-condition fields remain unknown or `[]`. Actual Gemini smoke has not been run for this UI path; the next recommended step is a controlled smoke design before any provider call.

v11.0 designs the future controlled Battle State UI Gemini smoke without changing the payload contract or executing a provider call. The future smoke should use the existing limited-context checkbox-on UI-selected path, require top-level `battle_state_context` with visible self/opponent species and HP percent only, require unknown status/boost/item/field fields and `known_conditions=[]`, and require the existing battle-state prompt guard. Any actual call is deferred to v11.1 and requires explicit T1 approval, exactly one Gemini call, and zero retries.

v8.5 adds an offline mocked advice fixture for the explicit `opponent_move_context` path. The fixture monkeypatches `call_gemini` and `_log_advisor_call`, verifies default-off omission, explicit prompt guard and serialized payload context, and coexistence with `turn_pipeline` plus `turn_order_context`. The mocked response says the known Thunderbolt is user-confirmed known move data, selected move is unknown, and Quick Attack is only a candidate that must not be treated as confirmed or selected. The response avoids selected-move, hidden moveset, hidden item, EV/IV/nature, RNG, item consumption, and post-turn HP inference. No actual Gemini call or UI/source extraction is added.

## Current Payload Shape

Top-level sections:

- `scenario`
- optional `turn_snapshot`
- optional `turn_pipeline`
- optional `turn_order_context`
- optional `opponent_move_context`
- `pokemon`
- `stat_profiles`
- `item_profiles`
- `opponent_assumptions`
- `speed_context`
- `moves`
- `opponent_moves`

`scenario` contains:

- `mode`: currently `ui-selected-pokemon-v0.18`
- `format_note`: explains that this is selected Pokemon identity plus default-assumption user-confirmed move estimates and opponent move context, not full battle state
- `known_limitations`: guardrails the prompt and UI must preserve

`pokemon.my_active` and `pokemon.opponent_active` contain:

- `slot_index`
- `name_en`
- `name_ko`
- `types`
- `types_ko`
- `base_stats`
- `abilities`
- `abilities_ko`
- `hp_percent`
- `selected_move_index`

`stat_profiles` contains:

- `my_active`
- `opponent_active`

Each active stat profile contains:

- `status`: `default_assumption` or `user_confirmed_final_stats`
- `source`: `system_default` or `user_input`
- `level`
- `final_stats`
- `evs`
- `ivs`
- `nature`
- `item`
- `notes`

`item_profiles` contains:

- `my_active`
- `opponent_active`

Each active item profile contains:

- `status`: `unknown`, `none`, `system_default_none`, or `user_confirmed`
- `source`
- `item_id`
- `name_en`
- `name_ko`
- `effects_scope`
- `damage_modifier_status`
- `notes`

In v0.23 the UI can emit `system_default_none`, `unknown`, `none`, or `user_confirmed` item profiles for active Pokemon. My active defaults to `system_default_none` for compatibility with the previous no-item calculation assumption. Opponent active defaults to `unknown` unless T1 confirms no item or selects a legal item from the repository-backed selector.

`opponent_assumptions` contains possible opponent sample profiles for the active opponent species. It is context-only in v0.38 and is not confirmed battle information.

When samples are available, `opponent_assumptions` contains:

- `mode`: `multi_sample_assumption_v0.38`
- `schema_version`: current payload shape, currently `opponent_assumptions_v0.47`
- `metadata_version`: current `possible_samples` metadata shape, currently `minimal_metadata_v1`
- `available`: `true`
- `scope`: `opponent_active`
- `is_confirmed_information`: always `false`
- `calculation_usage`: `context_only`
- `payload_features`: developer/debug feature flags
- `opponent_active.species_id`
- `opponent_active.known_status`: currently `not_confirmed`
- `opponent_active.is_user_confirmed`: `false`
- `opponent_active.user_confirmed_fields`: currently `{}`
- `opponent_active.possible_samples`
- `opponent_active.samples_meta`
- `opponent_active.observation_history`: currently `[]`
- `opponent_active.update_policy.mode`: `static`
- `limitations`

`mode` is a historical behavior label. It remains `multi_sample_assumption_v0.38` for compatibility. `schema_version` describes the current payload shape, and `metadata_version` describes the minimal metadata shape inside `possible_samples`. These version fields are additive developer/contract metadata. The LLM should not mention version fields in user-facing battle advice.

`payload_features` currently contains:

- `possible_samples`: `true`
- `minimal_metadata`: `true`
- `debug_summary_supported`: `true`
- `full_stats_excluded`: `true`
- `damage_speed_integration`: `false`

Each `possible_samples` entry contains:

- `sample_id`
- `species_id`
- `label_en`
- `label_ko`
- `source`: `sample_assumed`
- `source_type`
- `confidence`
- `prior_probability`: currently `null`
- `prior_probability_type`: `not_available`
- `evidence_basis`
- `is_user_confirmed`: `false`
- `possible_item`
- `role`: estimated sample role when available
- `archetype_id`: estimated sample archetype label when available
- `possible_items`: possible item assumptions, not confirmed held items
- `calculation_usage`: `context_only`
- `limitations`

`possible_samples` deliberately excludes full stats, SP distribution, source URL, source note, long reviewer notes, and full source metadata. Role, archetype, and possible item metadata are context-only labels. They must not be treated as confirmed opponent role, confirmed opponent item, damage calculation input, or Speed calculation input.

`samples_meta` contains:

- `total_known_archetypes`
- `included_top_k`
- `default_top_k`: `3`
- `coverage_probability`: currently `null`
- `coverage_probability_type`: `not_available`
- `omitted_archetypes_note`

When samples are unavailable, `opponent_assumptions.available` is `false` and `reason` is one of:

- `no_samples_for_species`
- `opponent_active_missing`
- `repository_unavailable`

The LLM must not invent possible samples when `available` is `false`.

`opponent_assumptions.calculation_usage` is `context_only` in v0.38:

- possible samples are not used by `damage_estimate`
- possible samples are not used by `speed_context`
- possible samples do not provide KO, OHKO, 2HKO, survival, or final turn order
- `prior_probability: null` means the prior is unavailable, not zero probability
- Top-K omission does not mean omitted archetypes are impossible

`speed_context` contains raw and supported effective Speed comparison metadata. It is not final turn order.

When both active Pokemon have user-confirmed final stats with `spe`, `speed_context` contains:

- `mode`: `choice_scarf_effective_speed_v0.30`
- `available`: `true`
- `my_active.raw_speed`
- `my_active.effective_speed`
- `my_active.source`: `user_confirmed_final_stats`
- `my_active.is_user_confirmed`
- `my_active.speed_modifiers`
- `opponent_active.raw_speed`
- `opponent_active.effective_speed`
- `opponent_active.source`: `user_confirmed_final_stats`
- `opponent_active.is_user_confirmed`
- `opponent_active.speed_modifiers`
- `comparison.raw_speed_relation`: `my_active_faster`, `opponent_active_faster`, or `speed_tie`
- `comparison.raw_speed_margin`
- `comparison.raw_speed_tie`
- `comparison.effective_speed_relation`
- `comparison.effective_speed_margin`
- `comparison.effective_speed_tie`
- `comparison.speed_margin`: raw Speed margin compatibility alias
- `comparison.speed_tie`: raw Speed tie compatibility alias
- `limitations`
- `is_final_turn_order`: always `false`

When either active Pokemon is missing user-confirmed final Speed, `speed_context` contains:

- `mode`: `choice_scarf_effective_speed_v0.30`
- `available`: `false`
- `reason`: `insufficient_confirmed_final_stats`
- `limitations`
- `is_final_turn_order`: always `false`

Default Speed fallback is not used in v0.30.

`moves` contains:

- `my_selected_move_index`
- `my_available_moves`
- `my_selected_move`
- `opponent_available_moves`
- `opponent_selected_move`
- `opponent_selected_move_index`
- `move_data_status`
- `notes`

`moves.opponent_available_moves` remains a legacy compatibility field and is empty in v0.18. New opponent move semantics live in `opponent_moves`.

`opponent_moves` contains:

- `status`
- `known_moves`
- `candidate_moves`
- `candidate_moves_limit`
- `candidate_source_status`
- `unknown_moves`
- `limitations`

User-confirmed move entries contain:

- `slot`
- `move_id`
- `name_en`
- `name_ko`
- `type`
- `category`
- `power`
- `accuracy`
- `pp`
- `damage_estimate` on each user-confirmed entry in `moves.my_available_moves`
- `damage_estimate` on `moves.my_selected_move`
- `damage_estimate` on each user-confirmed entry in `opponent_moves.known_moves`

Each move `damage_estimate` contains:

- `status`
- `scope`
- `is_final_battle_damage`
- `assumption_profile`
- `item_effects`
- `target` when the estimate is for opponent known move damage against `my_active`
- `selected_move_id` when available
- `damage_range` when available
- `percent_range` when available
- `type_effectiveness` when available
- `rolls` when available
- `assumptions`
- `derived_stats` when available
- `limitations`

## Opponent Move Semantics

Opponent move data is split into separate categories:

- `known_moves`: moves the user directly confirmed in the opponent Q/W/E/R slots. These are the only confirmed opponent moves.
- `candidate_moves`: possible moves from the Serebii-derived Champions movepool cache. These include `confidence: "possible_not_confirmed"` and are not the opponent's known moveset.
- `unknown_moves`: explicit state for missing or partial opponent move information.

Opponent candidate moves are capped by `candidate_moves_limit`. Known opponent moves may include `damage_estimate` in v0.18 when they are user-confirmed moves. Candidate moves do not include `damage_estimate` in v0.18.
Candidate moves may be mentioned as possible threats only when clearly labeled as unconfirmed. The advisor should use `my_available_moves[*].damage_estimate` to compare the user's own move options.
Opponent known move damage estimates use `target: "my_active"` and are rough threat references only.

## Item Semantics

Item state is separate from stat state:

- `unknown`: the item is not known.
- `none`: the user confirmed no held item.
- `system_default_none`: the calculation assumes no held item by default.
- `user_confirmed`: the user or a test/helper payload supplied an item.

`unknown` and `none` must not be treated as the same thing.

The normal v0.23 selector is legal-item based. Legal item and modeled item are separate concepts:

- `legal_but_not_modeled`: selectable as user-confirmed item information, but the item effect does not change damage.
- `legal_and_damage_supported`: recognized by the legal fixture as having local damage support, but damage still counts the item only when `damage_estimate.item_effects` marks the effect as `applied`.
- `damage_supported_but_not_champions_legal`: debug/test only and not exposed in the normal selector.

The legacy damage-test subset remains available to tests/helpers, not the normal legal selector:

- `choice-band`: physical move damage modifier only
- `choice-specs`: special move damage modifier only
- `life-orb`: damage modifier only
- `muscle-band`: physical move damage modifier only
- `wise-glasses`: special move damage modifier only

Legal catalog-backed type boosting items may apply as attacker-side damage modifiers:

- when `item_profiles.<attacker>.status` is `user_confirmed`
- when the item is a Champions legal `type_boosting_item`
- when a local catalog-backed damage modifier exists
- when the move type matches the item's boosted type

When applied, these items use a `1.2x` damage modifier and `damage_estimate.item_effects.attacker_item.status` is `applied`.
When the move type does not match the boosted type, `status` is `not_applicable` and damage is unchanged.
When a legal item such as Fairy Feather has no catalog-backed damage modifier, `status` is `unsupported_item` and damage is unchanged.

Excluded from v0.30 item application:

- Expert Belt
- Assault Vest
- Choice lock
- Life Orb recoil
- candidate move damage

Legal item modeling examples:

- Choice Scarf: selectable; its supported speed modifier may be applied in `speed_context` when user-confirmed, but speed order and Choice Scarf choice lock are not modeled.
- Focus Sash: selectable; its limited survival context may be included only when user-confirmed and full HP. It is not damage reduction and does not change raw damage estimates.
- Focus Band: selectable; its limited survival context may be included only when user-confirmed and the raw incoming hit is potentially lethal. Survival is not guaranteed, and activation probability is not calculated.
- Leftovers / Sitrus Berry: selectable; limited recovery context may be included only when user-confirmed and max HP is available. Exact turn sequencing and item consumption are not modeled.
- Quick Claw: selectable; limited `speed_order_context` may be included only when user-confirmed and Champions legal. Activation probability and final move order are not calculated.
- Light Ball: selectable; limited `species_stat_item_context` may be included only when user-confirmed, Champions legal, local species-stat metadata exists, and the holder species is Pikachu. In v3.1, eligible Pikachu + Light Ball damage estimates apply the supported species-stat modifier in `damage_estimate.item_effects`; the context explains that applied modifier.

### Legal Item Gate

User-facing modeled item contexts require Champions legal item coverage from `data/static/champions_legal_items.json`.

The following are not legal coverage sources by themselves:

- `data/static/items.json`
- `data/static/items_damage.json`
- context helper existence
- engine/debug metadata
- `data/static/charge_moves.json`

If an item is user-confirmed but absent from the Champions legal item fixture, the payload must not emit a modeled item context for that item. The stable unavailable reason is `blocked_by_legal_item_coverage`.

Loaded Dice is currently implemented as future-only multi-hit context support but is blocked from user-facing modeled context until Loaded Dice legal coverage is confirmed. Power Herb remains blocked; `charge_moves.json` is move metadata and does not establish Power Herb legality.

Blocked or future-only item reasons are developer/debug/contract metadata, not normal user-facing advice content. When an item is blocked by legal coverage, the LLM should not include the blocked item effect in the default recommendation text, mention the blocked item name, say "user-confirmed Loaded Dice," say "Power Herb," say "Loaded Dice is not modeled," say "Power Herb is not modeled," or say the blocked item effect is not included. It should also avoid generic substitutes such as "the user-confirmed item effect," "held item effect," "selected item effect," or "item-based limitation." The default response should not mention that a blocked item exists by saying its effect is absent, ignored, unavailable, excluded, unsupported, or outside the estimate. The response must not imply blocked or future-only items are available in Champions.

If the user explicitly asks about a blocked item, the LLM may give only a short explanation that Champions legal coverage is not confirmed, so the item effect is not reflected in advice. It must not calculate, strategize around, or imply availability for the blocked item.

`damage_estimate.item_effects` is the source of truth for whether an item effect was applied to a specific calculation.

When `damage_estimate.item_effects.attacker_item.status` is `applied`, the LLM should explicitly mention that the supported item damage modifier is included in that estimate. It should describe the number as being calculated under the stated assumptions plus the supported item modifier, not as only default assumptions. Non-damage item effects remain unmodeled.

If Life Orb is applied, the LLM should say the damage modifier is applied and Life Orb recoil is not modeled. If Choice Scarf, Choice Band, or Choice Specs is applied, the LLM should say the relevant supported effect is applied and choice lock is not modeled.

For type boosting items, the LLM should say the damage modifier is included only when `damage_estimate.item_effects.attacker_item.status` is `applied`. It must not say the item boosted damage when the move type does not match, when the item is unsupported, or merely because the item is legal. Fairy Feather should be described as legal but not damage-modeled until a catalog-backed modifier exists.

## Type Boost Context Semantics

`type_boost_context` is an additive limited context for user-confirmed Champions legal type-boosting items whose catalog metadata supports a matching move type. It is never nested inside `damage_estimate` or `ko_context`.

The context is explanatory: it surfaces the same supported item relationship that `damage_estimate.item_effects` already uses when applicable. It does not create a new damage formula path, does not recalculate raw damage rolls, and does not add type-boost-adjusted KO/OHKO/2HKO context.

Available type boost context requires:

- attacker item profile must be `status: user_confirmed`
- item must pass Champions legal item coverage
- item category must be `type_boosting_item`
- item effect support status must be `legal_and_damage_supported`
- item must exist in `items_damage.json` `type_boost_items`
- move type must be known
- move type must match the item boosted type

The first supported scope is the legal damage-supported type-boosting item set:

- `black-belt`
- `black-glasses`
- `charcoal`
- `dragon-fang`
- `hard-stone`
- `magnet`
- `metal-coat`
- `miracle-seed`
- `mystic-water`
- `never-melt-ice`
- `poison-barb`
- `sharp-beak`
- `silk-scarf`
- `silver-powder`
- `soft-sand`
- `spell-tag`
- `twisted-spoon`

Excluded items:

- `fairy-feather`: Champions legal, but no catalog-backed damage metadata/helper support yet.
- `odd-incense`, `rose-incense`, `sea-incense`, `wave-incense`: present in `items_damage.json`, but not confirmed as Champions legal items in `champions_legal_items.json`.

Available context may include:

- `mode`: `limited_type_boost_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: the item id
- `item.status`: `user_confirmed`
- `item.legal_status`: `legal_modeled`
- `type_boost_effect.boosted_type`: boosted type from `items_damage.json`
- `type_boost_effect.move_type`: move type
- `type_boost_effect.effect_label`: `may_boost_matching_type_move`
- `type_boost_effect.formula_label`: `type_boost_limited_damage_modifier_context`
- `type_boost_effect.damage_estimate_item_effect_status`: the related `damage_estimate.item_effects.attacker_item.status`
- `type_boost_effect.raw_damage_rolls_changed`: `false`
- `type_boost_effect.ko_context_changed`: `false`
- `type_boost_effect.type_boost_adjusted_ko_integrated`: `false`
- `type_boost_effect.type_boost_adjusted_ohko_2hko_integrated`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_type_boost_item`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `not_type_boosting_item`
- `type_boost_metadata_missing`
- `boosted_type_missing`
- `move_type_missing`
- `move_type_does_not_match_boosted_type`
- `damage_estimate_missing`

When `type_boost_context.available` is true, the note should stay concise. The LLM may say the user-confirmed item may boost matching-type moves and that the damage estimate may already include the supported item modifier when applicable. It should not say the context is final battle truth.

The LLM must not say:

- "This guarantees KO."
- "This secures the KO."
- "Boosted damage proves the KO."
- "This is final damage."
- "The type-boost-adjusted KO chance is 70%."

If `type_boost_context.available` is false in the enriched/debug payload, the default advice payload should omit `type_boost_context`. The unavailable reason is developer/debug/contract metadata only. The LLM should not mention the unavailable type-boost item name, effect, or reason in default advice unless the user explicitly asks about that item.

For non-Choice items such as Charcoal, Mystic Water, Black Belt, Metal Coat, Sharp Beak, Fairy Feather, Light Ball, Leftovers, Focus Sash, or Focus Band, the LLM must not say choice lock is not modeled. Choice lock is relevant only to Choice Scarf, Choice Band, and Choice Specs.

## Species Stat Item Context Semantics

`species_stat_item_context` is an additive limited context for species-specific stat items that already have local metadata and damage-helper support. It is never nested inside `damage_estimate` or `ko_context`.

In v3.1, modeled species-stat item context is limited to Light Ball:

- attacker item profile must be `status: user_confirmed`
- attacker item id must be `light-ball`
- attacker item must pass Champions legal item coverage
- `items_damage.json` must provide `species_stat_items.light-ball` metadata
- holder species must normalize to `pikachu`
- move must be a damaging move with physical or special category metadata

The context is a sibling explanation for an applied `damage_estimate.item_effects` modifier. `damage_estimate.item_effects` remains the source of truth for whether the supported Light Ball species-stat modifier was applied to a specific estimate. v3.1 does not change the core damage formula or Q12 constants, but eligible Pikachu + Light Ball estimates intentionally use adjusted attack or special attack for the advisor estimate, so raw damage rolls and the existing `ko_context` are based on those adjusted damage estimate rolls. The context does not infer exact EV/IV/nature-adjusted final stats and does not create final KO truth.

Available context may include:

- `mode`: `limited_species_stat_item_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: `light-ball`
- `item.status`: `user_confirmed`
- `item.legal_status`: `legal_modeled`
- `species_stat_effect.holder_species_id`: `pikachu`
- `species_stat_effect.supported_species`: `["pikachu"]`
- `species_stat_effect.boosted_stats`: stat ids from local metadata
- `species_stat_effect.effect_label`: `may_boost_pikachu_offensive_stats`
- `species_stat_effect.formula_label`: `species_stat_item_limited_modifier_context`
- `species_stat_effect.damage_estimate_item_effect_status`: the related `damage_estimate.item_effects.attacker_item.status`
- `species_stat_effect.raw_damage_rolls_changed`: `true`
- `species_stat_effect.ko_context_changed`: `true`
- `species_stat_effect.species_stat_adjusted_ko_integrated`: `true`
- `species_stat_effect.species_stat_adjusted_ohko_2hko_integrated`: `true`
- `species_stat_effect.final_stats_inferred`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `damage_estimate_missing`
- `move_category_missing_or_unsupported`
- `no_species_stat_item`
- `item_not_user_confirmed`
- `not_species_stat_item`
- `blocked_by_legal_item_coverage`
- `species_stat_metadata_missing`
- `supported_species_missing`
- `holder_species_missing`
- `holder_species_not_supported`
- `boosted_stats_missing`
- `species_stat_item_not_applied_to_damage_estimate`

When `species_stat_item_context.available` is true, the LLM should say Light Ball is a Pikachu-specific offensive item context applied in the damage estimate when `damage_estimate.item_effects` marks the supported modifier as applied. It should not say Light Ball is not included or not modeled when the available context is present. It also should not use generic no-item/default-assumption wording such as "no item effects", "without item effects", "assuming no item", "default no-item assumption", "item not included", "item not modeled", or "item not reflected". Describe the estimate as default assumptions plus the supported Light Ball modifier, not as a no-item estimate. It should not generalize Light Ball to non-Pikachu holders, and it should not treat the context as final stat truth or a final KO guarantee.

The LLM must not say:

- "Light Ball is not included."
- "Light Ball is not modeled."
- "No item effects are included."
- "Without item effects."
- "Assuming no item."
- "Default no-item assumption."
- "Item not reflected."
- "Light Ball guarantees KO."
- "Light Ball always doubles damage."
- "Confirmed OHKO because of Light Ball."
- "All Electric-type Pokemon benefit from Light Ball."
- "Light Ball works on any holder."
- "Final stats are fully known."
- "Exact EV/IV/nature-adjusted stats are known."

If `species_stat_item_context.available` is false in the enriched/debug payload, the default advice payload should omit `species_stat_item_context`. The unavailable reason is developer/debug/contract metadata only. The LLM should not mention Light Ball, non-Pikachu mismatch, unsupported reason, missing metadata, or not-modeled wording in default advice unless the user explicitly asks about that item.

## Survival Context Semantics

`survival_context` is an additive limited context next to a relevant `damage_estimate`. It does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, or item damage modifier math.

In v0.96, modeled survival contexts are limited Focus Sash and limited Focus Band context:

Shared rules:

- defender item profile must be `status: user_confirmed`
- defender item must pass Champions legal item coverage
- incoming raw damage must have `max >= current_hp` or an equivalent limited HP reference
- `min >= current_hp` is represented separately as `guaranteed_lethal_without_item`
- raw damage rolls are unchanged
- `ko_context` is unchanged
- KO/OHKO/2HKO estimates do not include survival item activation
- final survival probability is not calculated
- item consumption and turn sequencing are not modeled

Focus Sash-specific rules:

- defender item profile must be `status: user_confirmed`
- defender item id must be `focus-sash`
- defender HP must be full by exact HP or `hp_percent == 100`
- incoming damage must have `max >= current_hp`
- `min >= current_hp` is represented separately as `guaranteed_lethal_without_item`

Available Focus Sash context may include:

- `mode`: `limited_item_survival_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `focus-sash`
- `item.status`: `user_confirmed`
- `current_hp_is_full`: `true`
- `incoming_damage.could_be_lethal_without_item`
- `incoming_damage.guaranteed_lethal_without_item`
- `survival_effect.type`: `focus_sash`
- `survival_effect.may_survive_at_1_hp`: `true`
- `survival_effect.raw_damage_rolls_changed`: `false`
- `is_final_battle_truth`: `false`

Focus Band-specific rules:

- defender item id must be `focus-band`
- defender HP does not need to be full
- incoming raw damage must be potentially lethal without the item
- activation probability is not calculated
- final survival probability is not calculated
- Focus Band is not damage reduction and does not change KO probability

Available Focus Band context may include:

- `mode`: `limited_item_survival_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `focus-band`
- `item.status`: `user_confirmed`
- `incoming_damage.could_be_lethal_without_item`
- `incoming_damage.guaranteed_lethal_without_item`
- `incoming_damage.hp_reference_source`
- `survival_effect.type`: `focus_band`
- `survival_effect.effect_label`: `may_occasionally_survive_lethal_hit`
- `survival_effect.survival_is_not_guaranteed`: `true`
- `survival_effect.activation_probability_calculated`: `false`
- `survival_effect.final_survival_probability_integrated`: `false`
- `survival_effect.raw_damage_rolls_changed`: `false`
- `survival_effect.ko_context_changed`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_focus_sash`
- `item_not_user_confirmed`
- `hp_not_full`
- `hp_unknown`
- `damage_not_lethal`
- `multi_hit_not_supported`
- `damage_estimate_missing`
- `defender_max_hp_missing`
- `unsupported_turn_engine_required`

The LLM may say:

- "Focus Sash may allow survival at 1 HP if the Pokemon is at full HP, but this is limited context and does not change the raw damage estimate."
- "Without considering Focus Sash, the damage range could be lethal; with a user-confirmed Focus Sash and full HP, survival at 1 HP is possible under limited assumptions."
- "Focus Sash survival is limited context; multi-hit moves, hazards, chip damage, and exact turn sequencing are not modeled."
- "This Focus Sash note assumes single-hit damage from full HP; multi-hit, hazards, chip damage, and turn sequencing are not modeled."
- "Focus Band may occasionally let the Pokemon survive an otherwise lethal hit, but survival is not guaranteed."
- "Raw damage and KO estimates do not include Focus Band activation."
- "Focus Band activation probability and final survival probability are not calculated."

When `survival_context.available` is `true`, the LLM should include one concise limitation sentence. The limitation should stay short and should not become longer than the recommendation.

If `survival_context.available` is false, or no `survival_context` is present for a move, the LLM should not invent Focus Sash or Focus Band survival, should not mention unavailable reasons, and should not force the survival limitation sentence. The default advice payload should omit unavailable `survival_context`; enriched/debug payload may retain the reason.

The LLM must not say:

- "Focus Sash reduces the damage."
- "Focus Band reduces the damage."
- "The Pokemon definitely survives."
- "The Pokemon will survive."
- "Focus Sash guarantees survival in this turn."
- "Focus Band guarantees survival in this turn."
- "Focus Band confirms survival."
- "Focus Band means it is safe to take the hit."
- "Focus Band activation is included in KO chance."
- "The final survival probability is 10%."
- "Focus Sash applies when the item is unknown or unconfirmed."
- "Focus Band applies when the item is unknown or unconfirmed."
- "Focus Sash handles multi-hit moves, hazards, residual damage, weather/status chip, ability interactions, or exact turn sequencing."

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `type_boost_context`, `species_stat_item_context`, `speed_order_context`, `resist_berry_context`, `chilan_berry_context`, or `ko_context`.

## Recovery Context Semantics

`recovery_context` is an additive limited context next to a relevant `damage_estimate`. It does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, or item damage modifier math.

`ko_context` is unchanged by `recovery_context`. KO/OHKO/2HKO estimates do not include recovery. The LLM may mention recovery as a follow-up limitation, but it must not say the raw KO chance already includes Sitrus Berry or Leftovers.

In v0.60, the only modeled recovery context is limited Sitrus Berry / Leftovers context:

- defender item profile must be `status: user_confirmed`
- defender item id must be `sitrus-berry` or `leftovers`
- defender max HP must be available
- recovery amount is max-HP formula based
- exact activation timing is not final battle truth
- item consumption is not tracked

Available Sitrus Berry context may include:

- `mode`: `limited_item_recovery_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `sitrus-berry`
- `item.status`: `user_confirmed`
- `recovery_effect.type`: `sitrus_berry`
- `recovery_effect.timing`: `threshold_or_after_damage_limited`
- `recovery_effect.estimated_recovery_hp`
- `recovery_effect.formula_label`: `floor(max_hp / 4)`
- `recovery_effect.raw_damage_rolls_changed`: `false`
- `recovery_effect.ko_context_changed`: `false`
- `is_final_battle_truth`: `false`

Available Leftovers context may include:

- `mode`: `limited_item_recovery_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `leftovers`
- `item.status`: `user_confirmed`
- `recovery_effect.type`: `leftovers`
- `recovery_effect.timing`: `end_of_turn_limited`
- `recovery_effect.estimated_recovery_hp`
- `recovery_effect.formula_label`: `floor(max_hp / 16)`
- `recovery_effect.raw_damage_rolls_changed`: `false`
- `recovery_effect.ko_context_changed`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_recovery_item`
- `item_not_user_confirmed`
- `defender_max_hp_missing`
- `unsupported_recovery_item`
- `damage_estimate_missing`
- `turn_engine_required`

The LLM may say:

- "Leftovers may affect follow-up KO/2HKO under limited assumptions, but exact end-of-turn recovery and sequencing are not modeled."
- "Sitrus Berry recovery is shown as limited context only and does not change the raw damage or KO estimate."
- "The raw KO estimate does not include recovery; recovery_context is a separate limited note."
- "This recovery note does not change the raw damage estimate or the limited KO context."

The LLM must not say:

- "This always becomes a 3HKO after Leftovers."
- "Sitrus definitely activates here."
- "The KO chance already includes recovery."
- "Leftovers has been fully simulated."
- "Recovery changes the raw damage rolls."
- "Recovery changes ko_context."
- "Recovery applies when the item is unknown or unconfirmed."

When `recovery_context.available` is true, the recovery note should stay concise, ideally one or two sentences, and should mention that exact activation timing, item consumption, and turn sequencing are not modeled. It should not become longer than the recommendation.

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `speed_order_context`, or `ko_context`.

## Accuracy Context Semantics

`accuracy_context` is an additive limited context for move hit reliability. It is never nested inside `damage_estimate` or `ko_context`.

`accuracy_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item damage modifier math, or `ko_context`.

In v0.63, the only modeled accuracy context is limited Bright Powder context:

- defender item profile must be `status: user_confirmed`
- defender item id must be `bright-powder`
- move accuracy metadata must be available
- final hit probability is not calculated
- hit-adjusted KO probability is not calculated
- exact accuracy/evasion stage math is not modeled
- ability/weather interactions, multi-hit accuracy, and turn sequencing are not modeled
- raw damage and KO/OHKO/2HKO estimates do not include hit chance

Available Bright Powder context may include:

- `mode`: `limited_accuracy_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `bright-powder`
- `item.status`: `user_confirmed`
- `move_accuracy.base_accuracy`
- `move_accuracy.accuracy_source`: `move_metadata`
- `move_accuracy.accuracy_known`: `true`
- `accuracy_effect.type`: `bright_powder`
- `accuracy_effect.effect_label`: `may_reduce_hit_reliability`
- `accuracy_effect.formula_label`: `bright_powder_limited_modifier`
- `accuracy_effect.raw_damage_rolls_changed`: `false`
- `accuracy_effect.ko_context_changed`: `false`
- `accuracy_effect.hit_probability_integrated`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_bright_powder`
- `item_not_user_confirmed`
- `move_accuracy_missing`
- `unsupported_accuracy_item`
- `accuracy_engine_missing`
- `turn_engine_required`
- `damage_estimate_missing`

The LLM may say:

- "Bright Powder may reduce hit reliability under limited accuracy context, but the raw damage and KO estimates do not include hit chance."
- "The move can KO by raw damage rolls, but accuracy and Bright Powder effects are not integrated into that KO chance."
- "This is not a final hit probability; accuracy/evasion stages, ability interactions, weather, multi-hit accuracy, and turn sequencing are not modeled."
- "Final hit probability is not calculated, and hit-adjusted KO probability is not available."

The LLM must not say:

- "The damage is reduced by Bright Powder."
- "This move will miss."
- "This move is guaranteed to miss."
- "The KO chance already accounts for Bright Powder."
- "The final hit probability is confirmed."
- "The hit-adjusted KO chance is 70%."
- "Bright Powder applies when the item is unknown or unconfirmed."

When `accuracy_context.available` is true, the accuracy note should stay concise, ideally one or two sentences, and should mention that raw damage and KO/OHKO/2HKO estimates do not include hit chance. It should also include one concise limitation sentence that final hit probability, accuracy/evasion stages, ability/weather interactions, multi-hit accuracy, and turn sequencing are not modeled.

If `accuracy_context.available` is false, or no `accuracy_context` is present for a move, the LLM should not invent Bright Powder accuracy effects or force an accuracy limitation sentence.

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `speed_order_context`, or `ko_context`.

## Critical Context Semantics

`critical_context` is an additive limited context for Scope Lens critical-hit likelihood. It is never nested inside `damage_estimate` or `ko_context`.

`critical_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item damage modifier math, or `ko_context`.

In v0.66, the only modeled critical-hit context is limited Scope Lens context:

- attacker item profile must be `status: user_confirmed`
- attacker item id must be `scope-lens`
- final critical-hit probability is not calculated
- crit-adjusted KO probability is not calculated
- critical-hit damage is not folded into raw damage estimates
- exact critical-hit stage math is not exposed in the LLM payload
- abilities, move-specific crit effects, and turn sequencing are not modeled
- raw damage and KO/OHKO/2HKO estimates do not include crit chance

Available Scope Lens context may include:

- `mode`: `limited_critical_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: `scope-lens`
- `item.status`: `user_confirmed`
- `critical_effect.type`: `scope_lens`
- `critical_effect.effect_label`: `may_increase_critical_hit_likelihood`
- `critical_effect.formula_label`: `scope_lens_limited_critical_modifier`
- `critical_effect.raw_damage_rolls_changed`: `false`
- `critical_effect.ko_context_changed`: `false`
- `critical_effect.crit_probability_integrated`: `false`
- `critical_effect.crit_adjusted_ko_integrated`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_scope_lens`
- `item_not_user_confirmed`
- `unsupported_critical_item`
- `critical_engine_missing`
- `move_crit_metadata_missing`
- `turn_engine_required`
- `damage_estimate_missing`

The LLM may say:

- "Scope Lens may increase critical-hit likelihood as limited critical context, but the raw damage and KO estimates do not include crit chance."
- "The raw KO chance is separate from any critical-hit possibility; crit-adjusted KO probability is not calculated."
- "This is not a final critical-hit probability; critical-hit stages, abilities, move-specific crit effects, and turn sequencing are not modeled."

The LLM must not say:

- "Scope Lens boosts the damage directly."
- "This move will crit."
- "This move is guaranteed to crit."
- "The KO chance already accounts for Scope Lens crit chance."
- "The final critical-hit probability is confirmed."
- "The crit-adjusted KO chance is 70%."
- "Scope Lens applies when the item is unknown or unconfirmed."

When `critical_context.available` is true, the critical-hit note should stay concise, ideally one or two sentences, and should mention that raw damage and KO/OHKO/2HKO estimates do not include crit chance. It should also state that final critical-hit probability and crit-adjusted KO probability are not calculated.

If `critical_context.available` is false, or no `critical_context` is present for a move, the LLM should not invent Scope Lens critical-hit effects or force a critical-hit limitation sentence.

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `speed_order_context`, or `ko_context`.

## Flinch Context Semantics

`flinch_context` is an additive limited context for King's Rock flinch pressure. It is never nested inside `damage_estimate` or `ko_context`.

`flinch_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item damage modifier math, or `ko_context`.

In v0.70, the only modeled flinch context is limited King's Rock context:

- attacker item profile must be `status: user_confirmed`
- attacker item id must be `kings-rock`
- final flinch probability is not calculated
- flinch-adjusted turn or outcome probability is not calculated
- flinch pressure is not folded into raw damage estimates
- exact speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled
- raw damage and KO/OHKO/2HKO estimates do not include flinch chance

Available King's Rock context may include:

- `mode`: `limited_flinch_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: `kings-rock`
- `item.status`: `user_confirmed`
- `flinch_effect.type`: `kings_rock`
- `flinch_effect.effect_label`: `may_add_flinch_pressure`
- `flinch_effect.formula_label`: `kings_rock_limited_flinch_modifier`
- `flinch_effect.raw_damage_rolls_changed`: `false`
- `flinch_effect.ko_context_changed`: `false`
- `flinch_effect.flinch_probability_integrated`: `false`
- `flinch_effect.turn_outcome_integrated`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_kings_rock`
- `item_not_user_confirmed`
- `unsupported_flinch_item`
- `flinch_engine_missing`
- `move_flinch_metadata_missing`
- `turn_engine_required`
- `damage_estimate_missing`

The LLM may say:

- "King's Rock may add flinch pressure as limited flinch context, but the raw damage and KO estimates do not include flinch chance."
- "The raw KO chance is separate from any King's Rock flinch possibility; flinch-adjusted turn or outcome probability is not calculated."
- "King's Rock flinch pressure is separate from the raw damage estimate; raw damage and raw `ko_context` are unchanged."
- "This is not a final flinch probability; speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled."

The LLM must not say:

- "King's Rock boosts the damage directly."
- "This move will flinch the target."
- "The target cannot move."
- "This move is guaranteed to flinch."
- "The KO chance already accounts for King's Rock flinch chance."
- "The final flinch probability is confirmed."
- "The flinch-adjusted KO chance is 70%."
- "King's Rock applies when the item is unknown or unconfirmed."

When `flinch_context.available` is true, the flinch note should stay concise, ideally one or two sentences, and should mention that raw damage and KO/OHKO/2HKO estimates do not include flinch chance. It should also state that final flinch probability and flinch-adjusted turn or outcome probability are not calculated.

When `flinch_context.available` is true, the LLM should say the raw damage estimate is unchanged and raw `ko_context` is unchanged. It should include one concise limitation sentence that speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled.

When `flinch_context.available` is true, prefer "raw damage estimate is unchanged" over awkward wording such as "damage modifier is not included." King's Rock is not a direct damage boost, and flinch context should be framed as separate pressure, not as damage modifier bookkeeping.

If `flinch_context.available` is false, or no `flinch_context` is present for a move, the LLM should not invent King's Rock flinch effects or force a flinch limitation sentence.

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `speed_order_context`, or `ko_context`.

## Multi-hit Context Semantics

`multi_hit_context` is an additive limited context for Loaded Dice multi-hit reliability. It is never nested inside `damage_estimate` or `ko_context`.

`multi_hit_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item damage modifier math, or `ko_context`.

In v0.73, the only implemented multi-hit context helper is limited Loaded Dice context. In v0.80, Loaded Dice is blocked from user-facing modeled context until Champions legal coverage is confirmed:

- attacker item profile must be `status: user_confirmed`
- attacker item id must be `loaded-dice`
- attacker item id must also pass the Champions legal item gate
- move metadata must identify the move as multi-hit
- final hit count probability is not calculated
- multi-hit-adjusted KO probability is not calculated
- hit count changes are not folded into raw damage estimates
- raw damage and KO/OHKO/2HKO estimates do not include multi-hit count changes
- Focus Sash interaction, King's Rock interaction, accuracy/crit per-hit handling, and turn sequencing are not modeled

Available Loaded Dice context may include:

Note: while `loaded-dice` is absent from `data/static/champions_legal_items.json`, this available shape is future-only and should not appear in user-facing payloads.

- `mode`: `limited_multi_hit_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: `loaded-dice`
- `item.status`: `user_confirmed`
- `move_metadata.is_multi_hit`: `true`
- `move_metadata.metadata_source`: `move_metadata`
- `move_metadata.multi_hit_known`: `true`
- `multi_hit_effect.type`: `loaded_dice`
- `multi_hit_effect.effect_label`: `may_improve_multi_hit_reliability`
- `multi_hit_effect.formula_label`: `loaded_dice_limited_multihit_modifier`
- `multi_hit_effect.raw_damage_rolls_changed`: `false`
- `multi_hit_effect.ko_context_changed`: `false`
- `multi_hit_effect.hit_count_probability_integrated`: `false`
- `multi_hit_effect.multi_hit_adjusted_ko_integrated`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_loaded_dice`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `unsupported_multi_hit_item`
- `move_not_multi_hit`
- `move_multihit_metadata_missing`
- `multi_hit_engine_missing`
- `turn_engine_required`
- `damage_estimate_missing`

The LLM may say:

- "Loaded Dice may improve multi-hit reliability as limited context, but the raw damage and KO estimates do not include multi-hit count changes."
- "The raw KO chance is separate from any Loaded Dice multi-hit possibility; multi-hit-adjusted KO probability is not calculated."
- "This is not a final hit count distribution; Focus Sash, King's Rock, accuracy, crit per-hit handling, and turn sequencing are not modeled."

The LLM must not say:

- "Loaded Dice directly boosts the damage."
- "This move will hit 5 times."
- "This guarantees 5 hits."
- "The KO chance already accounts for Loaded Dice hit count changes."
- "Loaded Dice breaks Focus Sash here."
- "The final hit count probability is confirmed."
- "The multi-hit-adjusted KO chance is 70%."
- "Loaded Dice applies when the item is unknown or unconfirmed."

When `multi_hit_context.available` is true, the multi-hit note should stay concise, ideally one or two sentences, and should mention that raw damage and KO/OHKO/2HKO estimates do not include multi-hit count changes. It should also state that final hit count probability and multi-hit-adjusted KO probability are not calculated.

If `multi_hit_context.available` is false, or no `multi_hit_context` is present for a move, the LLM should not invent Loaded Dice multi-hit effects or force a multi-hit limitation sentence.

If `multi_hit_context.available` is false because the item is blocked by legal coverage, the blocked reason is developer/debug/contract metadata. The default user-facing recommendation should stay quiet about Loaded Dice and should not say "Loaded Dice," "user-confirmed Loaded Dice," "Loaded Dice is not modeled," or "Loaded Dice's effect is not included" unless the user explicitly asks about Loaded Dice.

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `type_boost_context`, `speed_order_context`, `resist_berry_context`, `chilan_berry_context`, or `ko_context`.

## Available Item Context Required Mention

When the default advice payload contains one or more item context fields with `available=true`, the prompt must include a required-mention guard. The guard lists the available item contexts and tells Gemini to mention each listed context at least once when it is directly relevant to the recommendation.

The guard is generated from the already-filtered default advice payload, not from the enriched/debug payload. Therefore it applies only to contexts still visible to ordinary advice. It must not reintroduce unavailable, deferred, blocked, unsupported, or non-triggered item names or reasons.

Available item contexts must not be described as unavailable, unmodeled, not included, not reflected, absent, or omitted. In particular, when any available item context is present, ordinary advice should avoid generic wording such as:

- "item is not included"
- "item is not modeled"
- "item is not reflected"
- "no item is considered"
- "assuming no item"
- "without item effects"
- "default no-item assumption"

This guard does not change raw calculations by itself. Available item context wording must remain limited and must not become final KO odds, guaranteed survival, guaranteed move order, exact final stats, or final battle truth. Raw damage rolls and `ko_context` remain governed by their existing fields. For v3.1 Light Ball, those existing fields are the adjusted advisor damage estimate rolls when the eligible Pikachu + Light Ball modifier is applied.

For Light Ball, an available `species_stat_item_context` should be mentioned as Pikachu-specific offensive item context. For Chilan Berry, an available `chilan_berry_context` should be mentioned as Normal-type limited context for a Normal-type damaging move.

## Unavailable Item Context Silence

Unavailable, deferred, blocked, unconfirmed, non-triggered, or absent item context reasons are developer/debug/contract metadata by default. They should not be surfaced in ordinary battle advice.

The default Gemini advice payload is filtered from the enriched/debug payload. Item context fields with `available=false` are removed from the default advice payload before prompt serialization, while the enriched/debug payload may retain the full context and `reason` for diagnostics and tests. This keeps unavailable/deferred reasons available to developers without giving Gemini default advice a reason to explain them.

In v1.0, the default-advice filtering policy is registry-backed. The contract-owned registry constants list the context keys that are allowed to participate in default advice filtering:

- `ADVICE_CONTEXT_KEYS`: all known advice context surfaces, including top-level `speed_context`
- `ADVICE_ITEM_CONTEXT_KEYS`: item context fields that are removed from default advice when `available=false`
- `ADVICE_CONTEXTS_REQUIRING_MOVE_LOCAL_ITEM_EFFECT_SCRUB`: context fields that also require local `damage_estimate.item_effects` scrubbing when unavailable
- `DEBUG_ONLY_REASON_PHRASES`: debug-only limitation wording removed from default advice payload limitations/notes

`build_ui_advice_payload()` delegates to the default-advice filtering helper so the same policy applies before prompt serialization. This is a cleanup only: it does not add item mechanics, change raw damage rolls, change `ko_context`, or change legal fixture behavior.

The default advice payload also strips debug-only limitation strings that contain unavailable/deferred/blocked wording such as "not modeled", "not reflected", "unsupported", "deferred", "blocked", "effect is not applied", or "item effect is not included". This applies to nested `limitations` lists as well, including otherwise legal raw contexts such as `ko_context`, so generic limitation wording does not leak unavailable item state into ordinary advice. The enriched/debug payload may keep those limitations for diagnostics.

The filtering applies to item context fields such as:

- `survival_context`
- `recovery_context`
- `accuracy_context`
- `critical_context`
- `flinch_context`
- `multi_hit_context`
- `type_boost_context`
- `species_stat_item_context`
- `speed_order_context`
- `resist_berry_context`
- `chilan_berry_context`
- future `charge_context`

Top-level `speed_context` is listed as an advice context but is not filtered as an item context. It keeps the existing Speed contract and remains raw/effective Speed comparison only. Choice Scarf effective Speed continues to live in `speed_context`, not `speed_order_context`, and Choice Scarf choice lock remains unmodeled.

When a user-confirmed item is absent from Champions legal coverage, default advice payloads also hide that non-legal item profile as unknown. This prevents blocked item names such as Loaded Dice or future-only items such as Power Herb from appearing in ordinary advice JSON. The enriched/debug payload may still retain the original item profile and blocked context reason.

This applies to unavailable item contexts such as:

- `blocked_by_legal_item_coverage`
- `future_only_until_legal_confirmed`
- `move_not_super_effective`
- `chilan_berry_deferred`
- `item_not_user_confirmed`
- `no_resist_berry`

Default user-facing advice must not say:

- "item effect is not included"
- "opponent's item effect is not included"
- "user-confirmed item effect is not included"
- "item is not modeled"
- "item effect is not applied"
- "not included in this estimate"
- "not reflected in the calculation"

Default user-facing advice should also avoid naming unavailable or deferred item effects. If the user explicitly asks about that item or reason, the response may briefly explain the relevant metadata state without implying that a final item-adjusted calculation exists.

## Resist Berry Context Semantics

`resist_berry_context` is an additive limited context for standard type-resist berries. It is never nested inside `damage_estimate` or `ko_context`.

`resist_berry_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item damage modifier math, or `ko_context`.

The first supported scope is the 17 standard type-resist berries whose `items_damage.json` metadata has a `resist_type` and does not set `always_resist=true`:

- `babiri-berry`
- `charti-berry`
- `chople-berry`
- `coba-berry`
- `colbur-berry`
- `haban-berry`
- `kasib-berry`
- `kebia-berry`
- `occa-berry`
- `passho-berry`
- `payapa-berry`
- `rindo-berry`
- `roseli-berry`
- `shuca-berry`
- `tanga-berry`
- `wacan-berry`
- `yache-berry`

The Normal-type always-resist berry edge case is handled separately by `chilan_berry_context` because `items_damage.json` marks it as `always_resist=true`, and that edge case is not the same as a super-effective trigger.

Available resist berry context requires:

- defender item profile must be `status: user_confirmed`
- defender item id must pass the Champions legal item gate
- defender item id must exist in `items_damage.json` `type_resist_berries`
- incoming move type must be known
- incoming move type must match the berry resisted type
- `damage_estimate.type_effectiveness` must identify the hit as super effective
- raw damage and KO/OHKO/2HKO estimates do not include berry reduction
- berry-adjusted damage is not calculated
- berry-adjusted KO probability is not calculated
- item consumption is not tracked
- multi-hit handling, abilities, weather, Tera, and turn sequencing are not modeled

Available context may include:

- `mode`: `limited_resist_berry_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: the berry id
- `item.status`: `user_confirmed`
- `item.legal_status`: `legal_modeled`
- `resist_effect.berry_type`: resisted type from `items_damage.json`
- `resist_effect.incoming_move_type`: incoming move type
- `resist_effect.requires_super_effective_hit`: `true`
- `resist_effect.super_effective_match`: `true`
- `resist_effect.effect_label`: `may_reduce_qualifying_super_effective_hit`
- `resist_effect.formula_label`: `resist_berry_limited_damage_reduction`
- `resist_effect.raw_damage_rolls_changed`: `false`
- `resist_effect.ko_context_changed`: `false`
- `resist_effect.berry_adjusted_damage_integrated`: `false`
- `resist_effect.berry_adjusted_ko_integrated`: `false`
- `resist_effect.item_consumption_tracked`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_resist_berry`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `incoming_move_type_missing`
- `berry_type_missing`
- `move_not_super_effective`
- `type_matchup_unknown`
- `chilan_berry_deferred`
- `resist_berry_engine_missing`
- `damage_estimate_missing`

The LLM may say:

- "Yache Berry may reduce a qualifying Ice-type super-effective hit as limited context, but the raw damage and KO estimates do not include berry reduction."
- "This is not a final survival prediction because item consumption and turn sequencing are not modeled."

The LLM must not say:

- "Yache Berry makes this always survive."
- "The KO chance already includes Yache Berry."
- "The damage range is reduced to X-Y."
- "The berry-adjusted KO chance is 70%."
- "The berry has already been consumed."
- "A deferred resist berry edge case is modeled" unless a future explicit field supports it.

When `resist_berry_context.available` is true, the resist berry note should stay concise, ideally one or two sentences, and should mention that raw damage and KO/OHKO/2HKO estimates do not include berry reduction. It should also state that berry-adjusted damage, berry-adjusted KO probability, and item consumption are not calculated.

When `resist_berry_context.available` is true, prefer wording such as "raw damage estimate is unchanged" and "raw ko_context is unchanged" over wording that implies the berry should have been part of the damage formula.

If `resist_berry_context.available` is false in the enriched/debug payload, the default advice payload should omit `resist_berry_context`. The unavailable reason is developer/debug/contract metadata only. The LLM should not invent resist berry effects, force a resist berry limitation sentence, or mention the unavailable berry name/effect/reason in default advice.

For unavailable resist berry context, the LLM must not say:

- "Yache Berry effect is not applied."
- "The berry effect is not included."
- "The berry is not modeled."
- "Yache Berry is unavailable because the move is not super effective."

If the user explicitly asks about that berry, the response may briefly explain that the current move does not have an available limited `resist_berry_context`, without claiming berry-adjusted damage or KO probability.

## Chilan Berry Context Semantics

`chilan_berry_context` is an additive limited context for Chilan Berry's Normal-type special case. It is separate from `resist_berry_context` because Chilan Berry does not use the standard super-effective trigger model.

`chilan_berry_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item modifier math, Q12 constants, or `ko_context`.

Available Chilan context requires:

- defender item profile must be `status: user_confirmed`
- defender item id must be `chilan-berry`
- defender item id must pass the Champions legal item gate
- `items_damage.json` metadata must identify `resist_type=normal`
- `items_damage.json` metadata must identify `always_resist=true`
- incoming move type must be known
- incoming move type must be `normal`
- incoming move must be damaging
- raw `damage_estimate` must be available

Available context may include:

- `mode`: `limited_chilan_berry_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `chilan-berry`
- `item.status`: `user_confirmed`
- `item.legal_status`: `legal_modeled`
- `normal_resist_effect.berry_type`: `normal`
- `normal_resist_effect.incoming_move_type`: `normal`
- `normal_resist_effect.requires_super_effective_hit`: `false`
- `normal_resist_effect.always_resist`: `true`
- `normal_resist_effect.effect_label`: `may_reduce_normal_type_hit`
- `normal_resist_effect.formula_label`: `chilan_berry_limited_normal_damage_reduction`
- `normal_resist_effect.raw_damage_rolls_changed`: `false`
- `normal_resist_effect.ko_context_changed`: `false`
- `normal_resist_effect.chilan_adjusted_damage_integrated`: `false`
- `normal_resist_effect.chilan_adjusted_ko_integrated`: `false`
- `normal_resist_effect.item_consumption_tracked`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_chilan_berry`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `chilan_berry_metadata_missing`
- `incoming_move_type_missing`
- `move_type_not_normal`
- `move_not_damaging`
- `damage_estimate_missing`

When `chilan_berry_context.available` is true, the LLM should say Chilan Berry is a Normal-type limited context and may reduce damage from a Normal-type damaging move. It should also say this limited context is separate from raw damage rolls and is not integrated into final KO odds; raw damage rolls and `ko_context` remain based on the current calculator. It should not say Chilan Berry is not included or not modeled when the available context is present.

The LLM must not say:

- "Chilan Berry is not included."
- "Chilan Berry is not modeled."
- "Chilan Berry guarantees survival."
- "Confirmed live."
- "The Pokemon will survive because of Chilan Berry."
- "KO chance is reduced to X."
- "Final damage is halved."
- "Raw damage rolls already include Chilan Berry."
- "Chilan Berry applies to all move types."

If `chilan_berry_context.available` is false in the enriched/debug payload, the default advice payload should omit `chilan_berry_context`. The unavailable reason is developer/debug/contract metadata only. The LLM should not mention Chilan Berry, the Chilan effect, or the unavailable reason in default advice unless the user explicitly asks about that item.

## KO Context Semantics

`ko_context` is an additive limited context next to a relevant `damage_estimate`. It does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item modifiers, or `survival_context`.

In v0.57, KO context is limited damage-roll context:

- OHKO chance is based on raw damage rolls when rolls are available.
- `successful_rolls` counts rolls where `roll >= current_hp`.
- `chance` is `successful_rolls / total_rolls`.
- `ohko.guaranteed` is true only when every roll meets or exceeds current HP.
- If rolls are missing, min/max fallback may set possible/guaranteed booleans but must not invent a chance.
- 2HKO context uses limited min/max logic:
  - `min_damage * 2 >= current_hp` means guaranteed 2HKO under limited assumptions.
  - `max_damage * 2 >= current_hp` means possible 2HKO under limited assumptions.
  - roll-pair 2HKO probability is not exposed in v0.57.

Available KO context may include:

- `mode`: `limited_damage_roll_ko_context`
- `available`: `true`
- `target_hp.current_hp`
- `target_hp.max_hp`
- `target_hp.hp_percent`
- `damage.min`
- `damage.max`
- `damage.roll_count`
- `ohko.possible`
- `ohko.guaranteed`
- `ohko.chance`
- `ohko.successful_rolls`
- `ohko.total_rolls`
- `two_hko.possible`
- `two_hko.guaranteed`
- `two_hko.method`: `limited_min_max`
- `raw_damage_rolls_changed`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `hp_unknown`
- `damage_estimate_missing`

The LLM may say:

- "The raw damage rolls have a 6/16 chance to KO from the current HP, but this is limited damage-roll context."
- "This is a limited 2HKO estimate assuming the same move is used twice with no healing, switching, protection, or chip changes."
- "Raw damage could KO, but survival context is separate and may allow limited Focus Sash or Focus Band survival under its own assumptions."

The LLM must not say:

- "This guarantees the KO in battle."
- "This will always 2HKO."
- "The opponent cannot survive."
- "Focus Sash or Focus Band is included in the KO probability."
- "Accuracy, Speed order, priority, recovery, hazards, chip damage, switching, protection, or turn sequencing are modeled."

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `speed_order_context`, or `ko_context`.

## Opponent Assumption Semantics

`opponent_assumptions` is a context-only risk section for possible opponent sample profiles.

It must not be treated like:

- `stat_profiles`
- `opponent_moves.known_moves`
- user-confirmed final stats
- damage calculation input
- Speed calculation input

The LLM may say:

- "Possible opponent samples include a fast physical Garchomp sample."
- "These are assumptions, not confirmed opponent stats."
- "The sample is context only and was not used directly for damage or speed calculation."
- "Prior probability is not available for this sentinel sample."
- "Garchomp has possible sample assumptions, but they are context only and not confirmed."
- "A possible fast physical Garchomp sample exists, but it was not used directly for damage or speed calculation."
- "The opponent's exact set is still unknown."

The LLM must not say:

- "The opponent is this sample."
- "The opponent definitely has 154 Speed."
- "This sample proves the opponent item."
- "prior_probability is null, so this set is impossible."
- "This sample confirms turn order, KO, or survival."

User-confirmed fields override possible sample assumptions. If a future payload marks conflicts between `user_confirmed_fields` and possible samples, conflicting samples must not drive advice.

When `opponent_assumptions.available` is `true` and `possible_samples` is non-empty, the LLM should briefly mention the existence of possible sample context when relevant, preferably as one short limitation sentence:

- "Possible opponent samples exist, but they are context-only and not confirmed."

This sentence is a visibility cue, not a calculation claim. The LLM must not say sample stats were used for damage, Speed, KO, survival, or final turn order unless a future payload explicitly provides that calculated field.

Concision guardrail:

- Do not dump `sample_id`, full stats, source metadata, `update_policy`, `coverage_probability`, or full Top-K sample lists into the response.
- Do not let sample context become longer than the main damage recommendation.
- If `opponent_assumptions.available` is `false`, do not invent samples or force a sample limitation.
- Do not enumerate role, archetype, or possible item metadata by default.
- `possible_items` are possible assumptions, not confirmed held items.

## Opponent Assumptions Debug Summary

The developer debug summary is a copy/export-ready view of `opponent_assumptions` only. It is not a full LLM payload export and must not be automatically inserted into the Gemini response.

Debug summary policy:

- developer-only
- `opponent_assumptions` summary only
- no full LLM payload export in v0.45
- no API keys, secrets, `.env` values, or token usage logs
- no full stats dump
- no full source metadata dump
- no `update_policy` dump
- no full Top-K metadata dump
- no UI debug panel in v0.45

The summary may include:

- opponent species id
- availability and unavailable reason
- `calculation_usage`
- `is_confirmed_information`
- possible sample count
- included Top-K count
- sample id
- sample species id
- role / archetype id when present
- confidence
- `is_user_confirmed`
- possible items
- `used_for_damage: false`
- `used_for_speed: false`
- guardrail booleans such as `not_confirmed`, `not_damage_input`, `not_speed_input`, `not_final_turn_order`, and `context_only`

If a future file export is added, it should write only to a git-ignored debug path such as `logs/debug_payloads/`. Debug exports remain outside commits.

v0.51 adds a developer CLI for this summary:

```powershell
uv run python scripts/debug_opponent_assumptions.py --species rotom-wash
```

The CLI prints the safe `opponent_assumptions` debug summary JSON to stdout. It does not call Gemini, does not write files, does not export the full LLM payload, and does not read or print API keys, `.env` values, secrets, or token logs. `--top-k` can be used to limit possible samples.

## Speed Context Semantics

`speed_context` is raw and supported effective Speed comparison only.

It may compare `stat_profiles.my_active.final_stats.spe` and `stat_profiles.opponent_active.final_stats.spe` only when both active Pokemon have `status: "user_confirmed_final_stats"`.

Effective Speed in v0.30 may include only:

- Choice Scarf speed modifier
- only when `item_profiles.*.status` is `user_confirmed`
- only when `item_profiles.*.item_id` is `choice-scarf`

Choice Scarf uses a `1.5` speed modifier in `speed_context.*.speed_modifiers`.

Choice Scarf choice lock is not modeled.

It does not model:

- priority
- Tailwind
- Trick Room
- paralysis
- Speed stages
- ability speed effects
- final turn order
- Turn Engine state

The LLM may say:

- "Based on raw Speed only, your Pokemon appears faster."
- "With the supported Choice Scarf speed modifier, your Pokemon appears faster by effective Speed estimate."
- "This does not confirm final turn order because priority, Tailwind, Trick Room, paralysis, Speed stages, and ability speed effects are not modeled."

The LLM must not say:

- "You will move first."
- "Choice Scarf guarantees you move first."
- "This guarantees turn order."

If `speed_context.available` is `false`, the LLM should not compare Speed and should mention that raw Speed comparison requires user-confirmed final Speed for both active Pokemon.

## Speed-Order Item Context Semantics

`speed_order_context` is an additive limited context for Quick Claw move-order pressure. It is never nested inside `speed_context`, `damage_estimate`, or `ko_context`.

In v0.98, modeled speed-order item context is limited to Quick Claw:

- `item_profiles.<attacker>.status` must be `user_confirmed`
- `item_profiles.<attacker>.item_id` must be `quick-claw`
- Champions legal item coverage must pass
- a selected/available/known move payload must exist

Available context may include:

- `mode`: `limited_speed_order_item_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: `quick-claw`
- `item.status`: `user_confirmed`
- `item.legal_status`: `legal_modeled`
- `speed_order_effect.type`: `quick_claw`
- `speed_order_effect.effect_label`: `may_affect_move_order`
- `speed_order_effect.activation_probability_calculated`: `false`
- `speed_order_effect.final_move_order_calculated`: `false`
- `speed_order_effect.speed_tie_resolved`: `false`
- `speed_order_effect.priority_integrated`: `false`
- `speed_order_effect.turn_engine_integrated`: `false`
- `is_final_battle_truth`: `false`

When `speed_order_context.available` is true, the LLM may say Quick Claw may affect move order or can occasionally affect move order. The LLM should also say move order is not fully modeled and should not treat the context as guaranteed priority.

The LLM must not say:

- "Quick Claw will move first."
- "Quick Claw guarantees outspeeding."
- "Confirmed first."
- "Always acts before."
- "Wins the speed interaction."
- "Safe because it moves first."
- "Quick Claw activation probability is X%."

The context does not calculate final move order, activation probability, speed ties, priority, Trick Room, Tailwind, paralysis, boosts, abilities, weather, item consumption, or turn sequencing.

If `speed_order_context.available` is false in the enriched/debug payload, the default advice payload should omit `speed_order_context`. The unavailable reason is developer/debug/contract metadata only. The LLM should not mention the unavailable Quick Claw item name, effect, or reason in default advice unless the user explicitly asks about that item.

Choice Scarf is not modeled through `speed_order_context`; keep Choice Scarf handling in top-level `speed_context`.

## Type Effectiveness Semantics

Damage estimates include explicit type effectiveness metadata:

```json
{
  "type_effectiveness": {
    "multiplier": 0.5,
    "label": "not_very_effective"
  }
}
```

Labels:

- `immune`: multiplier `0`
- `not_very_effective`: multiplier greater than `0` and less than `1`
- `neutral`: multiplier `1`
- `super_effective`: multiplier greater than `1`

The LLM must use this field when explaining type matchups. It must not call a move super effective, resisted, or immune from general Pokemon knowledge when this field says otherwise.

The LLM must not print raw labels such as `super_effective` or `not_very_effective` directly. It should convert labels to natural wording:

- `super_effective` -> "super effective"
- `not_very_effective` -> "not very effective" or "resisted"
- `immune` -> "immune" or "no effect"
- `neutral` -> "neutral"

## Explicitly Missing

The v0.18 payload does not contain:

- EV/IV/nature
- full battle item effect modeling beyond the legal `item_profiles` selector
- selected ability certainty
- weather
- terrain
- stat boosts
- exact current HP integer
- candidate move damage estimates
- OHKO/2HKO/KO chance
- final turn order
- speed tie
- status duration
- Turn Engine state

## LLM Guardrails

The LLM must not:

- assume unprovided EVs, IVs, nature, held items, boosts, weather, terrain, exact HP, move sets, or Tera types
- treat `base_stats` as final battle stats
- describe `damage_estimate` as final battle damage
- infer OHKO/2HKO, KO chance, survival, or speed order unless explicit calculated fields are present
- treat `speed_context` as final turn order
- claim a Pokemon will move first when `speed_context.is_final_turn_order` is `false`
- apply Choice Scarf speed unless `speed_context.*.speed_modifiers` marks it as applied from a user-confirmed item
- apply priority, Tailwind, Trick Room, paralysis, Speed stages, or ability speed effects from `speed_context`
- treat cache learnsets or unselected moves as available moves
- treat `opponent_moves.candidate_moves` as confirmed opponent moves
- treat `opponent_assumptions.possible_samples` as confirmed opponent sets
- treat `sample_assumed` opponent samples as user-confirmed information
- interpret `prior_probability: null` as zero probability
- claim Top-K omitted opponent sample archetypes are impossible
- say context-only samples changed `damage_estimate` or `speed_context`
- assume the opponent has a candidate move unless it appears in `opponent_moves.known_moves`
- claim candidate move damage, speed order, or turn order from v0.18 opponent move metadata
- describe opponent known move damage estimates as final battle damage
- ignore `assumption_profile` when explaining damage estimate confidence
- invent opponent item, selected ability, EVs, IVs, nature, boosts, speed order, turn outcome, or missing final stats
- infer EVs, IVs, nature, or item from user-confirmed final stats
- treat `unknown` item as `none`
- treat a selected legal item as modeled unless `damage_estimate.item_effects` marks its effect as `applied`
- present damage-supported non-legal/debug items as normal Champions legal selections
- claim item effects are applied unless `damage_estimate.item_effects` marks them as `applied`
- omit an applied attacker item modifier when explaining why one move did more damage
- describe an item-applied estimate as only default assumptions when `item_effects.attacker_item.status` is `applied`
- print raw `type_effectiveness` labels such as `super_effective` or `not_very_effective`
- claim choice lock, Life Orb recoil, Focus Sash survival, or Leftovers recovery is modeled
- mention choice lock for non-Choice items such as Charcoal, Mystic Water, Black Belt, Metal Coat, Sharp Beak, Fairy Feather, Light Ball, Leftovers, Focus Sash, or Focus Band
- describe a move as super effective, resisted, or immune unless `damage_estimate.type_effectiveness` supports that label
- consider Terastallization, which is banned in PoChamps

The LLM may:

- explain broad type or role risks at a non-damage-exact level
- discuss user-confirmed move metadata such as type, category, power, accuracy, and PP
- discuss `damage_estimate` only under its stated default assumptions
- discuss `assumption_profile` as the stat model used for an estimate
- discuss `damage_estimate.item_effects` as the item effect summary for that estimate
- discuss `damage_estimate.type_effectiveness` as the source for type matchup explanations
- discuss `speed_context` as raw and supported effective Speed comparison only when available
- say "based on raw Speed only" or "appears faster by raw Speed" when explaining `speed_context`
- discuss Choice Scarf as a supported effective Speed estimate only when `speed_context.*.speed_modifiers` marks it applied
- say choice lock is not modeled when Choice Scarf speed is applied
- distinguish raw Speed relation from effective Speed relation when they differ
- say a supported item damage modifier is applied only when `damage_estimate.item_effects` says `status: "applied"`
- mention applied attacker item damage modifiers when they are part of the damage estimate
- say Life Orb recoil or Choice item lock is not modeled when those effects appear in `unapplied_effects`
- convert `type_effectiveness` labels into natural wording such as "super effective", "not very effective", "immune", or "neutral"
- discuss user-confirmed final stats as user-provided stat values when `stat_profiles` says so
- discuss `opponent_moves.known_moves` as user-confirmed opponent moves
- discuss `opponent_moves.known_moves[*].damage_estimate` only as default-assumption damage against `my_active`
- discuss `opponent_moves.candidate_moves` only as possible, not confirmed, Champions moves
- discuss `opponent_assumptions.possible_samples` only as context-only possible profiles
- mention that possible samples are assumptions, not confirmed opponent sets
- mention that context-only samples were not used directly for damage or speed calculations
- mention candidate moves as possible threats only when they are labeled as unconfirmed
- use `my_available_moves[*].damage_estimate` to compare the user's own move options
- recommend a direction while naming the missing information that prevents a confident damage-based call
- ask for or point out missing final stats, items, field state, opponent moves, or damage estimates

## Damage Estimate Defaults

Each damage estimate includes this default assumption profile:

```json
{
  "id": "default_level50_ivs31_evs0_neutral_no_item",
  "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / no item",
  "source": "system_default",
  "confidence": "rough_reference",
  "is_user_confirmed": false
}
```

When a supported damage item modifier is applied with default stats, the profile changes to:

```json
{
  "id": "default_level50_ivs31_evs0_neutral_with_damage_item",
  "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / supported damage item",
  "source": "system_default_and_user_input",
  "confidence": "rough_reference_with_user_confirmed_item",
  "is_user_confirmed": false
}
```

Move damage estimates use:

- level 50
- IV 31 all
- EV 0 all
- neutral nature
- no item
- no boosts
- no weather
- no terrain
- no screens
- no critical hit
- singles / non-spread assumption
- no ability effects unless explicitly selected and connected

`percent_range` uses default defender max HP as the denominator. It is not exact current HP.

When `stat_profiles` provides six user-confirmed final stats for an active Pokemon, damage estimates may use those final stats. In that case the estimate uses this profile:

```json
{
  "id": "user_confirmed_final_stats_level50",
  "label": "User-confirmed final stats / Level 50",
  "source": "user_input",
  "confidence": "higher_confidence_reference",
  "is_user_confirmed": true
}
```

When user-confirmed final stats and a supported damage item modifier are both used, the profile changes to:

```json
{
  "id": "user_confirmed_final_stats_level50_with_damage_item",
  "label": "User-confirmed final stats / Level 50 / supported damage item",
  "source": "user_input",
  "confidence": "higher_confidence_reference",
  "is_user_confirmed": true
}
```

Even with user-confirmed final stats and supported damage item modifiers, `is_final_battle_damage` remains `false` because selected ability, boosts, weather, terrain, screens, exact current HP, non-damage item effects, and KO odds are not connected.

Unavailable statuses include:

- `unavailable_no_selected_move`
- `unavailable_no_known_move`
- `unavailable_status_move`
- `unavailable_missing_power`
- `unavailable_missing_pokemon`
- `unavailable_missing_base_stats`
- `unavailable_missing_type`
- `unavailable_unsupported_category`
- `unavailable_engine_error`

## Future Field Locations

Future versions may add candidate move threat scoring or opponent-to-my-active KO probability, but those require separate guardrails because candidate moves are not confirmed.

Turn Engine state should later enter a separate top-level `battle_state` section instead of being mixed into Pokemon identity metadata.

## v12.59 Current Condition Context

With limited context enabled, the advisor payload may include
`condition_context.current_conditions`. Each entry is a separately validated
user-confirmed present-state value with `side`, `condition_type`,
`status=user_confirmed`, `source=user_confirmed_current_condition`, and
`confidence=known`. Valid values are limited to `burn`, `poison`, `toxic`,
`paralysis`, `sleep`, `freeze`, `none`, and `unknown`; there is at most one
entry per side.

`none` means the user confirmed no current major status. `unknown` means the
current major status is not known; it is not a request to infer one. This
context does not establish application/trigger timing, resolved effects, exact
status damage, duration, post-turn HP/state, thaw/full-paralysis, RNG, or final
order. Limited context off omits both the raw confirmation candidate and this
payload context.

v12.60 status note: when valid `condition_context` is present, the compact
prompt guard requires a side/type readback as user-confirmed present-state
context and retains the `none`/`unknown` distinction plus non-inference
boundaries. Disabled, absent, empty, invalid, and item-event-only paths omit
condition-specific wording. Offline readiness is not actual-provider approval.

## v12.67 Condition and Item-Event Attribution

When validated `condition_context.current_conditions` or
`item_event_context.observed_events` is present, prompt generation may add a
payload-driven `Trusted context attribution` readback instruction. Each current
condition remains a user-confirmed current state, while each item event remains
an explicitly user-confirmed observation. When both exist, the instruction
requires that the two categories and their side/identity values remain
separate. It does not alter either payload schema, authorize condition-event or
item-effect inference, or establish resolved effects, exact HP/damage, timing,
post-turn state, RNG, or final order.

## v12.70 Structured Trusted-Context Acknowledgement

When normalized trusted condition or observed-item-event entries exist, the
prompt requires a short `[Trusted Context]` block followed by `[Advice]`.
Current-condition lines use `Current condition | side | condition_type` and
observed-item-event lines use `Observed item event | side | item | event_type`.
The required values are derived from normalized payload contexts. The smoke CLI
parser exact-compares the acknowledgement entries to that normalized expected
set and separately rejects empty advice or forbidden resolved/exact/timing/RNG
claims. This changes response formatting only; it does not change payload
schema, source trust, calculations, or turn resolution.
## v13.5 Type-aware deterministic results

`deterministic_calculation_context.type_aware_damage_estimates` records the
limited STAB/type calculation separately from `base_damage_estimates`. A
resolved primary `damage_estimates` record has scope
`base_damage_stage_stab_type`, move/type metadata, `stab`, and
`type_effectiveness` rationals. The acknowledgement parser requires exact STAB
and type-effectiveness lines before the type-aware damage line. Ability/item
overrides and Tera remain excluded.
## v13.6 Context-modified damage boundary

`context_modified_damage_estimates` is separate from v13.5 type-aware results.
It may apply only confirmed attacker burn and ordinary confirmed rain/sun.
Screens require a trusted battle-format source; without one they are unavailable
with `missing_battle_format_for_screen` and are never silently treated as a
singles or doubles modifier.
## v13.7 battle-format screen adapter

Only `user_confirmed_battle_format` values `singles` and `doubles` may resolve
a present defender screen. The production payload uses
`battle_format_context.current_battle_format`, preserving only the confirmed
format/source/known-confidence tuple; raw UI confirmation is removed. Missing
format retains the v13.6 unavailable result.

The trusted exact-set entry is `Battle format | singles` or `Battle format |
doubles`. A resolved screen adds `Screen modifier | opponent | screen |
format | multiplier` to deterministic results. The accepted multipliers are
singles `1/2` and doubles `2/3`; Reflect precedes Aurora Veil for physical
moves and Light Screen precedes Aurora Veil for special moves. One defender
screen reduction is applied, never a stack. Format, side, identity,
multiplier, damage/percentage, KO, and scope mutations are rejected.

## v13.8 priority and field-aware move order

`deterministic_calculation_context.move_order_assessment` is emitted only under
the existing limited-context gate. It uses selected-move metadata priority,
explicitly selected opponent-move metadata priority, final Speed, current
Speed stage, Tailwind, and Trick Room. Missing opponent priority is explicitly
unavailable; priority zero is never inferred. The result scope is
`priority-stage-speed-tailwind-trick-room-only`. Priority precedes Speed;
Tailwind doubles only its side's stage-adjusted integer Speed; Trick Room
reverses equal-priority speed comparison only; equal speed is `tie`.

## v13.9 deterministic hit chance

`deterministic_calculation_context.hit_chance_assessment` uses only selected
move metadata accuracy and current self accuracy/opponent evasion stages.
Omitted stages use the existing neutral-zero stage convention. Accuracy is an
integer rational calculation with standard 3-based stage ratios and floor
rounding before a 100% clamp. Metadata `None` is unavailable unless an explicit
canonical `always_hit` marker exists. It does not affect damage, immunity, KO,
or expected damage and excludes ability, item, weather, OHKO, and special move
rules. The exact deterministic line is `Hit chance | self | opponent | move |
percent-or-unavailable | reason | move-accuracy-and-stages-only`.

## v13.10 drain and recoil

Selected move PokeAPI `meta.drain` is mapped into repository metadata. Positive
values drain and negative values recoil from actual roll damage capped by
confirmed defender HP. The scope is
`damage-dealt-proportional-drain-recoil-only`; no hit-chance expected value,
ability/item exception, or between-turn effect is included. Exact result lines
cover drain/recoil percentage and range, optional HP-capped healing, and
optional recoil KO count/status.

## v13.11 multi-hit damage

`multi_hit_assessment` is separate from single-hit and two-use KO results.
Generic metadata-backed hit counts use independent-roll convolution and current
defender HP for KO status. Exceptional multi-hit rules remain unavailable.

## v13.13 direct healing

`direct_healing_assessment` uses selected move `meta.healing` only under the
limited-context gate. Its scope is `direct-max-hp-proportional-healing-only`.
The calculation is `raw_healing = floor(maximum_hp * healing_percent / 100)`;
actual healing is capped at `maximum_hp - current_hp`, and resulting HP is
current plus actual healing.

Missing or zero metadata emits no result. Full HP is `no_effect`; a fainted
self is `not_applicable`; absent current or maximum HP is unavailable; and
current HP above maximum HP is invalid. Conditional, weather-based, delayed,
or target-dependent healing is unavailable. Gate-off emits neither the result
nor its acknowledgement. Direct healing does not merge with drain/recoil.

## v13.14 fixed damage

`fixed_damage_assessment` is gate-on only and uses scope
`explicit-fixed-damage-rules-only`. Resolved explicit rules carry move, rule,
damage, and deterministic KO status. Level rules require a trusted integer
level 1..100; HP-half rules require exact defender current HP. Unsupported
special and OHKO rules remain unavailable and never use normal formula fallback.

## v13.15 HP-based special damage

`hp_based_special_damage_assessment` is limited-context only with scope
`explicit-hp-based-special-damage-only`. It accepts exact self/opponent HP for
Endeavor and Final Gambit only; it does not use normal damage, recoil, or
post-faint switching mechanics.

## v13.16 Observed Previous Damage

When limited context is enabled, one user-confirmed direct-damage snapshot
normalizes to `observed_previous_damage_context`; raw UI confirmation is not
serialized. It requires positive integer damage, physical/special category,
`direct_move_damage`, and opponent-to-self direction. With limited context
off it is omitted but retained by the UI session. It solely enables the
Counter/Mirror Coat/Metal Burst reactive assessment with exact trusted and
deterministic acknowledgement validation; it does not establish turn timing,
priority, indirect damage, survival effects, or ability overrides.

## v13.17 Self Consequence

Limited context uses existing trusted self current/max HP only for explicit
maximum-HP costs. `self_consequence_assessment` is separate from recoil and
Final Gambit; it does not simulate replacement, delayed healing, stat changes,
or ability overrides.

## v13.18 Current-HP Move Power

Limited context computes only allowlisted current-HP variable move power from
trusted self current/max HP. Missing HP produces unavailable/not-applicable,
never a metadata-power fallback.

## v13.19 Speed-Based Move Power

Electro Ball/Gyro Ball use trusted final Speed, stages, and Tailwind only.

## v13.20 Weight-Based Move Power

Weight power uses canonical integer hectograms and no missing-weight fallback.

## v13.21 Stat-Stage Move Power

Stat-stage power uses only normalized current stages; missing side context has no metadata fallback.

## v13.22 Target-HP Move Power

Target-HP power consumes only normalized opponent current/max HP.

## v13.23 Environment Move Transformation

Environment transformations use trusted field state; Terrain Pulse requires explicit grounded state.

## v13.25 Turn-Event Move Power

Turn-event power consumes explicit current-turn confirmations only.

## v14.23 Advice worker shutdown boundary

Advice shutdown is UI-lifecycle-only: close suppresses callback presentation,
requests cooperative QThread interruption, and never serializes cancellation,
thread identity, request tokens, raw provider output, or raw exceptions into
the advisor payload or UI. A synchronous provider call is not cancellable by
this contract; after it returns, an interrupted worker exits through its
internal cancellation signal without publishing a result.

## v15.0 request-start turn snapshot

Structured recommendation preparation captures a frozen `turn_snapshot` from
the selected UI battle input before candidate evaluation. It contains active
player/opponent identity, confirmed HP and item status where present, and
explicit unknown values otherwise. When `my_available_moves` is present, every
candidate slot must match that active player's move at capture time. Request
tokens, widgets, repositories, provider objects, and inferred item/ability or
field state are never serialized.

## v15.1 unified current-state snapshot

The request-start `turn_snapshot.current_state` contains detached normalized
current-state contexts only: HP, conditions, abilities, stages, field state,
observed item events, and supported deterministic inputs. Explicit side and
slot labels must match the active Pokémon; a supplied session label must match
the request session label. Request tokens, internal fingerprints, widgets,
provider objects, raw responses, and inferred facts remain excluded.

## v15.2 context provenance

Pokémon-scoped current-state entries require canonical provenance matching the
active side, slot, Pokémon identity, and session. Missing or mismatched legacy
provenance is excluded from both candidate input and provider summary; it is
not repaired or inferred. Field-scoped state remains separately allowed.

## v15.3 UI provenance capture

UI-captured side-labelled contexts receive canonical active slot, Pokémon, and
session provenance before request-start snapshot creation. Missing active
identity remains unprovenanced and is excluded by the v15.2 boundary.

## v15.8 observed-event capture

Only the structured copied-input boundary may normalize an explicit trusted UI
event into `turn_snapshot.current_state.item_event_context.observed_events`.
Each event remains separate from known current state and carries matching
side/slot/Pokemon/session provenance, `trust=observed_event`, and explicit
observed/confirmed flags. Wrong-owner or stale-session events are omitted rather
than repaired. Legacy battle input, legacy prompts, and public confirmation
payloads do not gain this internal schema.

## v15.9 deterministic damage-input signature

Structured candidate evaluation creates a detached, snapshot-derived calculation
input before existing deterministic context logic. It binds active attacker and
defender identity plus exact candidate move/slot, and carries copied supported
current-state evidence. This internal signature is not provider-visible. It does
not alter Q12 formulas, fabricate final stats, or turn observed events into
damage modifiers or known item/ability facts.

## v15.10 type and stat provenance bridge

Internal deterministic adapters may look up species types and base stats only by
the frozen snapshot identity. These blocks are repository metadata, not final
stats. Complete user-confirmed final stats remain separately provenanced; absent
values and unsupported ability/item modifiers remain unavailable. The Q12 formula
and provider-visible payload schema are unchanged.

## v15.11 structured final-stat capture

Exact final-stat confirmations are captured with owner/session provenance only
on the structured copied-input boundary. A complete matching six-stat set may
be exposed to the internal provenance bridge; partial or stale values are
excluded. Legacy payloads do not receive provenance fields or final-stat copies.

## v15.12 Q12 snapshot invocation adapter

The internal Q12 invocation adapter accepts only a Q12-ready detached snapshot
input, provenanced final-stat blocks, and a separately trusted level. Its result
is not a provider payload: status moves and incomplete, invalid, or unsupported
inputs remain sanitized local unavailable outcomes. It applies no observed-event,
ability/item, stage, weather, terrain, or field modifier unless a later explicit
adapter contract supports that modifier.

## v15.13 trusted level and candidate Q12 result

`trusted_level_context` is structured-only current-state evidence and accepts
only already-provenanced trusted levels. The prepared internal candidate may
hold a sanitized `q12_damage` result, but provider candidate comparisons and
legacy/public payloads exclude it. Missing trusted level is unavailable, not a
default level or zero damage.

## v15.14 structured known ability

Known current ability is structured-only copied-input evidence captured from an
explicit confirmation with matching owner/session provenance. Species ability
lists and observed activation events do not create that fact. The provider and
legacy payloads receive neither private provenance nor a new Q12 modifier.

## v15.15 observed damage provenance

`current_state.observed_damage_context.observed_damage_events` is structured-only
private evidence. The initial producer supplies a user-confirmed exact HP damage
amount, both active owners, and session provenance; no used move is implied.
Observed evidence is separate from deterministic Q12 output and cannot infer
stats, items, abilities, or modifiers. Legacy/public/provider payloads omit it.

## v15.16 used move and HP transition

Private structured evidence may enrich an observed-damage event only with a
matching explicit `observation_id`. Used-move slot ownership and exact HP
transition validation are required; selected moves and percentage HP are never
promoted. Mismatched amount/transition values preserve the amount and record a
conflict rather than inferring a correction.

## v15.17 observation ordering

Structured observed evidence may carry an explicit observation ID and session-local
sequence. Turn number remains null unless separately user-confirmed; no legacy or
provider-facing payload gains these private fields.

## v15.18 switch/faint evidence

Structured-only switch/faint observations require explicit confirmed ownership,
session, and sequence provenance. They do not alter public payloads or state.

## v15.19 lifecycle evidence

Lifecycle observations are structured-only ordered evidence with explicit scope
and reducer eligibility. They never derive current state or provider modifiers.

## v15.20 replay plan

Replay plans are internal, detached, non-mutating policy output. They are not a
provider payload and never generate Q12 inputs, state transitions, or public fields.

## v15.21 reducer state model

Reducer base state and transition readiness are internal detached contracts only.
They do not mutate snapshots, UI state, provider payloads, or Q12 inputs.

## v15.22 semantic projection

`project_atomic_transition` is private dry-run reducer validation over a copied
`battle-state-v1` state. Its projected state and provenance do not enter legacy,
public-confirmation, or provider payload schemas, and it never applies Q12,
modifiers, or runtime state.

## v15.23 atomic executor

Executor fingerprints, replay-batch identity, commit receipts, and detached
committed state are private reducer contracts. They are excluded from legacy,
public-confirmation, and provider schemas and do not trigger Q12 recomputation.

## v15.24 runtime state store

The process-local store's state snapshots, CAS fingerprints, and session
namespace are private runtime contracts. They do not alter payload schemas or
cause UI, persistence, provider, modifier, or Q12 behavior.

## v15.25 lifecycle confirmation

Canonical lifecycle observations are private structured-only records. They are
not legacy, public-confirmation, or provider schema fields and do not apply state.

## v15.26 used move and HP transition

Explicit private confirmations are structured-only evidence; no public payload,
provider schema, Q12 result, or current UI state is changed.

## v15.28 observation collection

Collected canonical observations remain private session evidence. Snapshot handoff
is not yet wired to production UI or provider-visible payloads.

## v15.29 snapshot handoff

Collection evidence may enter only private `TurnSnapshot.current_state` on an
explicit session-matched detached input. `MainWindow` captures that input at
structured-request start and the worker receives only the frozen mapping;
legacy behavior, reducer/store state, and Q12 are unchanged.

## v15.30 trusted turn context

`TurnSnapshot.current_state.trusted_turn_context` is private session-matched
evidence supplied only from explicit application turn state. It is unavailable
until explicitly set, remains separate from observation ordering and request
tokens, and is not automatically exposed to legacy/provider payloads.

## v15.31 private replay coordinator

Canonical collection evidence remains separate from committed store state until
an explicit private apply call succeeds through CAS; preview is detached and
does not expose a provider payload.

## v15.32 persistence envelope

Durable recovery uses one private schema-versioned envelope for session-matched
detached store state/fingerprint and sorted applied canonical-observation
copies/fingerprints. Its canonical fingerprints exclude wall-clock and request
values. Exact-shape validation, schema rejection without migration, corruption
rejection, and load are non-mutating; saving uses sibling temporary output plus
`os.replace()`.

On JSON load, numeric state slot-map keys are restored before validation, so a
persisted store state remains equal to the detached runtime state. Ledger entry
IDs must agree with their canonical observation IDs; malformed canonical
identity/sequence/session shape is rejected without runtime mutation.

Restore is explicit and same-session only, with no retagging. It first uses
normal store CAS, which retains normal sequence monotonicity, then performs a
single full-map ledger replacement. A replacement failure uses private
rollback-only CAS with a captured pre-restore snapshot and the just-applied
target fingerprint. Concurrent writer conflict produces sanitized
`critical_restore_inconsistency` and preserves that writer. This is persistence
recovery, not user-facing undo/redo. No UI/autosave/startup restore or provider
payload wiring is present.

## v15.38 runtime advice-state projection

Structured-only `battle_input` may contain a validated
`runtime_advice_state` section captured from one matching active runtime
snapshot. `TurnSnapshot.current_state.runtime_advice_state` carries only the
provider-safe `runtime-advice-state-v1` projection: session ID, active Pokémon
identity, HP/max HP, fainted, condition, item, weather, terrain, and both side
conditions. Each fact is explicitly `unknown`, `known_absent`, or `known` with
a value. It is not a raw `battle-state-v1` copy.

The runtime fingerprint is worker-only provenance and is excluded from
`runtime_advice_state`, provider payload, prompt, UI status, and logs. Raw
runtime/store/commands/coordinator/persistence, applied ledger, persistence
envelope/path, CAS/rollback data, request token, and thread metadata are also
excluded. Existing UI-derived fields and collection evidence remain separate;
they do not silently resolve or overwrite runtime projection facts.

## v15.39 grounded structured response

The structured provider payload may additionally contain only validated
`runtime_advice_state`. Fingerprint, request token, thread, ledger, CAS,
reducer, and persistence metadata remain excluded. Runtime-bearing responses
require `grounding-v1` with exact `confirmed_facts`, `unknown_facts`,
`evidence_only`, `conflicts`, and `conditional_dependencies` lists. Canonical
paths use the provider-safe projection shape such as
`opponent.active_pokemon.item` and `field.weather`; unknown is never absence.
Legacy six-field responses are an explicit compatibility lane only and cannot
bypass grounding for runtime requests. Actual provider semantic smoke remains
outside this offline contract.

## v15.41 runtime grounding response alignment

For a request containing `runtime_advice_state`, the provider response schema
requires the legacy recommendation fields plus `grounding`. Its
`schema_version` is `grounding-v1`, and its five exact lists are
`confirmed_facts`, `unknown_facts`, `evidence_only`, `conflicts`, and
`conditional_dependencies`. The decoded boundary preserves that seven-field
shape for the existing adapter and validator. Non-runtime requests retain the
legacy six-field response contract.

Structural diagnostics are bounded categories only; they never carry response
values, fragments, or a complete provider key inventory. Structural errors map
to the existing smoke exit 6, semantic errors to exit 7, and internal metadata
exposure to exit 8.

## v15.42 future mechanics-result boundary

No provider payload changes in this design-only milestone. A future candidate
may carry detached `mechanics-result-v1` evidence only after a project-owned
adapter classifies authoritative snapshot facts. Its status is `known`,
`bounded_range`, `conditional`, `insufficient_context`, or
`unsupported_mechanic`; numeric damage/KO facts are unconditional only for
`known`. Missing EVs, IVs, nature, item, ability, boosts, or HP remain unknown,
not calculator defaults. Package/version provenance, raw subprocess output,
raw descriptions, and raw state data are excluded from provider payloads.

## v15.42 implemented direct mechanics evidence

`candidate_comparisons` may contain `mechanics_result`: `status`, `move`,
`type_effectiveness`, `damage_range`, `damage_percent_range`, `ko_result`,
`missing_inputs`, `unsupported_reason`, `mechanics_source`, and `generation`.
For `insufficient_context`, numeric damage/percent/KO fields are `null` and
only allowlisted logical missing-input names remain. Raw roll arrays,
`DamageContext`, final-stat provenance, bridge output, cache paths, and engine
debug material are forbidden.

## v15.43 mechanics grounding acknowledgement

When a candidate has opted-in `mechanics_result` evidence, the structured
response requires grounding-v1. Each mechanics result is acknowledged only by
its canonical `candidate_comparisons.<index>.mechanics_result` path in
`evidence_only` with `authority: evidence` and `source: deterministic`.
`insufficient_context` additionally uses the value-free `.missing_inputs` path
as a conditional dependency. This is acknowledgement, not a provider-supplied
calculation or raw result echo.

## v15.44 machine-required mechanics acknowledgement

For a direct-mechanics request, the response schema additionally requires a
`mechanics_acknowledgements` list. It contains exactly one value-free mapping
per opted-in candidate: `slot_index`, `move`, canonical `mechanics_path`, the
native result `status`, and `missing_inputs_path` only for
`insufficient_context` (otherwise `null`). The parser validates the exact
candidate/action, canonical path, status, and incomplete dependency; omitted
or mismatched links are semantic failures. The list must not repeat damage,
percent, KO, roll, or other mechanics values, and replaces the duplicate
mechanics path previously required in grounding `evidence_only`.

For one direct-mechanics candidate, the production response schema also pins
its slot, move, canonical path, and status with enum constraints before the
provider responds. Multiple candidates retain the same parser-side exact-link
validation rather than introducing a new response format.

## v15.45 provider diagnostic boundary

The structured Gemini provider boundary is an existing `requests` REST call.
Before provider response parsing, it maps only safe HTTP or requests exception
families to bounded diagnostics: client initialization, model not found,
authentication, permission, quota/rate-limit, timeout, network, service
unavailable, invalid request, response failure, or unknown failure. The direct
smoke prints the allowlisted code only. It never emits a response body, request,
prompt, credential, headers, endpoint detail, exception message, or traceback.
For an explicitly one-call provider diagnostic, the direct runner accepts only
the `complete-direct-mechanics` fixture prefix and requires `max_calls` to
equal the selected fixture count.

## v15.46 request-schema compatibility diagnostics

Non-success provider responses may yield only `http_status`, allowlisted API
status, stage, component, logical field, and schema-keyword category. The raw
error body is parsed transiently for classification and then discarded. The
strict internal response contract remains separate from the provider schema;
the current REST API documents the older `responseSchema` field as deprecated
in favor of `responseJsonSchema`.

The compatibility diagnostic classified the request as HTTP 400,
`INVALID_ARGUMENT`, `response_schema`, `schema_keyword_enum`. Therefore the
provider-facing acknowledgement item no longer contains dynamic candidate enum
constraints. This does not relax internal validation: the parser still checks
the exact candidate/action, canonical path, status, and missing dependency.

## v15.47 native mechanics numeric claims

Claims retain required `kind` and `claim` and may additionally contain a
value-free `mechanics_path` plus `numeric_scope` (`damage_range`,
`damage_percent_range`, or `single_hit_probability`). A known direct-mechanics
numeric claim is valid only if its exact candidate path/scope is present and
its numeric literals equal the selected native range or probability. For
`insufficient_context`, referenced numeric mechanics claims are rejected and
only conditional/insufficient advice remains valid.

For a single insufficient direct candidate, the provider schema description
states the exact canonical `.missing_inputs` dependency path. It is guidance,
not a dynamic enum; the strict parser still rejects any different dependency.

Numeric claim guidance is explicit: all numeric literals must be the selected
native scope values, with no added HKO label, midpoint, rounded derivative, or
cross-candidate number. A non-numeric mechanics summary has no numeric scope
reference and remains valid for known mechanics.
