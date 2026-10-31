# Prospective evaluation admission and protocol runner v1

The opt-in runner reuses the existing evaluate_showdown_policy evaluator,
ShowdownEnvironment, player-visible projection, LearnedPolicy loader,
VisibleBaseline, durable_json/StartBudget and ResolvedRequestRateGuard.
No existing opponent, policy, PPO objective or native action rule changes.

The CLI exposes **protocol smoke only**. The frozen 96-case source,
manifest SHA, 1,152-point measure and three opponents remain unchanged.
The source is not consumed by loading metadata or enumerating coordinates;
policy forward/step/terminal execution on those 96 cases is prohibited.

Candidate admission is a predeclared endpoint convention: the existing
fixed-scenario 16K learning-curve final checkpoint, not its validation-best
8K checkpoint. Its ZIP, manifest, parent lineage, objective/feature contract,
Adam archive and prior result receipts are separately hash-bound. Prior
results are already public; this is not a blind historical selection.
Unavailable/incompatible identity means no candidate, not new training.

The smoke uses protocol case 0 owned by team a and protocol case 1 owned by
team b, both real native seats and all three fixed rivals. Two frozen actors
produce 24 base games. The 12 Foundation cells replay once under identical
initial conditions. Maximum native starts are 36, including failed starts;
there is no automatic replacement or restart budget.

An instrumentation repair may preserve a SHA-bound failed intent and skip
that original slot while finishing the remaining original schedule. It must
not replay/replace the failed slot, increase the 36-start cap, count the missing
outcome as a loss, or relabel an unmatched planned replay as the missing base.
Valid results and exact replay pairs must be reduced and reported explicitly.

Admission precedes inference and native reset. Only exact protocol coordinates
and model/rival identities pass. Both real request owners receive their own
authenticated public observations. Source IDs, teams, RNG and other private
coordinator data are never passed to actors. The original T=1 masked argmax
inference path is retained. No training, optimizer step or model saving runs.
The inference envelope retains episode/revision receipt metadata and public
incremental events needed by existing inference and heuristic owners. Those
fields are not additional actor features. Ended observations with zero legal
actions are accepted for trace auditing, never for another policy inference.
Truncated outcomes are durably recorded as invalid terminal evidence; they
cannot become draws/losses or enter the future complete-panel comparison.

A durable intent precedes each game. A result is written from the maintained
evaluator's per-game completion callback, before aggregate summaries.
The evaluator also invokes a second aggregate callback; matching content is
recognized without creating a duplicate result. Verified completed receipts
are reused; an unmatched intent fails closed. STOP is checked before starts
and during play. No silent result replacement, denominator change or replay
is authorized after a storage/engine failure.

Native rejection refreshes retain the existing native request/mask logic and
policy re-selection. Public trace validation requires no executed decision on
rejection, accepted progress resets the consecutive counter, and eight
unresolved attempts stop. The existing refresh classifier keeps raw, resolved
and unresolved counts. A terminal result with unresolved/pending rejection
evidence is not admitted as valid. Real terminal W/L/draw is distinct from
truncation and engine failure; native terminal returns alone are reported.

The future primary contrast remains candidate-minus-Foundation win fraction,
preserving the sealed source contract. Return difference is separate.
Foundation-minus-candidate is also reported as the signed inverse, including
reversed confidence-interval endpoints. Complete matched receipts are required.
All 12 ownership/seat/rival cells stay within each of 96 case clusters for
20,000 fixed-seed bootstrap draws (seed 1610312026). The 1,152 cells are not
independent replicates. Training-seed population uncertainty is not estimated.
Synthetic contract tests do not execute or inspect sealed-policy performance.

A separate T1 approval and frozen candidate/comparison addendum are required
before actual 1,152-point-per-policy evaluation. Protocol wins do not admit a
candidate by strength, select a checkpoint, or establish improvement. No
production promotion or automatic follow-up run is permitted.

The reusable ApprovedSealedRunner uses the same tested game kernel, but refuses
even sealed-coordinate enumeration without a separate SHA-bound T1 approval
receipt. It fixes the original source, reference/candidate identities, T=1,
1,152 points per policy, two policies and 2,304 total starts, with no replay or
replacement. Approval fields are a coordinator provenance contract, not human
authentication or permission by themselves. This task creates no real approval
receipt and never instantiates this class on the real sealed source. Tests use
synthetic coordinates/approval data and do not execute a model or simulator.
