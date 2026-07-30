# Known Action-Order Slice

This slice adds candidate-level `action_order` evidence without changing the
existing deterministic damage ranking. It evaluates only a known pair: the
self candidate action and an explicitly selected opponent action.

## Authority and order

- Move priority is read from canonical move metadata for both actions.
- Speed is accepted only when each side has a normalized, user-confirmed final
  battle Speed.
- Trick Room is read only from a normalized, user-confirmed current field
  state. A missing or untrusted field is `unknown`, never inactive.
- Higher priority acts first. At equal priority, active Trick Room reverses
  the known-final-Speed comparison; equal Speed is `speed_tie`.

The evaluator returns `acts_first`, `acts_second`, `speed_tie`,
`insufficient_context`, or `unsupported_mechanic`, together with bounded
action references and reason/missing-input fields. Conditional priority moves
are explicitly unsupported rather than silently resolved.

## Boundaries

It does not call the legacy move-order assessment and does not apply Speed
stages, Tailwind, base Speed, items, abilities, status, or opponent-action
prediction. Missing canonical priority, opponent action, trusted final Speed,
or known Trick Room remains insufficient context.

`action_order` is copied into each candidate/provider-safe comparison as
separate deterministic evidence. It does not modify damage, candidate rank, or
multi-move selection policy. Offline validation only; no provider, credential,
or network activity occurred.
