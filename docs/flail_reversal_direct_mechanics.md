# Practical 1.1: Flail and Reversal direct mechanics

Flail and Reversal now consume the existing canonical current-HP bracket
resolver before native direct-Q12 damage evaluation. Exact trusted attacker
current and maximum HP select the canonical base-power bracket; the resulting
damage continues through existing KO and danger consumers.

Missing HP stays incomplete, and malformed, impossible, or fainted attacker
HP remains conservatively unavailable. This changes neither the bracket table
nor other dynamic-power families, and introduces no HP-trigger item or turn
simulation behavior.
