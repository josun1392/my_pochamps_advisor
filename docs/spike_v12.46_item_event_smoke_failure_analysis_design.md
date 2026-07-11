# v12.46 Item Event Smoke Failure Analysis Design

## Purpose

Analyze the v12.45 `FAIL - SEMANTIC BOUNDARY` result and define a test-first
correction path without changing runtime behavior, prompts, payloads, tests, or
provider state.

## Preserved and Failed Boundaries

### Preserved

- The pre-call gate, normalization, source/status/confidence, forbidden-field,
  and observed-only guard contracts passed.
- The response did not assert Focus Sash HP=1, a resolved effect, post-turn
  state, RNG result, or final action order.
- The response used uncertainty for a candidate order modifier.

### Failed

- It did not clearly identify the explicit opponent Focus Sash observation as
  separate from the self known Leftovers context.
- It foregrounded unrelated available current-item and battle advice context.
- It included a specific HP damage range, which failed the smoke's required
  narrow observed-event focus.

The result does not prove that the mapper or source contract is wrong. It shows
that the final advice response did not meet the intended salience and
separation requirements.

## Failure Taxonomy

| Candidate | Evidence | Likely cause | Confidence | Production layer | Testable correction | Scope risk |
| --- | --- | --- | --- | --- | --- | --- |
| A. Item event identity separation failure | v12.45 summary says Focus Sash observation and known Leftovers were not clearly distinguished. | The current guard states observed-only limits but does not require an explicit identity/side contrast. | High | Prompt guard and response fixture | Assert distinct known-item and observed-event readback anchors. | Low |
| B. Context prioritization failure | Unrelated available context was foregrounded. | Existing available-item required-mention guard and broad advisor instructions may compete with the event guard. | Medium | Prompt composition | Add fixture expectations for event acknowledgement before optional-context discussion. | Medium |
| C. Response focus failure | The answer did not center the smoke's observed-event question. | The production prompt still asks for a best one-turn action, not a narrow event interpretation. | High | Fixture/question design | Split semantic interpretation from full-advice prioritization fixtures. | Low |
| D. Existing damage-context leakage | A specific HP range was included. | The fixture path contains existing trusted move damage estimates and instructions permit limited estimate use. | High | Fixture input and generic advisor instructions | Build a narrow event fixture that omits move/damage context; separately test full advice behavior. | Low |
| E. Prompt guard weakness | Guard prohibits overclaiming but does not require event acknowledgement or explain relationship to known items. | Missing positive readback/contrast instruction is a hypothesis. | Medium | Item-event guard | Contract-test a minimal explicit contrast guard before implementation. | Medium |
| F. Structured payload labeling ambiguity | Contexts use separate top-level structures but no response-oriented headings/priority contract. | Model may not infer that observed event deserves response salience. | Medium | Payload serialization and prompt composition | Test a named observed-event section before considering ordering changes. | Medium |
| G. Fixture/question ambiguity | One smoke simultaneously assessed event semantics and general advisor output. | The full UI-selected payload includes moves, known/candidate opponent moves, available item contexts, and damage data. | High | Smoke fixture | Use two explicitly scoped fixtures. | Low |

All likely causes remain hypotheses except the documented v12.45 response
behavior and the current production structure.

## Known Item and Observed Event Path

```text
known current item
-> item_profiles
-> battle_state_context.self_active/opponent_active.item

explicit observed item event
-> item_event_confirmations
-> item_event_context.observed_events

both
-> _build_ui_selected_prompt(...)
-> model response
```

Current observations:

- `battle_state_context` guard is placed immediately before the item-event
  guard.
- The item-event guard calls the event explicitly user-confirmed and
  observed-only, but it contains no positive requirement to name its side,
  item, or contrast with known current item context.
- The generic prompt resumes after the guard with extensive damage, KO, move,
  speed, and available-item instructions, then serializes the full structured
  payload.
- The final user task remains generic one-turn action advice; it does not
  explicitly prioritize interpretation of the observed item event.

This structure explains why separation is available in the payload but not
necessarily salient in the response. It does not establish that payload field
ordering alone caused the failure.

## Damage Range Source Analysis

