# v13.10 Deterministic Drain and Recoil

Move metadata now exposes PokeAPI `meta.drain`: positive integers are ordinary
damage-dealt drain and negative integers are ordinary proportional recoil.
Zero/missing produces no assessment. Actual damage is every deterministic roll
capped by confirmed defender current HP; floor percentage arithmetic produces
the effect range. Confirmed attacker HP optionally caps restoration or yields a
16-roll recoil-KO assessment.

Struggle, Mind Blown, Steel Beam, Chloroblast, and jump/crash moves are not
silently handled by this formula. Abilities, items, Life Orb/Shell Bell,
between-turn effects, hit chance, expected values, immunity resolution, and
turn engine behavior remain excluded. Scope is
`damage-dealt-proportional-drain-recoil-only`.
