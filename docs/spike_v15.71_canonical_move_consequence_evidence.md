# v15.71 canonical move consequence evidence

Candidates now carry a separate `move_consequence_evidence` block sourced only
from signed drain metadata, canonical recoil flags, the existing charge-move
fixture, and bounded move-effect identifiers. It labels recoil, drain, charge,
recharge, self-faint, forced switch, and repeated-use constraints without
calculating HP, survival, expected damage, turns, utility, or rank.

The evidence is candidate-local, adds only bounded comparison tags, and is
copied into a validated selected result. Presentation renders Korean labels
without internal metadata or ratios. Missing/dynamic metadata remains bounded
unknown or unsupported evidence. Provider, credential, and network activity
are not used in this slice.
