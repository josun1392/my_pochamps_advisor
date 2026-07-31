# v15.75 level-based fixed-damage mechanics

The direct-mechanics boundary now recognizes only the canonical Gen 9 IDs
`seismic-toss` and `night-shade` as level-based fixed damage. Their effective
damage is the trusted user level, not base power or Q12 attack/defense stats.
Known target current and maximum HP produce a deterministic range, percent,
and KO result.

Type immunity is evaluated from the canonical move type and trusted defender
types; ordinary resistance and weakness multipliers are not applied. Unknown
level, target HP, target types, or ability state remains insufficient context.
Known ability modifiers remain unsupported rather than assumed irrelevant.

HP-ratio, random, literal, counter, OHKO, and other special fixed-damage rules
remain unsupported in this narrow path. Candidate comparison uses the existing
final native range only, while presentation labels the selected result as
level-based fixed damage. No provider, credential, or network activity occurs.
