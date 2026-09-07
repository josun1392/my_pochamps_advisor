# Champions sleep/freeze action gating v1

Rule authority: T2-verified Pokémon Champions contract supplied by T1 for this family. No Scarlet/Violet fallback is used.

- Sleep selects duration 2 with 1/3 or 3 with 2/3 at establishment. Each detached branch persists its selected duration; action opportunity n wakes iff n >= adjusted duration. Survival evidence conditions an unresolved duration, never independently rerolls wake every turn.
- Active unsuppressed Early Bird transforms the selected duration using integer floor division by 2. Unknown ability/suppression is incomplete.
- Freeze attempts 1 and 2 thaw with 1/4; survivors remain frozen with 3/4. Attempt 3 thaws certainly.
- Exact user self-thaw move identities bypass natural thaw. Sleep Talk/Snore expose a typed execution handoff; their damage/called-move behavior is not implemented here.
- Target thaw is a separate successful-hit effect. No user-gate classification implies target thaw support.

The existing current-condition authority remains the major-status owner. A narrow reducer observation stores progression on the Pokémon: origin identity, establishment, observed prior action opportunities, optional selected sleep duration, and the current-condition observation it belongs to. This record survives switching; a changed/re-established condition makes stale evidence unusable. Current condition alone never supplies progression.

Runtime gating freezes actor/action, current condition, progression, active ability and suppression, action-order identity and branch path. Cancellation branches have no attack leaves. Cleared-condition branches install an immutable private runtime/D0 view before damage/status/item consumers. No original reducer/runtime/D0 is mutated.

The status-gated pair owner is additive and delegates ordering, attack materialization, intermediate projections and paralysis to existing owners. A fainted actor has no gate attempt. Sleep/freeze-specific ledger validation checks rational branch mass, persistent duration/attempt progression, move exceptions and exact detached changes. Existing generic pair, paralysis and ledger meanings are retained.


## Closure evidence and bounded integration

The implementation adds one reducer event (`record_champions_status_progression`) and one typed pair route. It does not change generic major-condition clearing, generic action ordering, the existing paralysis distribution, damage formulas, or generic ledger replay. The typed status-pair normalizer alone regenerates its frozen request and compares the entire result; this authenticates sequential state, attack leaves, order probabilities and final HP in addition to the local gate checks. Normalized terminal leaves retain cancelled actions as typed events without inventing attack leaves, and remain consumable by the existing descriptive metrics owner.

A selected branch persists both its original duration and the Early Bird transformation evidence. Later changes in suppression cannot reroll that already selected/adjusted duration. A new current-condition observation requires fresh episode-bound progression; an old record is rejected. Unknown progression is never initialized from the condition string alone.

The self-thaw catalog covers burn-up, flame-wheel, flare-blitz, fusion-flare, matcha-gotcha, pyro-ball, sacred-fire, scald, scorching-sands and steam-eruption. Every identity produces a certain, distinct self-thaw execution handoff and a status-cleared detached D0. The existing attack engine remains authoritative for each move's accuracy/damage/secondary support. For example, Scald reaches that engine with condition none and currently returns its pre-existing unsupported critical-hit catalog result; this family does not claim complete Scald damage/secondary support. Sleep Talk/Snore similarly expose the typed gate handoff without implementing called-move selection or Snore damage.

Successful-hit target thaw is separate: a Fire move or a catalogued self-thaw move attacking a still-frozen target requires a target-thaw effect authority and fails closed in this route. Unbound protection, pivot, survival, or other specialized pair extensions also fail closed rather than being silently ignored. Fainting and existing flinch cancellation precede a pending status opportunity. Existing detached paralysis consumption is preserved.

| Goal requirements | Executable evidence in `tests/test_champions_sleep_freeze_action_gate.py` |
| --- | --- |
| Sleep 1–7, 13 | Persistent duration test follows both 1/3 and 2/3 branches through all action opportunities; ordinary Tackle is cancelled without an exception. |
| Sleep 8–10; freeze 24 | Missing progression, foreign active identity, stale condition observation, and real reducer switch/re-entry tests. |
| Sleep 11–12, 14–16 | Sleep Talk/Snore catalog tests, exact Early Bird and Neutralizing Gas cases, adjustment persistence, and original snapshot/D0 equality. |
| Freeze 17–23, 28–29 | Attempts 1/2/3, exact root mass and composed 1/4 + 3/16 + 9/16 path; detached clear and input immutability. |
| Freeze 25–27 | All ten self-thaw identities bypass RNG; forged move classification rejected; actual attack-owner handoff sees cleared status. |
| Pair 30–33 | Ordinary cancellation has no attack leaf, opponent proceeds, wake/thaw attack paths execute, Guts/Facade receive condition none. |
| Pair 34–37 | Opponent-first KO, equal-Speed paths for both conditions, exact mass and typed ledger normalization. |
| Ledger / provenance | Forged actor, action, path, runtime, duration, ability, exception, clear, attack-on-cancel, order mass, later state and final HP rejected; standard descriptive metrics consume valid ledger. |
| Sequencing boundaries | Existing flinch cancels the pending opportunity; target thaw and unbound specialized extensions fail closed. |

Validation policy: focused family tests plus nearest regressions, compilation and exact-path diff-check. No new exhaustive checkpoint is required because the changes are additive and typed. Closing this family advances the post-checkpoint grouped counter from 0 to 1/10–15.

Verified on 2026-09-07: 61 focused tests; 322 nearest regression tests across 42 files. The final focused plus direct-condition check passed all 70 tests. All 11 changed Python files compile. Self-thaw move names were checked against the repository vendor move inventory; probability rules remain exclusively the supplied T2 Champions contract.
