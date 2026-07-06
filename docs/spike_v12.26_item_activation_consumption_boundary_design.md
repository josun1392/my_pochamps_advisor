# v12.26 Item Activation / Consumption Boundary Design

## Purpose

Define the boundary between user-confirmed known item context and item
activation, consumption, resolved item effects, and post-turn item state.

The current project can carry user-confirmed item context into advice. That
context is useful for strategy, but it is not proof that an item activated, was
consumed, changed damage, changed move order, or changed post-turn state.

This is design-only. No production code, payload behavior, prompt guard wording,
damage calculation, Turn Engine behavior, dependency file, or provider behavior
is changed.

No actual Gemini call was made.

## Current Known Item Meaning

`known item` / `user-confirmed item` means:

- the user currently knows or explicitly entered the held item
- the item may be sent as current context when the existing gated context path
  allows it
- the item may be used for strategic considerations
- the item source is user input or another explicitly trusted current-item
  source
- the item is not produced by legality, meta, damage, HP, move, or model
  inference

`known item` / `user-confirmed item` does not mean:

- the item activated this turn
- the item was consumed this turn
- the item effect was applied to damage
- the item effect was applied to Speed or resolved move order
- the item effect was applied to priority or RNG
- post-turn item state is known
- hidden item inference is allowed
- opponent set or item inference is allowed

## Non-Goals

v12.26 does not implement:

- item activation
- item consumption
- resolved item effects
- post-turn item state
- post-turn HP from item effects
- damage formula changes
- `damage_estimate` changes
- `ko_context` changes
- Q12 multiplier changes
- raw damage roll changes
- resolved turn order
- RNG resolution
- speed tie resolution
- Quick Claw activation resolution
- hidden item inference
- opponent set or item inference
- payload filtering changes
- prompt guard wording changes
- production code changes

## Why a Boundary Is Needed

Several existing contexts legitimately mention known items:

- recovery context can discuss Leftovers or Sitrus Berry as limited context
- survival context can discuss Focus Sash or Focus Band as limited context
- speed context can include supported Choice Scarf effective Speed
- speed-order context can discuss Quick Claw as unresolved limited context
- battle-state context can carry user-confirmed known items

Those contexts are not item event logs. Without a clear boundary, a model or a
future adapter could incorrectly turn "known Focus Sash" into "Focus Sash
activated", "known Berry" into "Berry was consumed", or "known Quick Claw" into
"Quick Claw changed final move order".

The boundary is:

```text
known current item context
!= observed activation
!= observed consumption
!= resolved item effect
!= post-turn item state
```

## Item State Model

| State | Meaning | Current status |
| --- | --- | --- |
| `unknown_item` | Item is unconfirmed or absent from trusted input. | Supported as unknown context. |
| `known_item` | Current item is user-confirmed or explicitly entered. Examples: `leftovers`, `choice-scarf`, `focus-sash`. | Supported as current context only. |
| `candidate_activation` | Conditions suggest the item could matter, but activation is not confirmed. Examples: Quick Claw could activate, Focus Sash could matter. | Allowed only as limited strategic wording, not a resolved event. |
| `observed_activation` | Activation was observed or explicitly confirmed. Examples: "Quick Claw activated", "Focus Sash endured". | Future-only unless an explicit trusted event source is designed. |
| `observed_consumption` | Consumption was observed or explicitly confirmed. Examples: "Berry was consumed", "Focus Sash was used". | Future-only unless an explicit trusted event source is designed. |
| `resolved_item_effect` | An approved Turn Engine or explicit observation calculated/applied the item effect. | Future-only. |

Only `unknown_item`, `known_item`, and limited `candidate_activation` wording are
inside the current boundary. `observed_activation`, `observed_consumption`, and
`resolved_item_effect` require separate source contracts, payload contracts,
tests, and approval.

## Allowed Sources

Allowed current and future source candidates:

| Source | Allowed item state | Boundary |
| --- | --- | --- |
| `user_confirmed_current_item` | `known_item` only | Confirms the current held item, not activation or consumption. |
| `explicit_user_confirmation` | `known_item`; future `observed_activation` / `observed_consumption` | User must explicitly say the item just activated or was consumed. |
| `battle_log_observed` | future `observed_activation` / `observed_consumption` | Requires explicit battle-log item event text. |
| `parser_observed` | future `observed_activation` / `observed_consumption` | Requires a parser to structure an observed battle-log or event source. |
| `imported_replay_observed` | future `observed_activation` / `observed_consumption` | Requires explicit replay/imported event data. |
| `future_turn_engine_resolved` | future `resolved_item_effect` | Requires an approved Turn Engine that resolves conditions, order, damage, and RNG where relevant. |

`user_confirmed_current_item` is intentionally narrow. It supports known-item
context only. It must not be promoted to activation, consumption, resolved
effect, or post-turn item state.

## Forbidden Sources

These sources must not create item activation, consumption, or resolved item
effects:

- species/common set/meta inference
- damage reverse inference
- HP percentage inference
- move selection inference
- opponent_move_context inference
- turn_order_context inference
- field_state inference
- legality gate inference
- resist berry context inference
- LLM/model guess
- hidden item guess
- "usually runs item X" style inference

They also must not promote an unknown item to a known item.

## Item-Specific Examples

### Leftovers

Known Leftovers:

- can be considered as the current item
- can support strategic recovery discussion
- can say recovery may affect follow-up planning under limited assumptions

Not allowed:

- exact recovery amount for this turn as a resolved result
- post-turn HP calculation
- saying Leftovers already recovered HP
- saying item effect has been fully simulated

### Choice Scarf

Known Choice Scarf:

