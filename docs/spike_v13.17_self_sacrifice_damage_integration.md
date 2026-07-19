# v13.17 Self-Sacrifice and HP-Cost Consequences

The explicit allowlist resolves only the user's consequence: Explosion,
Self-Destruct, Misty Explosion, Memento, Healing Wish, and Lunar Dance always
produce `self_resulting_hp=0` / `guaranteed_self_faint`. Opponent damage,
Memento stat drops, replacement, and delayed Healing Wish/Lunar Dance recovery
remain outside scope.

Steel Beam, Mind Blown, and Chloroblast use confirmed maximum-HP half cost:
`max(1, floor(maximum_hp / 2))`, capped against trusted current HP. Struggle
remains unavailable (`unsupported_self_damage_rule`) and never uses generic
drain/recoil. The result is independent from Final Gambit, ordinary recoil,
and normal damage under `explicit-self-sacrifice-and-hp-cost-only`.
