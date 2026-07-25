# v15.14 Structured Ability Provenance Producer

## Inventory

| Path | Meaning | Structured policy |
| --- | --- | --- |
| `CurrentAbilityDialog` → `MainWindow._current_ability_confirmations` | explicit user-confirmed current identity | existing public record remains unchanged |
| `MainWindow._capture_structured_ability_confirmation` | private owner/session binding at confirmation time | copied into structured requests only |
| `PokemonRepository.abilities_en` | possible species abilities | validation/reference only; never selection |
| observed `ability_activation_observed` event | observed event evidence | never becomes known current ability |

## Capture and validation

The private record carries the normalized canonical ability ID plus provenance:
`side`, `slot_index`, `pokemon_id`, `session_id`, `source`, and `trust`.
`normalize_structured_ability_confirmations` accepts only
`user_confirmed_current_ability` / `user_confirmed_current` entries whose active
side, slot, Pokemon, and session all match the request. It rejects `unknown`,
invalid IDs, missing provenance, stale records, and switched owners. It does not
pick a first or hidden ability from species metadata.

## Snapshot and Q12 boundary

The record is added only to the structured copied input as
`ability_context.current_abilities`; the frozen `TurnSnapshot` then feeds the
type/stat bridge's detached `known_ability` block. The Q12 adapter still supplies
no ability modifier. Ability identity, activation evidence, and damage modifiers
remain separate contracts. Legacy battle input, prompt, public confirmation
payload, and provider comparison schema are unchanged. Provider/network calls: 0.

Future modifier support needs a trusted identity, a modifier allowlist, timing
and phase semantics, attacker/defender scope, and dedicated regression fixtures.
