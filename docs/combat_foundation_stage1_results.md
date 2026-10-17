# Frozen combat foundation Stage 1, 2026-10-17

Status: **COMPLETE for the authorized durable training lineage and evaluations**.
Competitive improvement over categorical V4 is not established.
Stage 2 is **NO-GO pending T1 review**, not automatically authorized.
No checkpoint is promoted and production recommendations are unchanged.

## Identity and budget

- Training source commit: `f16d0a1c1c7ea159c2c7c81c2d79e14e28a94b09`.
- Foundation: `showdown-combat-foundation-v1`, 674,939 parameters.
- Encoder: public categorical V5 integrated-v3, dimension 28,822.
- Native engine: `942cda71d14bf0618bd57991708a2e2734b6daba`, `gen9championsbssregmc`.
- Seed 95017; original B0 V4-transfer initialization, not the 4,096-step smoke endpoint.
- B0 SHA256: `8f1a8b949ca7f8f52c4ecc1bb4b89f9b0999a6eb4a578f8f71b5a6ddda386dee`.
- Final counted trained transitions: **1,048,576**, collected lineage counter: **1,048,576**.
- Adam steps: **32,768**; complete PPO rollouts/updates: **2,048**.
- Immutable checkpoints: initialization plus 32 at the frozen 32,768-transition cadence.
- Endpoint SHA256: `9b3eb94aabea1fb25e75dfdba0b733c2a9acd45434ae368a86e14d8979950ccf`.
- Frozen raw config SHA256: `76699f638cdb181112c3fb9243e5c6e5bc5a3fa79a78fc2d6135a11f5e4f3bc9`.
- Bound config/source/team fingerprint: `39b63808e77cdd55b1dd96f2e719628cc8ce5fd20a85f1ac33b8d14bfaf27599`.

All 41 frozen learning source hashes, objectives, public-information boundaries,
35-action native masks, team subset and opponent slots are unchanged.

## Native evidence and paired performance

Audited training native endings: **82,569**, with 43,466 wins and 39,103 losses,
zero draws/truncations. Audited training plus evaluation endings: **86,729**.
Two controlled mechanic probes were closed nonterminal and are separate.

Each predeclared milestone used 64 canonical validation cases, both native seats,
four frozen rivals and matched candidate/categorical-V4 control: 1,024 battles.
Case-cluster bootstrap retains all seats/rivals, using 2,000 resamples.

| Trained transitions | Candidate wins / 512 | V4 control wins / 512 | Paired difference, 95% interval |
|---|---:|---:|---|
| 262,144 | 254 | 248 | +1.17pp [-6.64, +8.59] |
| 1,048,576 | 283 | 291 | -1.56pp [-8.59, +5.47] |

The final anchor stratum is 64/128 versus control 81/128, a -13.28pp difference
[-22.66, -3.91]pp, without multiplicity adjustment. The small TRAIN probe is
35/64 versus control 40/64, -7.81pp [-17.19, 0]. Direct games against V4 are
73/128 for both candidate and control; raw 57.03% is not evidence of superiority.
Validation teams/joint movesets are separated, not species-unseen. The previous
engineering panel is not reused; final campaign test/rare offset 98171000 remains
unconsumed. Repeated small diagnostics do not select the endpoint or tune design.

## Stability, resources and operational limitations

- Raw gradient maximum 3.672486; clipped maximum .500001256, within .50001 tolerance.
- Policy and Adam restoration match serialized tensors exactly; private auxiliary
  rollout/target arrays are absent from the endpoint ZIP.
- Four CPU workers, one Torch thread; Windows Job hard caps 50% CPU / 12 GiB.
- Peak job memory 6.24 GiB; measured 16-logical-CPU mean 11.60%, sampled max 13.53%.
- Durable-boundary launch wall 8,939.26s; 117.30 trained transitions/s, excluding
  uncommitted interrupted work and the disconnected gap. Rollout/update rate is
  121.84/s. Endpoint inference p50 approximately 7.78ms, p95 approximately 10.2ms.
- Final focused native/foundation/strategic/parallel regression: **82 passed**.

Three same-episode retry alerts caused real STOP/review/resume at 425,984,
688,128 and 753,664. Public masks were legal before native uncertainty refresh;
rejected choices were removed and native progress occurred between retries.
No mask, opponent, objective or alert threshold was relaxed.

Two audit limitations must remain visible:

1. The first operating wrapper omitted the same-episode eight-retry alert.
   Retrospective audit found one missed alert at 32,768. Its eight retries were
   distinct native decisions 22-29 with valid public request updates and a normal
   ending, but the planned automatic stop did not occur at that checkpoint.
2. Launch 3 exited without a final record. Recovery used its verified 589,824 /
   Adam 18,432 checkpoint. Its last heartbeat observed another 15,752 collected
   decisions and 1,267 ended battles, not committed to that model lineage.
   Exact discarded update/execution totals and exit time/cause are unavailable;
   the interrupted launch is not reported as complete. This work is not added to
   the final model's exact 1,048,576-transition count or the audited battle total.

Action/ability NLL and move membership BCE improve over frozen priors on final
unknown-field samples, but action calibration worsens and item NLL does not
improve. Prediction accuracy alone does not justify more combat training.
The frozen endpoint and evidence are preserved; Stage 2 expansion is not run.

## External evidence

Large checkpoints remain outside Git:
`C:/Users/jsp33/.codex/artifacts/pokeadvice-combat-foundation-v1-long-training/seed95017-stage1`.

Detailed Korean report, metrics, curves, manifests and disclosed incidents:
`C:/Users/jsp33/Documents/Codex/2026-10-17/task-pokeadvice-combat-pre-long-training/outputs/stage1`.

Inspect `REPORT_KO.md`, `metrics.json`, `final_integrity_audit.json`,
`interruption_launch03.json`, `EARLY_MONITORING_LIMITATION_KO.md`,
`learning_curves.csv`, the frozen case panels and individual evaluation records.
