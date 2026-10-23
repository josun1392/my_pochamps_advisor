# Public tactical exchange opponent v1

This opt-in opponent is a bounded conditional exchange heuristic, not native
truth, an optimal-action oracle, a damage authority, or a learned model.
Existing opponents, masks, rewards and default mixtures remain unchanged.

## Bounded design, before validation outcomes

Reuse `VisibleBaseline(tactical_heuristic)`, the V4 public strategic projection,
authenticated own request HP/stats, pinned move metadata and V5's existing
`reference_features`/damage-reference owner. Existing learned opponents infer
through their own versioned encoders; their checkpoints are immutable.

The missing mechanism addressed here is comparing an attack's opportunity cost
with spending a turn switching or healing, conditional on bounded public-legal
opponent attack hypotheses. The old scripted matchup estimates use species/base-stat
priors and HP thresholds without such an exchange. Do not query opponent
requests, checkpoints, real sets, RNG, or future actions. Revealed attacks are
prioritized, then the pinned legal species learnset and existing train-only
marginal frequencies select up to three possible attacks. An unrevealed legal
possibility is explicitly a hypothesis, never an asserted move in the real set;
a revealed move is not asserted certainly selectable now. The mechanics owner
receives hypotheses in a separate opt-in argument; legacy encoder defaults
remain revealed-only. Public observations/known_moves are never forged.

Evaluate two decision rounds, with independent low/high conditional damage
endpoints and possible action-order hypotheses. Switching consumes the first
own action and uses an unboosted entry reference, then an available own attack
reference in the second round. Supported immediate self-recovery consumes its
turn. Compare surviving HP balance, with terminal depletion scored separately.
Select the best worst-scenario utility, breaking ties by mean scenario utility
and the unchanged baseline. These utilities are not win probabilities. Ranges
are conditional neutral-unknown-modifier references, **not bounds on actual
damage or KO**. Neither endpoint combinations nor action-order hypotheses have
a claimed probability distribution.

Only ordinary fixed-power supported moves and explicitly supported own direct
recovery are modeled. Unsupported effects, ambiguous Illusion/stat templates,
hazard entry, transformation choices and missing incoming references use an
explicit legal baseline fallback. Publicly revealed immunity can be used;
unknown immunity is never declared absent. Baseline setup/status choices remain
available through the fallback. This is deliberately not a full effect engine.

Each decision exposes its public rationale, conditional scenarios, assumptions,
fallback reason, legal choices, and baseline disagreement. No new policy input
or private label is introduced.

## Native budget and freeze

- New PPO: zero; no independent-model 5,760-game budget is used.
- At most 128 development/contract native starts, including partial fixtures.
- Final: 224 frozen case clusters, 112 training-256 distribution and 112 V8
  validation-bank team cases, both real native seats, two rivals: new candidate
  and unchanged `tactical_heuristic` = 896 games. Total ceiling 1,024.
- Same frozen Foundation, initial native seeds, own-team/seat mapping and masked
  argmax. Keep final cases separate from design fixtures, previous evaluations,
  and sealed final data. Disclose complete-team and individual-set reuse.
- Freeze source, candidate settings, cases and model hashes before final games.
  No tuning from final outcomes and no automatic replacement games.
- One-worker CPU evaluation; own Windows job CPU <=50%, RAM <=12 GiB, CPU only.
  Detached execution, per-game durable start/commit receipts, no auto restarts.

## Adoption decision

`CONDITIONAL GO` requires correctness/privacy/legality and complete receipts,
nontrivial traceable behavior differences, multiple public tactical examples,
manageable latency, and a harder challenge than the comparator: the paired
Foundation win-fraction difference (candidate minus comparator) has upper 95%
case-cluster bound below zero overall, with no positive held-out point change.
Otherwise `NO-GO` for adding this candidate to the learning pool. Two seats and
both rivals are retained in each bootstrap case. Subgroup results are
descriptive. Success never authorizes PPO training or model promotion.

## Development gate evidence (before final outcomes)

The first revealed-only development slice had 0 comparable decisions in 188
move requests across 16 games. Thus that restriction cannot supply useful new
exposure. The same exchange candidate's public response-construction seam was
completed with the explicit legal-hypothesis path above, before any final game.
No final-outcome-driven coefficient search or alternative candidate pool is used.
