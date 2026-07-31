# v15.77 known damage-modifier context

## Boundary

Native direct mechanics may consume only request-start, explicitly known
modifier state: `field_state_context.current_field.weather`, the self active
entry in `condition_context.current_conditions`, opponent-owned entries in
`field_state_context.current_field.side_effects`, and the explicit battle
format. This slice supports ordinary rain/sun, attacker burn for physical
formula damage, and target Reflect/Light Screen in known singles only.

## Native application

The Q12 engine remains the rounding authority. Weather uses its existing
weather hook, screens use the existing singles screen hook, and burn is a
bounded `M_HALF` final-modifier hook. Fixed-hit candidates apply the same
native modifier contract to every per-hit roll before the existing exact
convolution. Level-based fixed damage does not enter this modifier path.

## Unknown-first and exclusions

Unknown relevant weather, self condition, screen ownership, or active-screen
battle format produces bounded insufficient context; doubles and other
unsupported formats produce unsupported mechanics. Irrelevant unknown state
does not block a candidate. Ability/item/terrain/stat-stage effects, special
weather, Aurora Veil, screen bypass/removal, and any default inference remain
out of scope.

## Evidence and presentation

Known applications produce only allowlisted `applied_damage_modifiers` tags.
Candidate, result, and presentation layers retain only the selected
candidate's tags and render bounded Korean labels. No multiplier, intermediate
rounding value, provider output, or raw snapshot field is exposed.

## Validation

Offline regression covers rain/sun, burn, target/self/ambiguous screens,
singles/unknown/doubles format gating, fixed-hit composition, level-fixed
non-application, request-start candidate propagation, and presentation
redaction. No credential, provider, or network activity occurs in this slice.
