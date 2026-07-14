# V12 Phase Review

## Delivered Trusted Context

| Feature | Source boundary | UI/session and payload | Prompt, acknowledgement, evaluator | Offline / actual evidence |
| --- | --- | --- | --- | --- |
| Known current item | Existing user-confirmed item profile only | Existing item selector and `item_profiles` | Existing item guards; no dedicated structured line | Existing contracts; not a v12 acknowledgement smoke category |
| Observed item event | Explicit user event confirmation only | Session list and `item_event_context` | Observed-item-event line; exact set and forbidden resolved-effect checks | Matrix green; v12.71 and v12.77 evidence |
| Current condition | User-confirmed present state only | Side-keyed session and `condition_context` | Condition line; exact set and timing/inference checks | Matrix green; v12.71 evidence |
| Current ability | User-confirmed current identity only | Side-keyed session and `ability_context` | Ability line; exact set and activation/inference checks | Matrix green; v12.77 evidence |
| Current stat stage | User-confirmed side/stat -6..+6 only | Side/stat session and `stat_stage_context` | Stat-stage line; exact set and cause/exact-result checks | Matrix green; offline only |
| Current field state | User-confirmed field snapshot only | Snapshot session and `field_state_context` | Weather/terrain/global/side lines; exact set and duration/source checks | Matrix green; offline only |

Limited-context gating retains session state while removing v12 trusted inputs
from battle input, normalized payload, prompt guards, and acknowledgement
expectations. The deterministic parser exact-compares normalized expected
entries. The sanitized CLI consumes the same production prompt path and emits
only its fixed safe JSON schema.

## Known Limitations And Deferred Work

- Context is user-confirmed; there is no automatic detection or inference.
- No parser, replay importer, or Turn Engine exists for observed transitions.
- Opponent moves and sets are not inferred as confirmed battle state.
- EV/IV/nature/item/final-stat inputs are not fully connected as deterministic
  battle calculation inputs.
- Current stat stages and field trusted contexts are not connected to core
  damage or speed calculations.
- Exact battle damage, full KO/OHKO/2HKO truth, post-turn transitions,
  remaining duration, final order, and RNG resolution are out of scope.
- Actual smoke evidence is limited to structured condition/item and combined
  ability fixtures; stat-stage and field contexts have no individual actual
  smoke evidence.

## V13 Entry Point

**Final Battle Stat Input and Calculation Boundary**

V13 should connect explicitly user-confirmed deterministic inputs to decision
support: final stats or EV/IV/nature/item input, a stat-stage application
boundary, weather/field/ability/item modifier policy, and a deterministic
damage/speed input contract. The LLM should consume those produced results,
not infer or calculate them.
