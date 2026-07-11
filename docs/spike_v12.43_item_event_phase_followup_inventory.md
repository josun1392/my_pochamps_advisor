# v12.43 Item Event Phase Follow-up Inventory

## Purpose

Inventory the work that remains after the Item Event Payload Mapping phase and
identify the next large development axis without adding behavior.

## Completed Item Event Scope

- Known items are limited to user-confirmed current context only.
- Known item is separated from activation and consumption.
- Item event source inventory and explicit-user-confirmation design are
  complete.
- `ItemEventDialog` is implemented as the explicit event entry point.
- `LLMAdvicePanel` has an Item event button, and MainWindow owns
  session-local `_item_event_confirmations`.
- Valid event confirmations map into `item_event_context.observed_events` only
  when the existing limited context checkbox is enabled.
- The limited context checkbox is the hard gate.
- Invalid events are omitted; all-invalid input omits item event context.
- Offline production prompt fixtures verify observed-only wording.
- The Item Event Payload Mapping phase is `CLOSED - PASS`.

## Remaining Limitations

The following are not implemented:

- battle log parser item event source
- replay parser item event source
- Turn Engine resolved item effect
- post-turn item state updater
- exact HP or damage calculation from an item event
- RNG resolver or speed/order resolver
- Quick Claw activation resolution
- Focus Sash exact survival resolution
- Berry exact recovery or damage-reduction resolution
- Choice lock state resolution
- controlled actual Gemini smoke for item event context
- item event UI polish or Korean copy

## Option Inventory

### Option A: v12.44 Item Event Actual Gemini Smoke Design

**Purpose:** Design a controlled smoke that verifies the current gated
`item_event_context` keeps observed-only boundaries in a real Gemini response.

**Benefits:**

- Follows naturally after payload mapping and the offline prompt fixture.
- Matches the completed field-state and current-item verification pattern.
- Produces a clear approval-gated path for validating model behavior without
  broadening the item-event contract.

**Risk and prerequisites:**

- This inventory performs no actual call; a later execution task needs separate
  T1/T2 approval, a preflight, one-call limit, and no retry.
- A smoke result verifies response behavior only; it does not resolve mechanics
  or replace parser, replay, or Turn Engine work.

**Recommended order:** First.

### Option B: v12.44 Battle Log Item Event Source Design

**Purpose:** Design how battle-log activation, consumption, recovery, and
reveal observations could become a trusted observed source.

**Benefits:**

- Is the natural automation source after explicit user confirmation.
- Can reduce manual event entry while retaining source provenance.

**Risk and prerequisites:**

- Log formats, event boundaries, provenance, normalization, and malformed-log
  handling need design and contract tests before parser implementation.
- Must remain observed-only and must not imply resolved effects or post-turn
  state.

**Recommended order:** Second, if T1 prioritizes automation over model smoke.

### Option C: v12.44 Status/Condition Source Design

**Purpose:** Begin a source-boundary design for burn, paralysis, sleep, poison,
confusion, and related conditions as known, observed, or resolved information.

**Benefits:**

- Extends the established item/field source-boundary pattern to another major
  battle-information category.

**Risk and prerequisites:**

- Duration, recovery, action prevention, damage, and turn progression can be
  confused with resolved results.
- Requires a separate status vocabulary and source contract before any mapping
  or UI work.

**Recommended order:** Third.

### Option D: v12.44 Damage Calculator Integration Design

**Purpose:** Define the boundary between current `damage_estimate`/Q12 behavior
and any future real damage-calculator integration.

**Benefits:**

- Establishes the design path toward more complete calculation support.

**Risk and prerequisites:**

- EVs, IVs, nature, items, field, status, ability, and unknown-information
  handling have a large correctness surface.
- Must start as design and contract work; it must not alter current damage
  calculations without explicit approval and focused tests.

**Recommended order:** Fourth; broader and higher risk than the source-boundary
options.

## Option Comparison

| Option | Main value | Risk | Prerequisite | Order |
| --- | --- | --- | --- | --- |
| A: Actual Gemini Smoke Design | Validates the completed path against model behavior | Controlled provider-use planning | Existing offline fixture and separate execution approval | 1 |
| B: Battle Log Source Design | Plans the next observed automation source | Provenance and parser ambiguity | Source vocabulary and contract design | 2 when automation is prioritized |
| C: Status/Condition Source Design | Extends source boundaries to conditions | Resolved duration/damage/action semantics | Separate source model and contract | 3 |
| D: Damage Calculator Integration Design | Plans a larger calculation capability | Highest unknown-input and regression surface | Explicit calculator scope and contracts | 4 |

## Recommended Next Step

**T2 recommendation: v12.44 Item Event Actual Gemini Smoke Design.**

The payload mapping phase is `CLOSED - PASS`, so the next natural decision is
to design a tightly controlled real-response verification. The design must keep
actual execution separate: a future v12.45 Controlled Item Event Gemini Smoke
requires explicit T1/T2 approval.

If T1 instead prioritizes automation sources, choose **v12.44 Battle Log Item
Event Source Design**.

## Scope Boundary

This inventory changes no contract or runtime behavior. It does not add a
parser, replay import, Turn Engine, automatic activation/consumption detection,
resolved effects, post-turn state, exact HP/damage/order/RNG calculations, or
hidden-item inference.

## No Actual Gemini Call

- No actual Gemini call was executed.
- No retry, second provider call, Vertex AI call, or network/provider call was
  executed.