| Question | Finding |
| --- | --- |
| Was damage context present in the input? | Confirmed. The production UI path attaches selected-move damage estimates, and the v12.45 base advice fixture also included established broader advisor context. |
| Was the numeric range an item-event mechanic result? | Not established. The sanitized result does not connect the range to Focus Sash. |
| Was it a trusted calculator value or model invention? | `LIKELY TRUSTED EXISTING DAMAGE_ESTIMATE`, but exact provenance cannot be reconstructed without the prohibited raw response/request review. |
| Was it needed to explain the observed event? | No. The smoke's narrow question was observed-event interpretation, not move damage advice. |
| Did `ko_context`, Q12, or raw rolls cause it? | `UNKNOWN`. No raw provider request or response is revisited in this analysis. |

The correction should not assume the model invented unsupported damage. Instead,
it should isolate whether otherwise permitted damage context is inappropriate
for a narrow event-interpretation question.

## Fixture and Question Split

Future work should separate two concerns:

### Fixture A: Item-Event Semantic Interpretation Only

- Includes the known current item and explicit observed event.
- Excludes unrelated moves, damage estimates, KO context, available item
  contexts, and candidate opponent moves where the production harness permits.
- Evaluates explicit observed-event acknowledgement, known-item contrast,
  uncertainty, and absence of resolved/exact claims.

### Fixture B: Full Advisor Response with Item-Event Prioritization

- Uses the normal UI-selected payload including existing advice context.
- Evaluates whether the model acknowledges the observed event before or alongside
  directly relevant advice without requiring unrelated analysis to disappear.
- Keeps existing damage-estimate behavior separate from item-event mechanics.

The goal is not to suppress all unrelated battle analysis. It is correct
separation, appropriate prioritization, unsupported-detail prevention, and
clear uncertainty.

## Minimum Correction Options

| Option | Expected benefit | Advice-quality risk | Scope | Testability | Prompt change | Payload contract change | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A. Strengthen `item_event_context` section wording | Makes observed-only semantics and acknowledgement clearer. | May add minor prompt verbosity. | Small | High | Yes | No | Recommended candidate |
| B. Add explicit known-item versus observed-event contrast guard | Directly targets the observed failure. | Could force irrelevant repetition when no comparison is useful. | Small | High | Yes | No | Recommended candidate, conditionally scoped |
| C. Add item-event-specific response instruction | Can direct a concise interpretation before general advice. | May over-prioritize event context in broad advice. | Small/medium | High | Yes | No | Consider after A/B tests |
| D. Suppress unrelated damage/KO detail when event exists | Prevents the observed numeric distraction. | Risks degrading normal advice and conflates trusted calculator data with event semantics. | Medium | Medium | Yes | No | Not recommended initially |
| E. Narrow the smoke fixture into a diagnostic prompt | Separates semantic failure from full-advice salience. | Does not improve production advice by itself. | Small | High | No, test fixture only | No | Recommended first |
| F. Reorder payload fields/sections | May improve salience. | Broad, model-sensitive, and hard to attribute. | Medium | Medium | Possibly | Possibly | Defer |

Do not perform a large prompt rewrite. The preferred correction hypothesis is a
narrow semantic fixture first, then a minimal event-specific guard change only
if reproduction tests demonstrate the missing contrast/readback behavior.

## Recommended Test-First Sequence

1. **v12.47 Item Event Smoke Failure Reproduction Contract Tests**
   - Lock Fixture A and Fixture B expectations.
   - Require distinct known-item and observed-event serialization/readback
     anchors.
   - Separate absence of unsupported event mechanics from broad-advice
     prioritization checks.
2. **v12.48 Minimal Item Event Prompt Contrast Design**
   - Choose the smallest A/B/C correction after reproduction tests identify the
     precise missing anchor.
3. **v12.49 Minimal Item Event Prompt Contrast Implementation**
   - Apply only the approved small prompt change with focused regression tests.
4. **v12.50 Item Event Offline Response Fixture**
   - Verify the changed prompt path with mocked provider responses and existing
     optional-context coexistence.
5. **v12.51 Optional Controlled Item Event Gemini Re-smoke Design**
   - Design a new one-call smoke only after offline evidence is green.

Any actual re-smoke needs separate T1/T2 approval. v12.46 grants no provider
execution approval.

## No Provider Call

This analysis uses only v12.44, v12.45, current prompt-builder code, related
offline tests, and payload contract documentation. It performs no Gemini,
provider, credential, token-log, or new experiment operation.
