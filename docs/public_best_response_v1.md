# Public-observation bounded response opponent v1

Identifier: `public_observation_best_response_v1`. Opt-in only; no production
advisor, legacy baseline, encoder, reward, PPO or model changes. Validation does
not authorize training against this candidate or adopting a learned model.

## Decision contract

`PublicBestResponseOpponent.act()` accepts exactly the acting player's existing
native public view. Own request role/identity reconciliation and the 35-bit
native legal mask are checked. No simulator, scenario, opposing request,
Foundation inference, checkpoint, private labels or native RNG is an input.
Within the captured process the reported selection distribution is one-hot, not an
estimated win probability. Administrative/forced requests use the unchanged
legal tactical fallback.

Unlike `public_tactical_exchange_v1`, comparison does not require the tactical
baseline's choice to have an available damage profile. Each supported own move
or switch is evaluated against the **same bounded response set**:

- Up to four revealed or canonically learnable attack hypotheses, prioritized
  by public TRAIN-only species marginals with type coverage.
- At most one recovery and one status hypothesis when publicly plausible.
- At most two **previously observed living bench identities**. Public preview
  alone never establishes which three were selected or an unseen bench's HP.
- Publicly established recharge, Taunt and trapping constrain these hypotheses.

Revealed attacks have scenario weight 2, other hypotheses weight 1. These are
declared comparison weights, **not calibrated action/set probabilities** and not
assertions of actual private legality, PP or selection. Unrevealed individual
move support does not constitute a reconstructed jointly legal hidden set.

Reused damage/stat/type/ability/item/field owners compute conditional references
from exact own request stats and independent legal opposing stat endpoints.
The damage endpoints are averaged and adjusted by nominal accuracy. Unknown
ability/item effects are neutral **only within this explicitly conditional
reference**; they are not established absent. Known immunity and public current
typing are used. This is neither exact damage prediction nor an actual KO bound.

The response game models one joint turn, including lost attack opportunity on
a switch, damage to the arriving member, capped healing, order-dependent KO,
nominal recoil/drain, and a discounted nominal future matchup. Positional
bonuses for supported status/setup are heuristic. Ranking is 0.75 scenario mean
+ 0.25 worst scenario; equal scores preserve the tactical choice then native
action index. No random disagreement injection or learned-opponent oracle.

## Explicit boundaries

This is a finite approximate response model, not a full Dex effect interpreter
or native search tree. It does not predict hidden sets, secondary effects,
criticals, all residual/entry abilities, delayed effects, or exact execution of
conditional/callback moves. Variable-power/charge/multihit references are
explicitly nominal. Uncertain speed modifiers retain order ambiguity. Public
Substitute is distinguished from direct HP damage. Exact post-transformation
stats are not fabricated: legal transformation aliases use a flagged
pre-transformation reference. Complex unsupported effects, copied stats or
Illusion ambiguity can invoke fallback. Unsupported candidate effects are
recorded rather than described as optimal or impossible actions.

`last_decision` retains the baseline and chosen indices, legal indices, each
response's evidence basis and unknown availability, conditional damage
references, per-pair positional utility, aggregate scores, omitted candidates,
fallback and timing. Full public input is preserved separately by the evaluation
coordinator. Neither the native result nor the other side's public view is
passed into the decision owner.

## Reuse and integration

- Existing V4 public projection, own identity, public boosts/side conditions.
- Existing V5 conditional damage/stat references and TRAIN-only public priors.
- Pinned native Dex metadata exporter; no Battle creation in that exporter.
- Existing `LearningEnvFactory` gains one explicit identifier. Historical names
  and default configurations retain their old construction and seeding.
- Native evaluator, actual-seat/team assignment, frozen loaders, retry monitor,
  resource owner and durable receipt audit are reused.

No third-party code is copied. Existing dependency/license requirements remain
unchanged; the new exporter reads the already pinned native runtime.

## Bounded validation

Artifacts are external under
`C:/Users/jsp33/.codex/artifacts/foundation-public-observation-best-response-v1-20261024`.
The authoritative pre-execution contract is **`revision_02_plan.json`**. The
unexecuted first plan is preserved: revision 02 corrected an individual-set
overlap-report comprehension, without changing cases or candidate behavior.

