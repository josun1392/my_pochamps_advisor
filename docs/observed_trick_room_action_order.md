# Observed Trick Room action order

Trick Room now has a narrow global field authority path. An explicit trusted
`trick_room_field_observed` lifecycle confirmation may record only `active` or
`inactive`; it is reducer-owned under the session field, never under a side or
Pokémon identity. The initial and unconfirmed state remains unknown.

The detached runtime projection exposes this fact only when its reducer
provenance is an explicit user-confirmed Trick Room observation. The frozen
request projection converts it to the existing canonical
`field_state_context.trick_room` tri-state used by action-order evaluation.
No state is inferred from move use, speed outcomes, Tailwind, or other field
facts. This does not add a general field engine or any new ranking reward.
