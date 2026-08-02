# Known Action-Order Slice

This slice adds candidate-level `action_order` evidence without changing the
existing deterministic damage ranking. It evaluates only a known pair: the
self candidate action and an explicitly selected opponent action.

## Authority and order

- Base move priority and category are read from canonical move metadata for both actions.
- A user-confirmed current Prankster applies `+1` only to its own status-category action. A user-confirmed current Gale Wings applies `+1` only to its own Flying-type action when a request-start exact HP snapshot confirms that side is at full HP. Dark-target move success is not evaluated here.
- Speed is accepted only when each side has a normalized, user-confirmed final
  battle Speed.
- Trick Room is read only from a normalized, user-confirmed current field
  state. A missing or untrusted field is `unknown`, never inactive.
- Higher effective priority acts first. At equal priority, the evaluator applies
  Speed stages, paralysis, Choice Scarf, supported matching weather abilities,
  and side-owned Tailwind before active Trick Room reverses the known-final-Speed
  comparison; equal adjusted Speed is `speed_tie`.

The evaluator returns `acts_first`, `acts_second`, `speed_tie`,
`insufficient_context`, or `unsupported_mechanic`, together with bounded
action references and reason/missing-input fields. Conditional priority moves
are explicitly unsupported rather than silently resolved.

## Boundaries

It does not call the legacy move-order assessment or apply Dark-type Prankster
failure, Triage, Stall, Mycelium Might, priority blocking,
ability suppression, duration mechanics, or opponent-action prediction.
Missing canonical priority/category, relevant ability, opponent action,
trusted final Speed, or known field/side authority remains insufficient context;
known relevant unsupported priority abilities remain unsupported.

`action_order` is copied into each candidate/provider-safe comparison as
separate deterministic evidence. It does not modify damage, candidate rank, or
multi-move selection policy. Offline validation only; no provider, credential,
or network activity occurred.