Before native final results, compare 565 consumed public states from 96 distinct
legacy trajectories against both existing opponents. These are convenience
sample design diagnostics, not fresh generalization evidence. Versioned final
decision evidence and latency are preserved separately from earlier development
arithmetic checks.

Final panel: 176 new initial cases (88 TRAIN256 probes, 88 V8 validation team
cases), two real seats, two frozen combat models (Foundation and original V4),
and candidate versus unchanged tactical opponent: **1,408 games**. The global
append-only ledger also counts all development native starts; total cap 1,536.
No old calibration/final games are re-executed. No sealed panel is used. New case
seeds do not establish unseen species/sets or identical downstream RNG after
actions diverge. The one-time diagnostic panel becomes consumed.

Predeclared adoption requires public correctness, meaningful broad differences,
manageable cost, a positive case-cluster 95% lower bound for candidate-minus-
tactical win rate against Foundation, nonnegative held-out and alternate-model
point differences, and no single-case dependence. Otherwise **NO-GO**. A passing
candidate is only a potential future matched PPO experiment, not a promotion.

The owner runs one CPU worker under a 50% CPU/12 GiB Windows job and a 3,600-second
deadline. Started-but-uncommitted games are never automatically replayed.
`--resume` only resumes fully audited durable receipts. No automatic restarts,
PPO transitions, model generation, reward changes or model selection occur.

## Completed validation: NO-GO for PPO inclusion

The 1,408 final games completed without rejection, draw or truncation. All
receipts and trace hashes passed audit, and Foundation/V4 parameter, ZIP and
Adam identities were unchanged. Eighteen development native starts bring the
total to **1,426/1,536**, not 1,426 completed final games. No PPO ran.

The following are **opponent win rates**, each from 352 games / 176 case clusters:

| Frozen player | New opponent | Tactical baseline | New minus tactical, cluster 95% |
| --- | --- | --- | --- |
| Foundation | 158/352, 44.89% | 169/352, 48.01% | -3.13pp [-9.09,+2.84] |
| Original V4 | 166/352, 47.16% | 177/352, 50.28% | -3.13pp [-9.38,+3.41] |

Foundation held-out-team difference was -5.11pp [-14.77,+4.55]; V4 held-out
difference -2.84pp [-11.93,+6.25]. Neither superiority nor inferiority nor
equivalence is established. The predeclared adoption gate fails. No policy was
promoted and the experimental identifier remains disabled in default mixtures.

On 565 consumed design states, comparison applied to 511 (90.44%) and changed
169 actions (29.91%), across 75/96 cases. On the candidate's final trajectories
it compared 6,105/7,582 move decisions and differed from the shadow tactical
choice 2,156 times (28.44%). This establishes broader behavioral differentiation,
not better decision quality. Recovery, switch and defense opportunities and
executions are separately preserved in `public_execution_analysis.json`.

Measured outer scoring latency was median 2.55ms / p95 3.61ms on the design
states; final execution took 841.797s (1.67 games/s), peak job memory 0.642 GiB.
Both rival groups included the same BR shadow instrumentation. These game rates
are not an isolated PPO-training-overhead benchmark.

Reproducibility limitation found in the closing audit: equal-key move hypotheses
come from a Python set without a lexical last tie-break, and the evaluation did
not bind `PYTHONHASHSEED`. Across 40 retained public examples, hash seeds 0/1
changed four response lists but no selected action; both matched the captured
actions. This does **not** establish cross-process equivalence on arbitrary
states. Captured responses/choices remain fully auditable. The evaluated policy
was left unchanged after final results; no post-hoc repair or retuning is
represented as having those battle results. Bind stable hypothesis ties before
any future reuse study. This is an additional expansion-readiness limitation,
not evidence that it caused the observed performance difference.

The approximate response model also omits important execution conditions and
exact transformed stats and can average away action-order/KO risk. A preserved
Moonlight attempt at 36/202 HP was preempted by a public Hyper Beam KO; a separate
Morning Sun example healed successfully after taking damage. Neither action is
an oracle-labeled optimum. Static possible-move scenarios need a calibrated
public response model before this approach merits another learning comparison.
