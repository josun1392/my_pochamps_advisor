# Sandstorm at the confirmed first end-of-turn phase

This bounded Practical 1.1 transition resolves Sandstorm only from reducer-owned
current weather observed as `sandstorm` for the matching confirmed first
end-of-turn phase. It uses identity-bound current type, current ability, held
item, and exact current/max HP; species and base typing are never consulted.

Rock, Ground, and Steel current types are immune. Exact Safety Goggles and the
supported current ability cases Magic Guard, Overcoat, Sand Force, Sand Rush,
and Sand Veil are immune. Exact Cloud Nine or Air Lock suppresses the weather
effect globally unless exact Neutralizing Gas is active. With exact known
non-immune authority, damage is `floor(max_hp / 16)`, clamped at zero.

For a non-type-immune target, unknown active ability, held item, or weather
authority remains incomplete. An already fainted owner is skipped. A lethal
supported tick records guaranteed KO evidence and updates authoritative HP.

This is not a general weather or end-of-turn engine. When another supported
same-owner end-of-turn HP transition or an unresolved burn/poison/toxic
residual would make ordering material, the Sandstorm result is incomplete
rather than imposing an unmodeled order. Snow/Hail, weather duration, delayed
effects, and other residual families remain outside this scope.