- can support Speed consideration when the existing supported speed context
  marks the modifier as applied
- can support strategic note that Choice lock may matter

Not allowed:

- exact final move order
- resolved turn order
- opponent selected move
- Choice lock state unless observed or user-confirmed
- claiming the Pokemon definitely moves first

### Focus Sash

Known Focus Sash:

- can support survival possibility as strategic context

Candidate activation:

- when HP is full and incoming damage could be lethal, wording may say Focus
  Sash could matter or may allow survival under limited assumptions

Not allowed:

- Focus Sash activated
- Focus Sash was consumed
- post-hit HP is exactly 1
- damage roll or KO result is resolved
- survival is guaranteed

### Berry

Known Berry:

- can support possible trigger-condition discussion
- can support limited resist/recovery context where existing contracts allow it

Not allowed:

- Berry was consumed
- exact recovery or damage reduction was applied
- exact activation timing
- berry-adjusted KO probability unless a future approved engine supports it

### Quick Claw

Known Quick Claw:

- can support chance-based move-order pressure discussion

Candidate activation:

- wording may say Quick Claw could activate or may affect move order

Not allowed:

- Quick Claw activated
- final move order changed
- RNG roll is known
- activation probability is calculated
- speed tie or order resolver behavior is implemented

## Payload Boundary Design

Currently allowed:

- known item context
- user-confirmed item source
- item name/value
- item source metadata
- limited candidate wording contexts that already exist, such as survival,
  recovery, speed, speed-order, and resist berry contexts

Currently forbidden:

- `item_activated=true`
- `item_consumed=true`
- `activation_turn`
- `consumed_turn`
- `resolved_item_effect`
- `post_turn_item_state`
- `post_turn_hp_from_item`
- `item_damage_modifier_applied` outside existing approved damage item support
- `item_speed_modifier_applied` outside existing approved speed context support
- `quick_claw_activated`
- `focus_sash_triggered`
- `berry_consumed`

Future-only payload candidates:

- `item_event_context`
- `observed_item_events`
- `resolved_item_effects`
- `post_turn_item_state`

Future-only fields require separate design, contract tests, prompt tests, source
contracts, UI/source inventory where relevant, and explicit approval before
implementation.

## Prompt / Response Boundary Design

The LLM may say:

- "known item is Leftovers"
- "Choice Scarf may affect Speed considerations"
- "Focus Sash could matter if conditions are met"
- "Quick Claw could activate, but activation is not resolved"
- "No item activation/consumption has been confirmed"

The LLM must not say:

- "Leftovers recovered HP this turn"
- "Choice Scarf makes this Pokemon move first"
- "Focus Sash will activate"
- "Focus Sash was consumed"
- "Berry was consumed"
- "Quick Claw activated"
- "The item effect changed the exact damage"
- "Post-turn HP is X"

Current prompt guards already contain many adjacent prohibitions around item
consumption, RNG item activation, post-turn HP, exact order, and full outcome.
v12.26 does not change prompt guard wording. The recommended next step is to
lock the boundary with contract tests before any wording or payload expansion.

## Safety Boundary

- Known item is current context only.
- Known item does not imply activation.
- Known item does not imply consumption.
- Known item does not imply resolved item effect.
- Known item does not imply post-turn item state.
- Known item does not imply exact post-turn HP.
- Known item does not imply exact damage.
- Known item does not imply resolved turn order.
- Candidate activation is not observed activation.
- Observed activation requires explicit trusted event source.
- Observed consumption requires explicit trusted event source.
- Resolved item effects require an approved resolver or explicit observation.
- Hidden item guessing remains forbidden.
- Damage reverse inference remains forbidden.
- Species/common set/meta item inference remains forbidden.
- LLM/model guesses remain forbidden sources.

## Future Implementation Path

Recommended staged path:

1. v12.27 Item Activation/Consumption Contract Tests
   - lock forbidden payload fields
   - lock known-item versus observed-event separation
   - lock source acceptance/rejection at helper or payload-contract level
   - lock prompt serialization does not promote known items to resolved events

2. Item Event Source Inventory
   - inventory battle log, parser, replay/import, and explicit user-confirmation
     sources
   - decide which sources can support observed activation/consumption

3. Item Event Contract Design
   - define `item_event_context` or `observed_item_events`
   - define event source, certainty, side, item id, turn/event index, and raw
     observation fields

4. Item Event Helper / Adapter
   - normalize trusted observed item events
   - reject inference-only sources
   - keep resolved effects absent unless separately approved

5. Resolved Item Effect Design
   - only after an approved Turn Engine or explicit observation model exists

## Test Recommendations

v12.27 contract tests should cover:

- `known_item` does not emit activation or consumption fields
- `user_confirmed_current_item` maps only to known current item context
- forbidden activation fields are absent from default payloads
- forbidden consumption fields are absent from default payloads
- `quick_claw_activated`, `focus_sash_triggered`, and `berry_consumed` are not
  emitted from current known-item sources
- damage reverse inference cannot create item events
- HP percentage inference cannot create item events
- species/common set/meta inference cannot create item events
- legality gate and resist berry contexts cannot become consumption sources
- candidate activation wording remains non-resolved
- observed activation/consumption remain future-only until a trusted event
  source contract exists
- existing payload contract and battle-state tests remain green

## Next Recommendation

Recommended next:

- v12.27 Item Activation/Consumption Contract Tests

Reason:

- the boundary is now documented
- the safest next step is to lock known-item versus activation/consumption
  separation in tests before any implementation or prompt wording changes

Alternatives:

- v12.27 Item Event Source Inventory
- v12.27 Status/Condition Source Design

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, or
network/provider call was made for v12.26.
