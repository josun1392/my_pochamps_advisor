# v12.73 Known Ability Source Boundary and Contract Foundation

## Inventory

Existing ability-related surfaces have distinct meanings:

- `data/cache/pokemon/*.json`, `core.cache_manager`, and
  `core.pokemon_repository.PokemonView.abilities_en` provide species/cache
  ability lists. They are possible species metadata, including hidden ability
  metadata where present, and are not current ability facts.
- UI-selected Pokemon identity can reach those repository/cache views, but the
  current UI has no direct current-ability confirmation control or session
  state. No `battle_input` current-ability key is produced.
- `data/static/ability_categories.json` categorizes mechanics. It is not a
  source of an active Pokemon's current ability.
- Damage/parity/multi-hit code can accept ability fields for scoped calculations
  such as Skill Link. Those calculations do not establish that an ability is
  currently known, activated, or resolved, and this task does not alter them.
- Current advisor payload/prompt paths contain ability limitation wording only;
  they have no current-ability payload context, prompt guard, or structured
  acknowledgement line.
- Move metadata can list moves such as Skill Swap or Gastro Acid. Move
  availability is not evidence that a replacement or suppression happened.
- Battle log, parser, imported replay, explicit event confirmation, and a Turn
  Engine remain future observed-source candidates only.

## Meaning boundary

The foundation distinguishes:

- `unknown_ability`
- `possible_species_ability`
- `known_current_ability`
- `observed_ability_event`
- `suppressed_or_replaced_ability_state`
- `resolved_ability_effect`
- `post_turn_ability_state`

Only a user-confirmed current identity is accepted now. Species possibilities
are not current facts. A known Intimidate does not prove switch-in activation
or an Attack drop; Levitate does not resolve a Ground interaction; Unaware does
not resolve a calculation; and Protosynthesis or Quark Drive does not establish
activation, boosted stat, multiplier, or final order. Neutralizing Gas, Gastro
Acid, Skill Swap, Trace, Mummy, and Lingering Aroma are future
suppression/replacement/event contracts, not current-identity fields.

## Normalization contract

`normalize_user_confirmed_current_ability(...)` is a pure validation seam. It
accepts only:

```python
{
    "side": "self" | "opponent",
    "ability": "<ability id>",
    "status": "user_confirmed",
    "source": "user_confirmed_current_ability",
}
```

It adds `confidence="known"` to the normalized result. The helper uses the
safe format policy rather than a cache lookup: lowercase kebab-case IDs are
accepted after case, whitespace, and underscore normalization. This permits
`"Quark Drive" -> "quark-drive"` without using a possible species list as a
source of truth. Empty values, `none`, multi-ability delimiter forms, and
malformed IDs are rejected. `unknown` is accepted as an explicit statement
that the specific current ability is unavailable.

Future source names, species/meta/common-set sources, candidate ability lists,
wrong status, and every activation/suppression/replacement/resolved/post-turn,
exact damage/stat/HP, immunity/prevention, RNG, and order field are rejected.
Forbidden-field detection is recursive.

## Non-integration boundary

This task adds no ability UI, session state, `battle_input` mapping, advisor
payload context, prompt wording, or structured acknowledgement entry. Existing
item event, current condition, field, limited-context, damage, KO, Q12/raw
roll, provider, CLI schema, and acknowledgement behavior remain unchanged.

## Verification

- new known-ability source contract: 50 passed
- advisor battle-state context: 40 passed
- status-condition source contract: 39 passed
- advisor payload contract: 500 passed
- item-event payload mapping: 27 passed
- trusted acknowledgement: 13 passed
- trusted acknowledgement matrix: 21 passed

## Status

**COMPLETE**

No provider/network call, credential check, raw response/token-log reading,
automatic ability detection, parser/replay/Turn Engine implementation, or
ability payload/prompt/UI integration occurred.
