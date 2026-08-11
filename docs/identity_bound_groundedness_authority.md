# Identity-Bound Groundedness Authority

This direct authority records `grounded`, `ungrounded`, or `unknown` for one
exact session/side/slot/Pokémon identity. It is intentionally distinct from the
existing side-scoped grounded context: that legacy context must not prove Arena
Trap legality. Future reducer and frozen-request wiring may populate this
contract; no groundedness derivation or Arena Trap blocker is implemented here.
