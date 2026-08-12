# Trusted same-turn event power

Avalanche, Revenge, Payback, and Assurance now use a narrow, reducer-owned
same-turn event authority in the direct Q12 damage path. Only an explicitly
user-confirmed observation can record one of these predicates for the current
session and turn: the user received qualifying direct damage, the target acted
earlier, or the target lost HP.

Each record carries both subject and target identity. The request snapshot
projects only records with the matching active identities and trusted current
turn; it deep-copies them and discards facts from earlier turns. Switch and
faint lifecycle transitions also discard affected identity-bound records.

The four moves resolve only from the predicate assigned by their canonical
rule: Avalanche/Revenge use received qualifying direct damage, Payback uses
target-acted-earlier, and Assurance uses target-lost-HP. An explicit `false`
observation keeps base power. Missing, malformed, wrong-turn, wrong-identity,
or non-projected authority leaves direct evaluation incomplete. No event is
inferred from move selection, estimated damage, HP deltas, predicted order, or
species data. Other turn-event mechanics and end-of-turn triggers remain
outside this slice.
