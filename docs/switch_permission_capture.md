# Trusted Switch Permission Capture

`capture_switch_permission` is the bounded manual observation seam. It records
`가능`/permitted, `불가능`/blocked, or `모름`/unknown only through the current
session's `BattleStateStore` CAS and canonical reducer event. The observation
is bound to the current self active slot/Pokémon identity and uses explicit
user-confirmed provenance; provider inference, species data, and historical
switches are not accepted.

Unknown clears previous authority. New sessions, active changes, and other
reducer mutations remain conservative unknown/invalidation boundaries. Capture
must happen before the request snapshot; later edits affect only the next
recommendation. The resulting runtime state is projected into the existing
switch candidate and combined recommendation flow without provider schema
changes. No UI control or external battle action is added here: the existing
panel has no direct reducer-backed current-active-fact control, so this
controller is the narrow integration seam for a future `교체 가능 여부` input.

## UI control

The advice panel now opens a compact `교체 가능 여부` dialog. Its visible choices
are `모름`, `가능`, and `불가능`, mapping respectively to `unknown`, `permitted`,
and `blocked`. Only the explicit `적용` action calls the capture controller;
initial rendering and programmatic combo selection do not write authority.
The dialog reads the current active owner at open time and failed/stale capture
does not leave a requested value authoritative. Automatic restriction
derivation remains future work.
