# Spike v0.9.2 Design - Serebii Champions Pokemon Move Pool Cache

## 1. Goal

v0.9.2 defines and validates a Pokemon Champions-specific per-Pokemon move pool cache using Serebii Champions Pokedex pages as the primary source.

This spike is not a full scraping implementation. It audits source viability, proposes a cache schema, and defines the next implementation path.

The immediate problem is that the app can still derive move candidates from non-Champions sources:

- `data/cache/pokeapi/pokemon/{id}.json` can contain historical PokeAPI move lists.
- Historical PokeAPI move lists can include moves such as `hidden-power`.
- `data/cache/pokemon/{entity_id}.json` is roster-scoped to Champions entities, but its `movepool` was generated from PokeAPI Scarlet/Violet learnset details.
- Scarlet/Violet learnset data is closer than historical PokeAPI data, but it is still not Pokemon Champions legality.
- v0.9.1 global overrides can deny known global problems such as `tera-blast`, but denylists are not a full per-Pokemon legality model.

The target direction is:

```text
Pokemon move candidates in the UI should come from Champions per-Pokemon move pools.
PokeAPI should describe move metadata only.
```

## 2. Repo State Before Work

Observed before this spike:

```text
branch: master
remote sync: master...my_pochamps/master
working tree: clean
recent commits:
- 58dd007 feat(ui): filter globally denied champions moves
- 1f8cbd1 fix(ui): improve roster search and move slot state
- 234c26d docs(spike): design v0.9.1 champions move cache
```

`docs/handoff_capsule_v1.1.md` and `logs/` exist locally but were not touched by this spike.

## 3. Source Hierarchy

### Primary: Serebii Champions Pokedex

Use Serebii Champions Pokedex pages as the primary source for per-Pokemon Champions move pools.

Examples:

- `https://www.serebii.net/pokedex-champions/charizard`
- `https://www.serebii.net/pokedex-champions/froslass`
- `https://www.serebii.net/pokedex-champions/vanilluxe`
- `https://www.serebii.net/pokedex-champions/starmie`

Audit result:

- The sample pages return HTTP 200.
- Each sample page contains a `Standard Moves` section.
- Each sample page contains an `Attack Name` table header.
- The table shape includes move name, type, category, attack/power, accuracy, PP, and effect.
- The four sample pages did not contain `Hidden Power`.
- The four sample pages did not contain `Tera Blast`.

Serebii is therefore suitable as the first source for `pokemon_id -> allowed move ids`.

### Cross-check: RotomLabs Champions Dex

Use RotomLabs as the second source for cross-checking.

Examples:

- `https://rotomlabs.net/dex/champions/charizard`
- `https://rotomlabs.net/dex/champions/froslass`
- `https://rotomlabs.net/dex/champions/vanilluxe`
- `https://rotomlabs.net/dex/champions/starmie`

Audit result:

- The sample pages expose `Tutor Moves` sections.
- RotomLabs states that its Champions data comes from a datamine.
- The pages are useful for comparing Serebii move lists and for diagnosing missing or suspicious entries.

Do not make RotomLabs the only source unless Serebii is missing or ambiguous for a given Pokemon.

### Global References: Bulbapedia, MetaVGC, Existing Override

Use these sources for global sanity checks, not as the first per-Pokemon source:

- Bulbapedia Champions move availability
- MetaVGC Regulation M-A legal move list and counts
- `data/static/champions_move_overrides.json`

Their roles:

- confirm globally denied moves such as `tera-blast`
- check expected allowed move count trends
- flag source conflicts

### Metadata Fallback: PokeAPI Move Cache

PokeAPI remains useful for move metadata:

- type
- category
- power
- accuracy
- PP
- localized names when present

PokeAPI must not provide Champions legality.

Allowed:

```text
Serebii says Charizard can use Flamethrower.
PokeAPI provides Flamethrower's type, category, power, accuracy, and PP.
```

Disallowed:

```text
PokeAPI Pokemon learnset says Charizard has Hidden Power.
Therefore Charizard can use Hidden Power in Champions.
```

## 4. Sample Pokemon Audit

### charizard

Serebii page:

```text
https://www.serebii.net/pokedex-champions/charizard
status: HTTP 200
```

