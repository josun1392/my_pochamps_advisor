# Experimental tactical checkpoint

Validation-selected seed709, retained on a validation tie with independent919.
CurriculumV4 / encoderV3 / native Showdown942cda71d14bf0618bd57991708a2e2734b6daba.
This improves the synthetic tactical test, not broad/unseen strategic strength.
Default guaranteed-first recommendations are unchanged.

SHA256:986ea2ba562d0b34df50ec2ca88ae3171e37031f6f358e9aa5813ffe01412641.
Catalog: `../showdown_initial_v1/catalog.json` plus the existing tactics catalog.
`model.json` records algorithm/optimizer/source/provenance; `primary_selection.json`
locks all choices before reading final outcomes. `selection.json` is the earlier
secondary league-only plan. Full reports: `../../docs/tactical_decision_result.md`.
`evaluation_summary.json` retains paired uncertainty/strata/affordances/motif results
and raw-result hashes. `experiment_summary.json` records all six learning seeds,
independence correction, actual counts/resources and the complete local raw path.
`readiness.json` proves actual Qt inference and unchanged runtime/default rollback.
`healing_diagnosis.json` preserves the genuine failed-heal limitation.

Policy action probabilities and discounted value are not exact or calibrated
win probabilities. Full-HP healing can anticipate faster damage, so do not make
it an illegal action mask. This checkpoint remains opt-in. Earlier v1/v2/v3
artifacts and the independent811/919/1021 checkpoints remain available.
