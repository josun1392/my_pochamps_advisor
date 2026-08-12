# Leftovers at the confirmed first end-of-turn phase

Only a living active Pokémon with exact reducer-owned `known_item=leftovers`,
exact current/max HP, and a confirmed matching first-end-of-turn phase receives
this transition. Below full HP it recovers `floor(max_hp / 16)`, capped at max
HP; at full HP it records a deterministic no-change result. The transition is
identity-bound to the active owner and updates canonical current HP, which then
flows through the existing detached runtime and frozen-state projections.

Unknown item/HP/fainted authority never activates recovery. This narrow rule
does not cover Sitrus Berry, Black Sludge, passive recovery abilities, drain,
item consumption, toxic progression, delayed recovery, or a generic item
engine. No additional suppression interaction is represented by the current
trusted state, so this implementation does not infer one.
