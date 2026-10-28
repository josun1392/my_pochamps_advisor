# Controlled matchup recombination micro PPO

Contract `foundation-matchup-recombination-controlled-ppo-v1`, baseline 414dddc.
Reuse the preceding study's exact sixteen TRAIN rosters, sets, move-slot order
and per-roster ordered bring-three. Never modify its models or receipts.

## Matched design

A repeats the preceding eight fixed unordered pairs. B uses four predeclared
perfect matchings (32 unordered pairs); each team has four opponents. A round-
robin factorization of K16 creates the matchings without policy scores or
outcomes. Matching zero is the old fixed pairing. Matching four is held out
in **both directions** for new-matchup evaluation. Another sixteen V8 validation
rosters provide a separate identity holdout, excluding prior known plan teams.

Exact exposure means collected on-policy **learner decision transitions**:
each training roster receives 1,024 as own team and 1,024 as opposing team in
each arm. Battle counts can differ as an outcome of pairing and are audited
separately; no claim of equal completed-episode counts is made.

Both arms use sixteen identical collection segments. Each segment has four
fixed ordered matchups and 256 steps per worker, comprising two unchanged
128-step PPO rollouts (1,024 total transitions). Native episodes may finish/reset
within a segment but the assigned rosters cannot change. After each segment,
close open tails without a terminal reward; the already-computed final rollout
retains the ordinary public value bootstrap. Fresh next-segment observations
begin with SB3 episode-start flags. This common bounded collection regime is
part of the comparison; it is not an uninterrupted reproduction of the prior
experiment. No fake draw/loss/truncation or cross-segment GAE is introduced.

All sixteen teams receive 256 transitions per role in each 4,096-transition
round. Native seeds are addressed by seed/segment/worker/local episode ordinal,
without condition/model identities. Policies can consume different RNG and
finish different numbers of battles after matchups diverge.

Seeds 104039 and 104041, paired A/B. Every arm independently restores the same
original Foundation weights and Adam. Set policy RNG once per arm, preserve
optimizer and RNG between segments; do not share on-policy buffers across arms.
No new feature, reward, PPO loss, entropy, beta, architecture or preview policy.
Opponents remain original frozen Foundation argmax 100% in both arms.

Per arm: 16,384 transitions / at most512 Adam. Total: 65,536 / at most2,048.
Every1,024-step boundary stores an immutable policy/Adam checkpoint and training
RNG for recovery; 4K/8K/12K/16K are the main fixed boundaries. No automatic resume
or extra training. Record accurate V8 and continuation-seed metadata for new
checkpoints; do not rewrite the legacy metadata of historical checkpoints.

## Frozen evaluation and uncertainty

Foundation plus A/B x two seeds; 512 games per model, 2,560 maximum starts.
Per model: 256 new-matchup games and 256 new-identity games. Each scope has
eight disjoint team-pair clusters x both ownership directions x eight native
seeds x both actual seats, against frozen Foundation argmax. All learning ends
before evaluation; no interim outcome selection or case substitution.

Primary: B-A on new matchups per seed and equal-seed mean. Secondary: B-parent
on new team identities, reported separately. Bootstrap full team-pair clusters
20,000 times, seed2026102811, retaining RNG/directions/seats/models/repetitions
together. Eight clusters and two training seeds limit uncertainty assessment.
New-matchup success never substitutes for new-team generalization evidence.

## Boundaries and validation

CPU50%, RAM8GiB, maximum four native workers, CPU PyTorch, no GPU/providers.
One detached process using the already-verified breakaway launch path assigns
its own bounded Windows Job and 5,400-second watchdog. Native-start/Adam intents,
public native traces, masks/logp/GAE audits, episode boundary and quota checks
fail closed. STOP or an actual error leaves immutable partial checkpoints and
actual consumed budgets; no lost work or failed evaluation is silently rerun.

Focused tests cover all120 possible edges, fixed/recombined exact marginal
exposure, reciprocal ownership, holdout exclusion, same own sets and native
seed addressing, immutable budgets, paired cluster analysis, native adapter
contracts and maintained SB3 fresh-episode behavior without learner updates.
Reuse Foundation, micro, public-information, retry and evaluation regressions.
No production promotion or additional experiments in any outcome. If independent
transfer is absent, end this small matchup-study series and return representation,
learning objectives and training scale to T2 review.

## Completed study (2026-10-28)

External artifact: `foundation-matchup-recombination-controlled-ppo-v1-20261028`.
Plan SHA-256: `f8a0c1fdca4533a2ea3082d3e42fc4d311738be71caab09ce50c9d68c086e08b`.
Result: **CONTROLLED_COMPARISON_INCONCLUSIVE**. Neither predeclared transfer
signal passed; no policy promotion or further experiment.

All four arms completed16,384 transitions and512 Adam steps (total65,536 /2,048).
Each team had exactly1,024 collected transitions in each own/opponent role in
every arm. Native battle counts differed, as anticipated. Sixty-four segment
checkpoints retain weights, Adam and training RNG. During the first4K round,
the A/B matchups were identical; parameter **and Adam tensor digests matched
exactly within both seed pairs**. Initial clones also matched logits/value.

| Model | New matchups: wins /256 | New identities: wins /256 | All: wins /512 |
|---|---:|---:|---:|
| Foundation |128|128|256|
| A,104039 |128|112|240|
| B,104039 |130|125|255|
| A,104041 |122|138|260|
| B,104041 |124|128|252|

Primary new-matchup B-A differences:

- Seed104039: +0.78 percentage points, 95% team-pair interval[-4.69,+7.03].
- Seed104041: +0.78 points, interval[-2.34,+4.69].
- Equal-seed mean: +0.78 points, interval[-3.52,+5.86].

On new team identities B-Foundation was -1.17 points[-5.08,+2.34] and
0.00[-3.13,+3.13]; equal-seed mean -0.59[-3.32,+2.15]. Neither direction proves
superiority, inferiority, equivalence or noninferiority. Each scope contains
eight disjoint team-pair clusters; two learner seeds cannot establish a precise
training-seed population interval. Different native panels and the common
segmented collection regime also preclude subtracting the prior study's scores
as a causal estimate.

All2,560 evaluation starts have unique terminal receipts; no missing/duplicate,
draw, truncation, rejection or retry. Training starts6,088 comprise5,576 terminal
episodes,256 unused constructor episodes and256 open tails at segment closure.
No terminal labels were invented for those tails. Total starts including
evaluation8,648. All128 rollout audits had exact old-logp/value/first-ratio
consistency; maximum GAE/return error4.17e-7. Historical original/16K/crossover
and prior diverse artifacts remain hash-identical.

Run wall2,905.54s (48m25.54s); evaluation1,001.03s; training throughput34.18--35.11
transitions/s. Peak process-tree memory1.70GiB, CPU tree2,711.28s, CPU-only.
Prelaunch focused/nearest tests95 passed /3 native-fixture skips, compile and
diff-check passed. Actual approved native execution provides separate evidence,
not a claim that skipped fixture tests ran. New checkpoint metadata correctly
records V8 and continuation seeds; historical metadata is not rewritten.

Stop this small matchup-recombination experiment series. Return observation
representation, learning objectives and appropriate training scale to a single
T2 design review. This result identifies no unique defect or guaranteed remedy.
