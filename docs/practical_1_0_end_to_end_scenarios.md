# Practical-1.0 deterministic end-to-end scenarios

`tests/test_v44_practical_1_0_end_to_end_scenarios.py` is a sanitized integration
fixture suite.  It deliberately crosses the lifecycle/replay, frozen-snapshot,
switch-transition, direct evaluation, and combined-action seams instead of
repeating individual mechanics-helper tests.

The scenarios cover:

- final Move-over-Switch selection when a supported entry hazard proves the
  switch-in faints, plus the established same-danger-tier Move preference and
  a hard-blocked switch;
- switch entry followed by canonical direct incoming evaluation with a trusted
  Focus Sash candidate;
- explicit Tailwind/Trick Room observations flowing through replay and frozen
  field authority to action ordering;
- an explicit same-turn event powering Avalanche, alongside confirmed
  first-end-of-turn Leftovers recovery reaching frozen HP state; and
- incomplete candidate-B typing remaining incomplete rather than producing
  fabricated safe incoming-damage evidence.

This is practical-1.0 integration coverage, not an exhaustive battle
simulation. Broad activation families, toxic-counter progression, delayed
effects, broad weather residuals, and non-damage strategic scoring remain
post-1.0 by design.
