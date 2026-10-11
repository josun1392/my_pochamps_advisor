# Native state compatibility

The approved compatibility direction adds versioned representations;
it does not change the meaning of existing `battle-state-v1` fields, recorded events, replay envelopes,
`champions-sleep-freeze-progression-v1` or the legacy exact gate. Historical
adjusted durations retain their old semantics for their existing consumers.

`showdown-observed-projection-v2` distinguishes unconfirmed legacy `None` from
confirmed absence for items, major status, weather and terrain. Missing values
and canonical Unknown markers also remain unobserved. Explicit current absence,
consumption/removal and the existing authorized status-clear lineage can verify
an absence. Unknown absence slots are supplied only by hypothetical sets and
conditioning; nothing is written back to observed state. Checkpoints from the
older projection fail closed and require reconstruction under the new contract.

`showdown-status-counter-v1` exposes native `start_time` and `remaining_time`,
labeled `hypothetical_native_state_not_observed`. Explicit initialization may
specify those counters in a scenario's native conditioning; this is a modeled
initial state. `showdown-legacy-status-compatibility-v1` retains the full legacy
record. Its `prior_attempts` are not blindly treated as elapsed native ticks.
The native root must match the recorded episode, chosen unadjusted duration
and action attempts. Early Bird progression beyond zero requires matching
native episode history; compatible one-tick counters can verify an explicit
counter hypothesis. A legacy adjusted duration is never assigned to a native
timer. Unknown history or conflicting evidence causes rejection.

In the pinned source, Champions sleep starts at a native counter drawn from
`[2,3,3]`. The inherited status callback decrements twice while Early Bird is
active, once otherwise; native `hasAbility` handles Gastro Acid, Neutralizing
Gas and Ability Shield. Rest explicitly starts at 3. Freeze starts at 3,
decrements on a status attempt and uses native 1/4 thaw RNG until the terminal
attempt. These are counter units, not the number of cancelled moves. The old
`duration // 2` gate applied to initial counter 3 predicts immediate wake,
whereas native execution first cancels as asleep, then wakes on the next attempt.
The new consumer follows native semantics while the old consumer is preserved.

The independent game research reports unchanged Rest timing and the in-game
ability description says twice as fast. Those references describe turns/attempts,
not a serialized timer conversion. Executable native tests cover both duration
values, Rest, sleep exceptions, suppression, freeze attempts and legacy replay
immutability. This avoids treating prose about halved sleep turns as a formula
for a serialized counter.

`evaluate_native_status_gate` enumerates the pinned native status callback's
RNG branches. Probabilities are exact **only for that callback conditional on
the modeled root**. It excludes PP, other BeforeMove handlers, accuracy, targets,
damage and recommendation ranking; it never enters a legacy exact ledger.
The implementation calls the upstream callback, not a Python mechanics formula.

`showdown-decision-phase-v1` exposes native turn, requesting sides and queued
actions and is labeled as a hypothetical native phase. Move, replacement and
pivot checkpoints retain their phase and queue. An arbitrary observed pending
action context is not enough to invent a native action queue; unsupported
partial-action captures remain rejected. Explicit modeled initial conditioning
is applied before scenario history, while current conditioning is applied after
history. Reconciliation retains the initial model and cannot initialize new
effects without native history.

`battle-decision-phase-v1` is a new optional human observation, admitted through
the existing confirmation, collection, reducer, runtime and persistence paths.
It records turn, move/faint/pivot selection, requesting sides and roster-bound
participants. Native projection verifies these against its actual request;
it does not manufacture a native queue from the observation. Any later
observation makes the phase stale for reconstruction until explicitly recaptured.
Historical phase participants can remain in replay after switching. The admission
API accepts only the designated user observation source, never simulator output.
Old sessions without the new record retain their meaning. The Battle menu's
Record Battle Decision Phase dialog requires explicit human confirmation of the
phase, turn and replacement side. Cancellation is inert; repeated confirmation
is idempotent. Admission uses the same reducer and replay path as the core API.
The optional record does not require a native backend or change recommendations.

Observed effects also verify hazard layers (v1 keeps Toxic Spikes and Sticky Web
unknown), Aqua Ring, Ingrain, Leech Seed source position, berry consumption,
last executed move, qualifying hit counts and Taunt/Encore/Disable. Existing
restriction counters are compared at a native move boundary, never assigned
as observed native counters. Mismatching durations or a moved Leech Seed source
fail closed. Initialization reruns native DisableMove/TrapPokemon callbacks
without advancing a turn or touching a paused replacement queue.

`evaluate_native_damage_rolls` reuses the native ModifyType/ModifyMove/TryHit/
getDamage pipeline and enumerates the 16 native damage rolls for a fixed crit
assumption. It supports ordinary single-hit moves and rejects additional RNG,
multi-hit, dynamic power callbacks and unsupported targets. It excludes accuracy,
action gates, secondary effects and HP application/survival; it is never an exact
action/KO probability or ranking fact. The former offline damage oracle now calls
this shared evaluator. Legacy damage formulas remain as regression references.

Primary sources:

- [Pinned Champions conditions](https://github.com/smogon/pokemon-showdown/blob/942cda71d14bf0618bd57991708a2e2734b6daba/data/mods/champions/conditions.ts)
- [Pinned inherited sleep callback](https://github.com/smogon/pokemon-showdown/blob/942cda71d14bf0618bd57991708a2e2734b6daba/data/conditions.ts)
- [Champions in-game mechanics research](https://www.smogon.com/forums/threads/champions-battle-mechanics-research.3780372/)
- [In-game ability descriptions](https://www.smogon.com/forums/threads/champions-battle-mechanics-research.3780372/page-4)
- [Champions Early Bird counter description](https://www.smogon.com/dex/champions/pokemon/kangaskhan/)
