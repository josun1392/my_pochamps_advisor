# v12.48 Minimal Item Event Prompt Contrast Design

## Purpose

Design the smallest prompt-only correction that distinguishes known current
items from explicit observed item events and prevents event readback omission.
This is a design document; it changes no prompt, payload, code, or test.

## Current Guard Analysis

The v12.41 `_build_item_event_context_prompt_guard(...)` is correctly limited
to payloads containing `item_event_context`. It already says that an event is
explicitly user-confirmed, observed-only, and not resolved/exact/post-turn/RNG
or order information.

Its gap is positive response guidance. It does not require:

- an acknowledgement of side, item, and observed event type
- a contrast with current known item context
- protection against unrelated damage discussion replacing the event
  explanation

## Correction A: Explicit Identity Contrast

When valid `item_event_context.observed_events` exists, the prompt should make
the following distinction explicit:

- **Known current item:** user-confirmed currently held item context only; it
  does not mean activation, consumption, recovery, or resolution.
- **Observed item event:** an explicitly user-confirmed event observation; it
  does not establish a resolved effect or resulting state.

For the representative case, self known Leftovers stays current context while
opponent Focus Sash activation stays observed-event context. The prompt must
not merge their sides or meanings.

## Correction B: Required Observed-Event Readback

When one or more valid observed events exist, request a brief acknowledgement
of each event's:

- side
- item
- observed event type
- user-confirmed observation status
- unresolved/exact-result boundary

This is not a requirement to repeat the entire payload or change the full advice
format. It prevents an observed event from disappearing from the response.

## Activation Conditions

The contrast/readback wording is active only when
`item_event_context.observed_events` is a non-empty valid list.

It must be absent when:

- limited context is off
- `item_event_context` is absent
- `observed_events` is absent or empty
- all supplied events are invalid and omitted
- only a known current item exists

## Minimal Wording Candidates

| Candidate | Wording direction | Clarity | Token overhead | Repetition risk | Advice-suppression risk | Testability |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | "Keep known current items separate from explicitly observed item events. Briefly acknowledge each observed event by side, item, and event type as user-confirmed observation only; do not infer its resolved effect, resulting HP, damage, RNG, or final order." | High | Low | Low | Low | High |
| 2 | "Known current items describe confirmed possession only. Observed item events describe confirmed observations only. Briefly state the observed event's side, item, and type before relying on unrelated battle context." | High | Medium | Medium | Low | High |
| 3 | "Observed item-event readback required: side, item, event type, user-confirmed observation, unresolved result." | Medium | Low | Medium | Low | Medium |

Candidate 1 is recommended. It fits the existing guard's prose style, has one
compact contrast/readback instruction, and retains the already-present negative
boundary wording.

## Existing Guard Relationship

| Option | Assessment |
| --- | --- |
| A. Extend existing guard minimally | Recommended. One compact positive contrast/readback sentence in the existing event-present guard avoids duplicate gating and preserves current negative boundaries. |
| B. Keep guard and add separate contrast/readback instruction | Not preferred initially. It risks duplicate wording and unclear placement without adding new conditions. |
| C. Strengthen section headings/labels only | Insufficient alone. Structured labels help tests but do not require response acknowledgement. |

No system-prompt rewrite, broad advice-format change, or payload ordering change
is recommended.

## Damage Context Coexistence

Trusted `damage_estimate` and `ko_context` remain available. The correction must
not delete damage context, prohibit full battle advice, or treat a supported
damage range as an item-event mechanic result.

The narrow rule is: when an observed event is present, unrelated damage detail
must not replace the required observed-event readback. Existing damage
assumption and limitation wording remains unchanged.

## v12.49 Test-First Contract

### Event Present

- Existing observed-only guard remains present.
- New contrast/readback anchor is present.
- Anchor requires side, item, event type, and user-confirmed observation.
- Existing resolved/exact/post-turn/RNG/order non-inference boundary remains
  present.

### Event Absent

- Contrast/readback anchor is absent.
- Item-event-specific wording is absent.
- Existing prompt sections remain unchanged.

### Identity Separation

- Self Leftovers remains a known current item.
- Opponent Focus Sash remains an observed activation event.
- Neither is promoted into the other's meaning or side.

### Damage Coexistence

- Trusted damage context remains available in full advice payloads.
- The contrast/readback anchor coexists with it.
- No contract requires damage context removal.

## Recommended Sequence

1. **v12.49 Minimal Item Event Prompt Contrast Contract Tests**
2. **v12.50 Minimal Item Event Prompt Contrast Implementation**
3. **v12.51 Item Event Offline Prompt/Response Fixture**
4. **v12.52 Optional Actual Gemini Re-smoke Design**

Any actual re-smoke remains separately T1/T2 approval-gated.

## No Provider Call

No actual Gemini/provider/network call, credential check, raw response review,
or token-log inspection is part of this design.
