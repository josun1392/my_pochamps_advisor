# Independent confirmation of the frozen 16K endpoint

This opt-in contract is distinct from the consumed 96-case source. It admits
exactly 288 new cases, 576 full teams and 1,152 distinct owner/seat native seed
vectors. Each case retains the existing two team owners, both actual seats,
ordered bring-three and three frozen rivals. There are 3,456 points per model,
each with mass 1/3,456, and at most 6,912 native battle starts for two models.

IndependentConfirmationSource reuses ProspectiveEvaluationSource's maintained
scenario mapping, external asset containment and policy-hash checks. Three
predeclared 192-team calls to the same pinned native TeamValidator generator
produce the source. The batches must join exactly; no rejected or duplicate
source is refilled. Full-team signatures preserve set facts and ignore roster
and move ordering. Historical case/full-team/seed overlap prevents admission.
The original 96-case source and its identities remain immutable.

IndependentConfirmationRunner changes only the authority/support/budget gate.
Its run method is the existing ApprovedSealedRunner.run, which delegates to
the unchanged ProtocolRunner.run native game kernel. Inference, policies,
feature encoders, native masks, seat remapping, rewards and terminal validation
are not modified. There is no extra protocol battle or automatic restart budget.

The two original ZIPs, optimizer archives, public feature contracts and T=1
argmax choices are hash-bound before inference. Only authenticated own public
observations reach each actor. Source identities, complete teams and RNG stay
in the coordinator/native reset. PPO/Adam updates, fitting and promotion are
forbidden. Rejection, failure, missing result, truncation, STOP or resource cap
ends the comparison without replacement, reweighting or incomplete win rates.

Before outcomes, the external construction contract freezes team-generation
and battle seeds, cases and ordered threes, exclusion evidence, model/rival
identities, CPU 50%/RAM 12GiB/CPU-only limits and a 120-minute execution cap.
The primary statistic is new-panel D=G_16K-G_Foundation. All 12 cells remain
in each of 288 case clusters for a predeclared percentile bootstrap. Success
requires the new-panel 95% lower endpoint strictly above zero. Any combination
with the already examined 96-case panel is secondary and cannot determine
confirmation. Two panels do not establish a training-seed population effect.

Novel complete teams do not imply unseen species or individual sets, nor a
sample from the historical TRAIN prior. Exclusion is limited to retained,
auditable artifacts; missing/deleted/manual-use histories are not certified.
All native data/models/results stay outside Git. There is no production route
and no automatic follow-up learning or evaluation.
