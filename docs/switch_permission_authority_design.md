# Trusted Switch Permission Authority

## Strict T1 policy

Missing restriction evidence is not permission. The direct, frozen authority is
bound to the current self active identity and has `permitted`, `blocked`, or
`unknown` state. New sessions, missing legacy context, stale ownership, and
malformed context normalize to `unknown` / `insufficient_context`.

`battle-state-v1.self_side.switch_permission_context` is written only by the
trusted `set_switch_permission` reducer effect with current-active identity,
session binding, and `user_confirmed_current_switch_permission` provenance.
It does not derive a result from static species/ability/item data, missing trap
observations, a prior successful switch, or provider output. Block reason is
optional and bounded; no mechanic-specific explanation is fabricated.

Any other reducer mutation invalidates the authority conservatively. A switch
also changes active ownership, so the incoming active begins `unknown` rather
than inheriting the previous active's permission. Request projection is
detached; a later live update affects only a later request.

## Candidate integration

`advisor_switch_candidates` freezes the source permission beside separate
target availability. A nonfainted target is selectable only when its current
active permission is trusted `permitted`; `blocked`, unknown, fainted, or
unknown target availability remains represented but nonselectable. The direct
authority answers legality only: it does not execute a switch, assess safety,
derive trapping mechanics, alter move semantics, or rank candidates.

The combined selector can now consume a legitimately selectable switch without
policy changes: lower proven danger may select it; same-tier Move preference
and unresolved equal-switch semantics remain intact. Provider payloads and UI
remain move-only.

## Future derivation

Future trusted mechanics adapters may derive this direct authority from
volatile traps, ability/item/type exceptions, and other switch restrictions.
They must provide explicit current-active/session-bound evidence; until then,
unknown stays nonselectable.
