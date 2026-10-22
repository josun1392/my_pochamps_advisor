# Native decision progress retry guard

This is a versioned **operational** repair, not a learning-method change.
`retry_monitor_version: native-decision-progress-retries-v1` explicitly selects
`ProgressRetryMonitor`. Existing configs without the field retain the historical
episode-total monitor. The operations journal/accounting versions are unchanged.

## Evidence and behavior

The stopped A-96021 checkpoint preserved 12 rejected attempts at native decision
points 50 through61. Each rejection had a different advancing native decision;
the battle ended normally at66. The old guard counted eight revisions across
the whole episode and stopped after the checkpoint, even though no request was
stuck. The exact native error text/full transport envelopes were not retained.

The new guard keys episodes separately, deduplicates retries by client revision,
and counts an unresolved run at one `native_decisions` value. An increase in that
counter is evidence of an accepted native commit and resets the run. A read-only,
coordinator-only episode cursor also resets a pending run at the checkpoint when
normal progress occurred without another rejection. It never enters Gym actor
observations or policy info. Public mask,
`maybeDisabled` or `maybeTrapped` updates alone do **not** reset it. Eight rejected
attempts without native progress still alert and stop through the existing trainer
STOP path. The native service's32-consecutive-rejection limit remains unchanged.

Telemetry separately records whole-episode totals, maximum unresolved run,
accepted-progress resets and last observed native point. Ended-episode totals are
written to `operational_monitor.json` before being retired from pending state.
Across checkpoints, pending runs survive serialization. On a real process resume,
the existing trainer retires pending native episodes because they are not exact
mid-episode restores. New native episodes start a new run; historical records stay.

Counters describe observed retry records at checkpoint inspection, not a claim
that an old last-failure state remains currently blocked. Rate-above1% and illegal
pre-request-mask alarms are unchanged. Missing/regressing progress evidence fails
closed. Opponent action selection, request projection, masks, rewards and PPO are
not modified.

## Source identity and explicit recovery

Changing the operations module, source trainer and coordinator-only episode
cursor changes categorical learning
source hashes and configuration fingerprints. An old frozen plan must reject the
new source; do not replace its hash or edit its saved STOP/state in place.

The external repair preparation creates a **new** plan/config/output namespace,
records old/new source hashes and adds only the explicit retry contract to all
four arm configs. A copied A-state records an explicit configuration-fingerprint
migration while continuing to reference the original immutable98,304-transition
checkpoint and Adam35840. All learning counters, original262,144-per-arm targets,
model settings and opponent/team identities remain unchanged. Original state,
configs, model files, STOP and evaluation plan are preserved byte-for-byte.

Prepared path:
`C:/Users/jsp33/.codex/artifacts/foundation-team-scale-retry-progress-repair-v1-20261022/revision_02`.

The earlier preparation in the parent directory is retained as superseded,
unexecuted evidence. It cannot pass the final source fingerprint.

A has163,840 transitions remaining. Three other arms have262,144 each, giving
950,272 remaining and the unchanged1,048,576 total main-study ceiling. Future
execution must use the new plan and explicit `--resume`: the copied A-state resumes
the original model/Adam/counters; other arm directories start from their declared
common parent. It is not a fresh optimizer or an uninterrupted RNG/native rollout.

No training is launched by preparation. The user must authorize the actual restart.
The separate reference evaluation and its sealed results are not changed or rerun.
Its frozen native policy/encoder/engine sources and model ZIPs are unchanged; only
learning operations/checkpoint telemetry code changes.
