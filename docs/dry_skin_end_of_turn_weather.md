# Practical 1.1: Dry Skin first-end-of-turn weather effect

With exact observed `dry-skin`, exact current weather, HP/max HP, and a
confirmed first end-of-turn phase, Dry Skin recovers `floor(max_hp / 8)` in
Rain and takes `floor(max_hp / 8)` damage in Sun. Recovery is capped at maximum
HP and Sun damage is clamped at zero. Other exact weather produces no Dry Skin
weather HP effect.

Cloud Nine, Air Lock, and Neutralizing Gas suppress the effect. Unknown
weather, ability, HP, suppression, or materially unordered same-owner residual
state remains incomplete. This adds no generic passive framework and does not
change independently supported Dry Skin direct-damage modifiers.