Move pool extraction viability:

- `Standard Moves` present.
- `Attack Name` table header present.
- HTML can be fetched without JavaScript.
- Move rows are visible in page text.

Sentinel checks:

- `hidden-power`: not present in Serebii sample page.
- `tera-blast`: not present in Serebii sample page.

RotomLabs cross-check:

- page exists
- `Tutor Moves` section present
- includes Charizard Champions move entries such as Acrobatics, Aerial Ace, Air Slash, Flamethrower, Earthquake, Protect, etc.

Current app difference:

- The older PokeAPI Pokemon cache can expose `hidden-power`.
- The Champions roster cache can expose `tera-blast`.
- A Serebii-derived cache would remove both for Charizard.

Notes:

- Charizard has Mega X and Mega Y forms. Form-specific treatment must be explicit in later implementation.

### froslass

Serebii page:

```text
https://www.serebii.net/pokedex-champions/froslass
status: HTTP 200
```

Move pool extraction viability:

- `Standard Moves` present.
- `Attack Name` table header present.
- HTML can be fetched without JavaScript.

Sentinel checks:

- `hidden-power`: not present in Serebii sample page.
- `tera-blast`: not present in Serebii sample page.

RotomLabs cross-check:

- page exists
- `Tutor Moves` section present
- includes Froslass Champions move entries such as Aurora Veil, Avalanche, Blizzard, Destiny Bond, Ice Beam, Shadow Ball, Spikes, etc.

Current app difference:

- Current `data/cache/pokemon/froslass.json` includes `tera-blast` through PokeAPI Scarlet/Violet machine data.
- v0.9.1 global override already filters `tera-blast` at UI candidate time.
- Serebii-derived per-Pokemon cache would make the allowed list cleaner at the source.

Notes:

- Froslass has a Mega form in the local roster. Later implementation must decide whether `froslass-mega` uses its own Serebii/RotomLabs section or inherits the base move pool with explicit source notes.

### vanilluxe

Serebii page:

```text
https://www.serebii.net/pokedex-champions/vanilluxe
status: HTTP 200
```

Move pool extraction viability:

- `Standard Moves` present.
- `Attack Name` table header present.
- HTML can be fetched without JavaScript.

Sentinel checks:

- `hidden-power`: not present in Serebii sample page.
- `tera-blast`: not present in Serebii sample page.

RotomLabs cross-check:

- page exists
- `Tutor Moves` section present
- includes Vanilluxe Champions move entries such as Acid Armor, Aurora Veil, Blizzard, Freeze-Dry, Ice Beam, Ice Shard, Icy Wind, Protect, Snowscape, Weather Ball, etc.

Current app difference:

- Current local Champions roster cache has an empty Vanilluxe movepool.
- Serebii-derived cache would directly fix Vanilluxe having no selectable moves.

Notes:

- Vanilluxe is an important sentinel for "empty local movepool but source page exists."

### starmie

Serebii page:

```text
https://www.serebii.net/pokedex-champions/starmie
status: HTTP 200
```

Move pool extraction viability:

- `Standard Moves` present.
- `Attack Name` table header present.
- HTML can be fetched without JavaScript.

Sentinel checks:

- `hidden-power`: not present in Serebii sample page.
- `tera-blast`: not present in Serebii sample page.

RotomLabs cross-check:

- page exists
- `Tutor Moves` section present
- includes Starmie Champions move entries such as Agility, Ancient Power, Blizzard, Hydro Pump, Ice Beam, Psychic, Recover, Scald, Surf, Thunderbolt, Trick Room, Waterfall, etc.

Current app difference:

- Current local Champions roster cache has an empty Starmie movepool.
- Serebii-derived cache would directly fix Starmie having no selectable moves.

Notes:

- Starmie has a Mega form. Later implementation must explicitly model form behavior.

## 5. Proposed Cache Location

Recommended location:

```text
data/cache/champions/regulation_m_a/pokemon_movepools/
```

Sample files:

```text
data/cache/champions/regulation_m_a/pokemon_movepools/charizard.json
data/cache/champions/regulation_m_a/pokemon_movepools/froslass.json
data/cache/champions/regulation_m_a/pokemon_movepools/vanilluxe.json
data/cache/champions/regulation_m_a/pokemon_movepools/starmie.json
```

