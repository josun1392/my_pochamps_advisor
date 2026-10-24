# Public metadata hierarchy v1

One standalone supervised response predictor, not PPO or a battle opponent.
Keep the predecessor and Foundation unchanged. No BR/advisor integration.

The original public response encoder authenticates one observer's own request
and public projection. Candidate support is unchanged: only moves already
revealed by the apparent current target actor, five unknown-move families and
one voluntary-switch category. No hidden set/slot/legality mask, learnset-derived
assertion of possession or unknown switch destination enters the forward pass.
Actual selected actions and private target masks authenticate labels only.

The new version removes938 known-move-ID context columns. Public move metadata
is shared: type/category, nominal power/accuracy/priority, maintained tactical
status/boost/heal/side-condition fields and flags. Context also receives pooled
revealed metadata/counts. A128/64 context net estimates six family probabilities;
one shared64/1 candidate scorer normalizes within each family. All families have
an unknown candidate (switch has an unknown destination). No trainable move-ID
embedding or output row exists. Identical metadata can remain indistinguishable;
this is explicit approximation, not a full effect interpreter or damage model.
Candidate order is not a feature. Exact identity bindings remain in output keys.

Train only the prior9983 train rows; prior4585 validation rows select among at
most20 epochs (patience4) and fit one global temperature0.5..5. Fresh Adam3e-4,
batch256, unweighted CE, clip5, seed106124. No architecture or class-weight sweep.
The old consumed5113-row test is not a new adoption test or training input.

Before fitting, freeze64 independent pairs/128 full teams from the V8 TRAIN4096
bank, excluding all previous256 full teams and joint species/movesets. Eight
RNG/ordered-bring-three replicas and both real native seats give1024 collection
games. Preserve original seven policies and10/10/10/10/10/30/20 episode mixture,
with fixed integer quota51/51/51/51/51/154/103 case pairs. Fit/freeze the model
BEFORE collecting any new test outcomes. Fresh data are test-only. No old battle
evaluation/sealed panel is used. Species/individual-set overlap is audited, not
called unseen without evidence. Cases and both seats cluster by complete pair.

The shared receipt-bound collector now accepts an explicit validator callback
and bounded game count; historical default1792 contract remains unchanged.
Public dataset extraction has an explicit test-only scope; default three-fold
behavior remains unchanged. Native retry/recharge/timeout/masks are unchanged.
Uncertain started games are not automatically replayed. One failed fit or opened
test cannot be automatically retrained/retested. CPU50%, RAM12GiB,1native worker,
CPU-only,one3600s owner and zero automatic restarts.

Final metrics use identical saved cases/inputs for public heuristic, frozen old
predictor and new model. Primary: pair-equal NLL differences,10000 cluster draws,
95% intervals and97.5% two-baseline intervals. Also Brier/top1/calibration,
families, seat/rival/public completeness, and cold known move labels. GO requires
primary NLL improvement against both baselines, at least100 cold labels across16
pairs with positive top1 improvement CI against the old model, no point Brier/
top1 regression against either baseline overall (or old Brier on cold), safe boundaries and
validation-derived context+network median under5ms. Any metric regression is
reported separately. No cold-label generalization signal or no probability
improvement yields NO-GO; do not answer with another complexity/volume expansion.
Conditional evidence stays CONDITIONAL GO. No result authorizes promotion, PPO
or claims that forecasting improves Best-Response battle strength.
