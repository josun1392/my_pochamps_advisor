# Black Sludge at the confirmed first end-of-turn phase

This Practical 1.1 slice evaluates only an exact reducer-owned
`known_item=black-sludge` for the living active owner at a confirmed matching
first end-of-turn phase. It uses that owner's reducer-owned current type, never
species or base typing.

- A trusted current type containing `poison` recovers `floor(max_hp / 16)`,
  capped at maximum HP.
- A trusted current type without `poison` loses `floor(max_hp / 8)`, clamped
  at zero. The result records whether that exact transition proves an
  end-of-turn KO.
- Exact Black Sludge with an unknown current type or unknown/impossible HP is
  explicitly incomplete and does not change HP.
- Unknown or unrelated items, and owners already fainted before the phase, do
  not create a Black Sludge transition.

The effect is a single current-phase HP transition. It does not simulate item
consumption, future turns, berries, switching items, generic passive-item
activation, automatic type changes, or unrepresented suppression mechanics.
There is no generic recovery/chip reward or ranking change.