Recommended support files:

```text
data/cache/champions/regulation_m_a/_index.json
data/cache/champions/regulation_m_a/_meta.json
data/cache/champions/regulation_m_a/_failures.log
```

Do not replace `data/cache/pokemon/{entity_id}.json`. That cache can continue to provide identity, stats, types, abilities, and sprites.

## 6. Proposed Schema

Example:

```json
{
  "pokemon_id": "charizard",
  "format": "pokemon_champions",
  "regulation": "M-A",
  "source_kind": "pokemon_movepool",
  "moves": [
    {
      "move_id": "flamethrower",
      "name_en": "Flamethrower",
      "source_refs": ["serebii"],
      "confidence": "third_party_primary",
      "metadata_source": "pokeapi"
    }
  ],
  "excluded_moves": [
    {
      "move_id": "hidden-power",
      "reason": "not_listed_in_champions_pokedex_movepool",
      "source_refs": ["serebii"]
    },
    {
      "move_id": "tera-blast",
      "reason": "globally_denied_in_champions_override",
      "source_refs": ["champions_move_overrides"]
    }
  ],
  "fetched_at": "2026-05-19",
  "source_refs": {
    "primary": [
      {
        "source": "serebii",
        "url": "https://www.serebii.net/pokedex-champions/charizard"
      }
    ],
    "cross_check": [
      {
        "source": "rotomlabs",
        "url": "https://rotomlabs.net/dex/champions/charizard"
      }
    ],
    "metadata": ["pokeapi"]
  },
  "notes": [
    "PokeAPI pokemon learnset is not used as a Champions legality source.",
    "PokeAPI move cache is used only for move metadata."
  ]
}
```

Recommended required fields:

- `pokemon_id`
- `format`
- `regulation`
- `source_kind`
- `moves`
- `excluded_moves`
- `fetched_at`
- `source_refs`
- `notes`

Recommended move fields:

- `move_id`
- `name_en`
- `source_refs`
- `confidence`
- `metadata_source`

Optional move fields if extracted from Serebii:

- `type`
- `category`
- `power`
- `accuracy`
- `pp`
- `effect_chance`

Even if those fields are extracted, PokeAPI should remain the normal metadata join source until the move metadata path is audited.

## 7. Normalization Policy

Serebii move names should be converted to canonical move ids:

```text
Flamethrower -> flamethrower
Will-O-Wisp -> will-o-wisp
Double-Edge -> double-edge
Freeze-Dry -> freeze-dry
Self-Destruct -> self-destruct
```

Recommended implementation:

1. Normalize Serebii display names with casefolding and punctuation handling.
2. Match against existing `data/ko_mapping.json` move keys and PokeAPI move cache names.
3. If no canonical id is found, emit a parse warning and exclude the move until manually mapped.
4. Never invent a move id silently.

## 8. Confidence Policy

Recommended values:

- `official`: official Pokemon Champions source confirms the exact move pool
- `third_party_primary`: Serebii Champions Pokedex lists the move
- `cross_checked`: Serebii and RotomLabs agree
- `third_party_single_source`: only one third-party source lists the move
- `manual_override`: local curated correction
- `unknown`: source is missing or ambiguous

Initial v0.9.2 sample fixtures should use:

```text
third_party_primary
```

If RotomLabs confirms the same move, later generation can upgrade to:

```text
cross_checked
```

## 9. Fallback Policy

Fallback must be conservative.

When a Champions per-Pokemon move pool exists:

```text
Use it.
Apply global denied move overrides.
Use PokeAPI only for move metadata.
```

When a Champions per-Pokemon move pool does not exist:

```text
Return unavailable/empty with a clear status.
Do not silently fall back to PokeAPI Pokemon learnset.
```

Recommended status:

```json
{
  "status": "unavailable_missing_champions_movepool",
  "pokemon_id": "vanilluxe",
  "reason": "No Serebii-derived Champions move pool fixture/cache exists for this Pokemon."
}
```

This is deliberately stricter than the current UI behavior. It prevents hidden historical moves from re-entering the advisor.

