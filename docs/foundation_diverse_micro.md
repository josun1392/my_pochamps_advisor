# Foundation diverse-scenario micro PPO

Opt-in contract `foundation-diverse-scenario-micro-ppo-generalization-v1`.
The original 4K and 4K-to-16K contracts retain their budgets and rival lists.
This study reuses their native Gym, immutable Foundation loader, PPO trainer,
rollout/logp/GAE auditor, retry guards, checkpoint writer and real-seat evaluator.
No new actor, critic, objective, feature, optimizer or mechanics implementation.

## Frozen design

- Two independent continuations from original Foundation weights **and Adam**:
  seeds 104031 and 104033, fresh episodes/on-policy rollout and seed RNG.
- Per seed: 16,384 transitions, at most 512 Adam steps, checkpoints at
  4,096 / 8,192 / 12,288 / 16,384. Combined cap 32,768 / 1,024.
- Opponent: immutable original Foundation **argmax only**, as explicitly
  requested. The previous fixed micro used a four-category mixture; therefore
  this experiment does not isolate diversity from every historical difference.
- Eight TRAIN pairs (16 complete V8 TRAIN teams), eight independent pairs
  (16 V8 validation teams), reciprocal team ownership, one deterministically
  frozen ordered bring-three per roster. Both actual native player seats.
- Teams selected by SHA ordering before inference/outcomes; exact complete-team
  and joint species/moveset duplicates excluded, move-slot order preserved.
  Individual species/sets can recur. Prior-plan membership is recorded;
  absence from the available plan audit is not proof of never-seen status.
- Four models, identical 256 cases x two seats = 512/model, 2,048 total.
  All learning completes before the panel is evaluated. Fixed16K is a reference,
  never initialization or a post-hoc best checkpoint. No win-rate headroom gate.
- Main analysis: independent-team differences against Foundation per training
  seed and equal-seed mean; Fixed16K comparisons on the same panel. Bootstrap
  complete team pairs, retaining all directions/seeds/seats/models together.
  Eight independent pairs and two learner seeds provide limited precision.

## Safety and artifacts

CPU-only, four sequential native workers (maintained DummyVecEnv), Windows Job
50% CPU / 8 GiB, 3,600-second process deadline, durable native-start/Adam intents,
STOP checks and immutable checkpoints. No automatic restart or replacing a lost
evaluation. A STOP leaves the last durable checkpoint; any recovery requires
accounting for actual collection/updates/starts before additional execution.
`started.json` prevents duplicate launches. Preflight runs no new native games.
On desktop hosts with a persistent outer Windows Job, inherited-job presence
alone does not establish terminal lifetime. A detached child must first prove
it survives its launcher/tool-shell exit. An append-only operational revision
binds that proof, original plan, old/new runner SHA and zero prior execution;
only the runner's launch check may differ. The child still assigns its own
nested Job with identical hard CPU/RAM limits. This does not promise survival
through OS shutdown or termination of the hosting desktop application's Job.

`scripts/pilot_foundation_diverse_micro.py prepare --output <new-external-dir>
--prior <completed-16k-dir>` freezes source/input SHA, teams, seeds and panel.
Preparation is restricted to the approved pre-implementation HEAD `ca6a495`;
after closure, audit the retained frozen artifacts rather than launching a new
study from the new implementation commit. Any new native run needs approval.
`run --output <same-dir>` executes each seed using the existing micro trainer,
then the four frozen endpoints. External full-player public views and training
labels remain coordinator artifacts; neither private labels nor scenario IDs
enter actor/critic inputs. Original Foundation and Adam are hashed before/after;
evaluation verifies all model and Adam states unchanged. No provider calls,
teacher, branching, production promotion or unbounded followup.

Focused validation: `tests/test_diverse_micro.py`, `tests/test_fixed_micro.py`,
plus existing Foundation, public information, retry and self-play adapter tests.
The final external report must distinguish implementation success, observed
paired change and uncertain generalization. Even positive evidence authorizes
no automatic scaling or model promotion.

## Completed bounded study (2026-10-28)

External artifact: `foundation-diverse-scenario-micro-ppo-generalization-v1-20261028`.
Frozen plan SHA-256:
`fb5c26e5bae390bdf87014330dd8e4ac81c8f319d258e4619d63dd0c78c68268`.
Verdict: **NO_OBSERVED_TRANSFER**. Both seeds completed 16,384 new transitions
and 512 Adam updates; all 2,048 evaluation starts have unique valid receipts.
No evaluation rejection, truncation, draw, replacement or extra run occurred.

| Model | TRAIN wins / 256 | Independent wins / 256 | All wins / 512 |
|---|---:|---:|---:|
| Foundation | 128 | 128 | 256 |
| Prior Fixed16K | 134 | 113 | 247 |
| Diverse 104031 | 192 | 119 | 311 |
| Diverse 104033 | 176 | 96 | 272 |

Independent-team paired changes against Foundation:

- Seed 104031: -3.52 percentage points, team-pair cluster 95% interval
  [-12.11, +3.91].
- Seed 104033: -12.50 points, interval [-21.09, -4.69].
- Equal-seed mean: -8.01 points, interval [-14.45, -1.95].

The corresponding TRAIN gains were +25.00 and +18.75 points. This is evidence
of useful adaptation within the frozen training matchups, without observed
transfer on this independent panel. The negative combined interval is
conditional on eight independent team-pair clusters and these two continuation
seeds; it is not a training-seed population interval or universal regression
claim. The prior Fixed16K used different training opponents and teams, so this
comparison does not isolate diversity alone. No model is selected or promoted.

Each seed retains four checkpoints. Original Foundation and Fixed16K ZIPs and
Adam identities remain unchanged, as do 6,267 files in the prior preservation
manifest. All 64 rollout audits reproduce old logp/value exactly, with maximum
GAE/return consistency error 3.58e-7. Runtime: 396.25 / 385.20 seconds of training
(41.35 / 42.53 transitions/s), 724.85 seconds evaluation, 1,509.58 seconds total;
peak bounded process-tree memory 1.37 GiB, CPU device only.

Legacy checkpoint metadata caveat: the generic checkpoint writer retains
`model_seed=95017` and `curriculum_version=showdown-learning-curriculum-v2`.
Actual execution provenance is the frozen per-seed plan and every native
episode receipt: seeds 104031/104033 and V8, respectively. Keep the original
ZIP/metadata immutable and bind this distinction in an external provenance
addendum. These legacy fields must not be used to reconstruct the study.