## 10. Repository / Helper Plan

Recommended module:

```text
core/champions_move_pool.py
```

Recommended public functions/classes:

```python
class ChampionsMovePoolRepository:
    def load_champions_movepool(self, pokemon_id: str) -> ChampionsMovePool | None: ...
    def get_allowed_move_ids_for_pokemon(self, pokemon_id: str) -> set[str]: ...
    def filter_champions_moves_for_pokemon(
        self,
        pokemon_id: str,
        candidate_move_ids: set[str],
    ) -> set[str]: ...
```

Important behavior:

- Read only from `data/cache/champions/regulation_m_a/pokemon_movepools/`.
- Apply `ChampionsMoveOverrides` after loading per-Pokemon moves.
- Return a clear unavailable status if the per-Pokemon cache is missing.
- Do not read `PokemonView.moves_en` as legality unless explicitly running a temporary compatibility mode.

## 11. UI Integration Plan

Current v0.9.1 behavior:

```text
view.moves_en
  -> global denied move filter
  -> MoveSearchBox.available_move_ids
```

Target behavior:

```text
ChampionsMovePoolRepository.get_allowed_move_ids_for_pokemon(view.en)
  -> MoveSearchBox.available_move_ids
```

Do not implement this UI change in the design spike without T1/T2 approval.

When implemented, the UI should show a status if the per-Pokemon Champions move pool is missing instead of silently using PokeAPI.

## 12. Implementation Plan

Recommended next steps:

1. Add a tiny sample cache for the four audited Pokemon.
2. Add `core/champions_move_pool.py`.
3. Add tests for loading sample fixtures:
   - Charizard does not allow `hidden-power`.
   - Charizard does not allow `tera-blast`.
   - Vanilluxe fixture is non-empty.
   - Starmie fixture is non-empty.
   - Unknown Pokemon returns unavailable/empty.
4. Add metadata join tests through `MoveRepository` for one legal move.
5. Only after sample fixtures pass, add a separate parser/build script.
6. Only after parser/build script is reviewed, wire MoveSearchBox to the Champions move pool repository.

## 13. Manual Verification Scenarios

After UI integration is approved:

- Charizard + move search `hidden` should not show Hidden Power.
- Charizard + move search `tera` should not show Tera Blast.
- Charizard + move search `flame` should show legal fire moves such as Flamethrower if present in the fixture.
- Vanilluxe should have non-empty move candidates.
- Starmie should have non-empty move candidates.
- Froslass should retain legitimate ice/ghost/status options and omit Tera Blast.
- Selecting a legal attacking move should still allow v0.9 damage estimate.

## 14. Rollback Plan

If the Serebii cache path causes issues:

1. Remove or disable `core/champions_move_pool.py`.
2. Remove sample files under `data/cache/champions/regulation_m_a/pokemon_movepools/`.
3. Revert UI integration if it has been added.
4. Keep `data/static/champions_move_overrides.json` active as the smaller v0.9.1 global safeguard unless that file is proven wrong.

Because this spike only writes documentation, rollback is simply deleting this document commit.

## 15. Out of Scope

This spike excludes:

- full scraping implementation
- automatic Serebii/RotomLabs bulk collection
- UI MoveSearchBox behavior changes
- damage engine changes
- `advisor/damage/` changes
- `advisor/probability/` changes
- four-move damage comparison
- opponent move integration
- EV/IV/nature/item/final stats UI
- Turn Engine
- API keys or secrets
- `docs/handoff_capsule_v1.1.md`
- `logs/`

## 16. Recommendation

Proceed with Serebii as the primary source.

The next implementation should be a small fixture/helper milestone, not a full scraper:

```text
v0.9.2a - Sample Serebii Champions movepool fixtures
```

Use the four sample Pokemon:

- `charizard`
- `froslass`
- `vanilluxe`
- `starmie`

This will let the project prove that:

- Serebii-derived move pools remove historical PokeAPI moves such as `hidden-power`
- Serebii-derived move pools remove globally denied moves such as `tera-blast`
- empty local movepool Pokemon can be repaired without using PokeAPI Pokemon learnsets
- PokeAPI can remain a safe metadata fallback

