# Spike v0.9.1 Design — Champions Move Legality Cache

## 1. Goal

v0.9.1 designs a Champions-specific move legality cache.

The immediate problem is that the current Pokemon cache uses the Pokemon Champions roster as the entity list, but fills move pools from PokeAPI Scarlet/Violet learnsets. That allows moves that should not be legal in Pokemon Champions, such as `tera-blast`, to appear in the UI.

This spike does not implement scraping, cache generation, or UI changes. It defines the target cache model and the integration plan for a later implementation.

v0.9.1 must:

- separate global Champions legal moves from per-Pokemon Champions move pools
- treat PokeAPI as move metadata fallback only
- record source, confidence, and fetched timestamp
- preserve existing Pokemon identity, type, stat, and ability cache behavior
- avoid changing `advisor/damage/` and `advisor/probability/`
- avoid automatic LLM calls or battle advisor behavior changes

## 2. Current State

Current data flow:

```text
data/static/champions_roster.json
  -> scripts/prefetch_champions_data.py
  -> data/cache/pokemon/{entity_id}.json
```

The target list is Champions-specific, but the move list is not.

`scripts/prefetch_champions_data.py` currently:

- reads `data/static/champions_roster.json`
- fetches each supported entity from PokeAPI `/pokemon/{slug}/`
- stores types, base stats, abilities, sprites, and movepool
- builds movepool from PokeAPI `version_group_details`
- filters to `GEN9_VERSION_GROUPS = {"scarlet-violet"}`

This means:

- `tera-blast` appears for many Pokemon because it is a Scarlet/Violet machine move
- some Pokemon have an empty movepool because their PokeAPI form endpoint does not expose the expected SV move data
- Mega forms often have empty or unreliable movepools
- the UI cannot distinguish "Champions legal move" from "PokeAPI Gen 9 learnset move"

## 3. Source Candidates

### Bulbapedia

Candidate use:

- global move availability
- roster-level cross-checking
- human-readable notes for unavailable or special moves

Known useful page:

- `https://bulbapedia.bulbagarden.net/wiki/List_of_moves_by_availability_in_Pok%C3%A9mon_Champions`

Strengths:

- broad move availability table
- useful for global legal/illegal filtering
- easy to inspect manually

Risks:

- table structure may change
- per-Pokemon move pools may not be complete from this source alone
- source is community-maintained, not official machine-readable data

### Serebii

Candidate use:

- global usable move list
- per-Pokemon Champions pages if available
- manual cross-check against Bulbapedia

Known useful page:

- `https://www.serebii.net/pokemonchampions/moves.shtml`

Strengths:

- often tracks game-specific move and roster pages quickly
- useful independent cross-check

Risks:

- HTML is not designed as a stable API
- move names may require normalization
- robots/rate-limit constraints must be respected before scraping

### MetaVGC

Candidate use:

- format-level counts and legal list sanity checks
- independent validation of legal Pokemon, items, and moves

Known useful page:

- `https://metavgc.com/guides/pokemon-champions-format-legal-pokemon-items-moves`

Strengths:

- good high-level legality summary
- useful expected counts for regression checks

Risks:

- may not provide per-Pokemon move pools
- article format may change
- should not be the sole source of truth

### RotomLabs

Candidate use:

- per-Pokemon Champions move pools
- move category grouping such as tutor moves
- backfilling Pokemon whose current local movepool is empty

Example useful page:

- `https://rotomlabs.net/dex/champions/froslass`

Strengths:

- Pokemon-specific Champions dex pages
- likely the best candidate for per-Pokemon move pool extraction

Risks:

- third-party data, not official API
- route and DOM shape may change
- coverage for all roster forms and Mega forms must be audited

### PokeAPI

Candidate use:

- move metadata fallback only
- move type
- move category
- power
- accuracy
- PP
- localized names where available

PokeAPI must not be used as the Champions move legality source.

Allowed PokeAPI fields:

- move metadata for a move already accepted by the Champions cache
- type/category/power/accuracy/PP needed by damage estimate
- fallback English identifiers and names

Disallowed PokeAPI use:

- treating Scarlet/Violet learnset as Champions legality
- automatically adding `machine`, `level_up`, `egg`, or `tutor` moves to Champions move pools
- using PokeAPI form movepools as Mega form legality

## 4. Design Principles

The cache should answer two different questions separately:

```text
1. Is this move legal in Pokemon Champions at all?
2. Can this specific Pokemon use this move in Pokemon Champions?
```

Those must not be collapsed into one PokeAPI-derived `movepool`.

The cache should be explicit about trust:

- source URL or source id
- fetched timestamp
- confidence level
- parse method
- manual override status

The UI should only offer moves that pass both checks:

```text
move_id in global_legal_moves
and
move_id in pokemon_move_pool[entity_id]
```

## 5. Proposed Cache Layout

Recommended new directory:

```text
data/cache/champions/
```

Recommended files:

```text
data/cache/champions/move_legalities.json
data/cache/champions/pokemon_move_pools/{entity_id}.json
data/cache/champions/_index.json
data/cache/champions/_meta.json
data/cache/champions/_failures.log
```

Keep the existing Pokemon cache:

```text
data/cache/pokemon/{entity_id}.json
```

The existing Pokemon cache should continue to own:

- Pokemon identity
- Korean display name
- types
- base stats
- abilities
- sprites
- roster availability

The new Champions move cache should own:

- global move legality
- per-Pokemon move availability
- legality source metadata
- confidence and warnings

## 6. Global Move Legality Schema

File:

```text
data/cache/champions/move_legalities.json
```

Example:

```json
{
  "schema_version": "champions-move-legality-v1",
  "format": "pokemon_champions",
  "ruleset": "regular_roster_m-a",
  "valid_until": "2026-06-16",
  "generated_at": "2026-05-19T00:00:00Z",
  "moves": {
    "shadow-ball": {
      "move_id": "shadow-ball",
      "is_legal": true,
      "availability": "legal",
      "sources": [
        {
          "source": "bulbapedia",
          "url": "https://bulbapedia.bulbagarden.net/wiki/List_of_moves_by_availability_in_Pok%C3%A9mon_Champions",
          "observed_value": "available",
          "fetched_at": "2026-05-19T00:00:00Z"
        },
        {
          "source": "serebii",
          "url": "https://www.serebii.net/pokemonchampions/moves.shtml",
          "observed_value": "listed",
          "fetched_at": "2026-05-19T00:00:00Z"
        }
      ],
      "confidence": "cross_checked",
      "notes": []
    },
    "tera-blast": {
      "move_id": "tera-blast",
      "is_legal": false,
      "availability": "not_usable",
      "sources": [
        {
          "source": "bulbapedia",
          "url": "https://bulbapedia.bulbagarden.net/wiki/List_of_moves_by_availability_in_Pok%C3%A9mon_Champions",
          "observed_value": "not_available",
          "fetched_at": "2026-05-19T00:00:00Z"
        }
      ],
      "confidence": "single_source",
      "notes": [
        "Do not expose in move search even if present in PokeAPI Scarlet/Violet learnsets."
      ]
    }
  }
}
```

Recommended `confidence` values:

- `official` when confirmed by official Pokemon Champions machine-readable or clearly published data
- `cross_checked` when two or more third-party sources agree
- `single_source` when only one source supports the entry
- `manual_override` when curated locally
- `unknown` when not confirmed

Recommended `availability` values:

- `legal`
- `not_usable`
- `unknown`
- `special_case`

## 7. Per-Pokemon Move Pool Schema

File:

```text
data/cache/champions/pokemon_move_pools/froslass.json
```

Example:

```json
{
  "schema_version": "champions-pokemon-move-pool-v1",
  "format": "pokemon_champions",
  "ruleset": "regular_roster_m-a",
  "entity_id": "froslass",
  "species": "froslass",
  "name": {
    "en": "froslass",
    "ko": "눈여아"
  },
  "moves": {
    "champions": [
      "aurora-veil",
      "blizzard",
      "destiny-bond",
      "shadow-ball",
      "triple-axel"
    ],
    "by_source_category": {
      "rotomlabs_tutor": [
        "aurora-veil",
        "blizzard",
        "shadow-ball"
      ],
      "serebii_listed": [],
      "manual_override": []
    }
  },
  "excluded_moves": {
    "tera-blast": {
      "reason": "global_not_legal_in_champions",
      "source": "global_move_legalities"
    }
  },
  "sources": [
    {
      "source": "rotomlabs",
      "url": "https://rotomlabs.net/dex/champions/froslass",
      "fetched_at": "2026-05-19T00:00:00Z",
      "parser": "rotomlabs_champions_dex_v1",
      "confidence": "single_source"
    }
  ],
  "confidence": "single_source",
  "warnings": [
    "Per-Pokemon Champions move pool is third-party sourced.",
    "PokeAPI learnset is not used for legality."
  ]
}
```

Recommended per-Pokemon fields:

- `entity_id`
- `species`
- `name`
- `moves.champions`
- `moves.by_source_category`
- `excluded_moves`
- `sources`
- `confidence`
- `warnings`

The `moves.champions` list should be the normalized, UI-ready move id list. It should already have global illegal moves removed.

## 8. Move Metadata Fallback Schema

Move metadata should remain separate from legality.

Existing `MoveRepository` may continue to read PokeAPI move cache, but only after the selected move id has already been accepted as Champions-legal.

Suggested metadata shape if a dedicated cache is added later:

```json
{
  "move_id": "shadow-ball",
  "name": {
    "en": "Shadow Ball",
    "ko": "섀도볼"
  },
  "type": "ghost",
  "category": "special",
  "power": 80,
  "accuracy": 100,
  "pp": 15,
  "metadata_source": "pokeapi",
  "metadata_fetched_at": "2026-05-19T00:00:00Z",
  "legality_source": "champions_move_cache"
}
```

Important rule:

```text
PokeAPI can describe a move, but it cannot make the move legal.
```

## 9. Integration Plan

Recommended new modules:

```text
core/champions_move_cache.py
core/champions_move_repository.py
```

Possible public API:

```python
class ChampionsMoveRepository:
    def get_global_legality(self, move_id: str) -> MoveLegality: ...
    def is_move_globally_legal(self, move_id: str) -> bool: ...
    def get_pokemon_move_ids(self, entity_id: str) -> list[str]: ...
    def get_pokemon_move_pool_status(self, entity_id: str) -> MovePoolStatus: ...
```

UI integration target:

```text
MainWindow._sync_move_search_candidates()
```

Current behavior:

```text
available_move_ids = set(view.moves_en)
```

Future behavior:

```text
available_move_ids = champions_move_repo.get_pokemon_move_ids(view.en)
```

Fallback behavior should be explicit:

- If Champions move pool is available, use only Champions move pool.
- If Champions move pool is missing, return an empty set plus a visible status/warning.
- Do not silently fall back to PokeAPI learnset for legality.

Recommended UI status messages:

- `Champions move pool not available for this Pokemon.`
- `Move hidden because it is not legal in Pokemon Champions.`

## 10. Generation Plan

Do not scrape as part of this spike.

Future generation should be split into small scripts:

```text
scripts/build_champions_global_move_legalities.py
scripts/build_champions_pokemon_move_pools.py
scripts/verify_champions_move_cache.py
```

Generation order:

1. Build global move legality table.
2. Build per-Pokemon move pools.
3. Normalize all move names to canonical move ids.
4. Remove globally illegal moves from per-Pokemon pools.
5. Attach PokeAPI metadata only for accepted move ids.
6. Emit source/confidence/fetched_at.
7. Verify expected counts and known sentinel cases.

Sentinel cases:

- `tera-blast` must be globally illegal or unavailable.
- `froslass` must not expose `tera-blast`.
- `vanilluxe` should have a non-empty Champions move pool if source coverage supports it.
- Mega forms should not remain empty merely because PokeAPI form learnsets are empty.

## 11. Verification Plan

Recommended tests:

- global legality schema validates
- per-Pokemon move pool schema validates
- `tera-blast` is not offered for `froslass`
- `tera-blast` is not offered for any Pokemon when global legality says not legal
- Pokemon with empty PokeAPI movepool can still receive Champions move pool
- missing Champions move pool does not fall back to PokeAPI legality
- PokeAPI metadata lookup works only after Champions legality allows the move
- `MoveSearchBox` receives Champions-filtered move ids

Recommended manual checks:

- Search Froslass moves and confirm `tera-blast` is absent.
- Search Vanilluxe moves and confirm the list is no longer empty if sourced.
- Search Charizard moves and confirm obvious legal Champions moves remain.
- Confirm damage estimate still works for a selected Champions-legal attacking move.

## 12. Error Handling

Global cache errors:

- missing `move_legalities.json`
- invalid schema
- source conflict
- move id normalization failure
- stale `valid_until`

Per-Pokemon cache errors:

- missing `{entity_id}.json`
- empty move pool
- all candidate moves filtered by global illegality
- source parser failure
- form id mismatch
- Mega form source missing

Recommended status model:

```json
{
  "status": "unavailable_missing_champions_move_pool",
  "entity_id": "vanilluxe",
  "reason": "No Champions-specific move pool cache exists for this Pokemon."
}
```

The UI should not silently replace this with PokeAPI learnset data.

## 13. Contract Impact

The Advisor Payload Contract should eventually distinguish:

- `moves.my_selected_move` from the user-confirmed move slot
- `move_legality.source`
- `move_legality.is_champions_legal`
- `move_legality.confidence`
- `move_metadata.source`

Recommended payload addition once implemented:

```json
{
  "move_legality": {
    "format": "pokemon_champions",
    "is_champions_legal": true,
    "source": "champions_move_cache",
    "confidence": "cross_checked"
  }
}
```

Allowed LLM claim:

- The selected move is available according to the local Champions move cache.

Disallowed LLM claim:

- The selected move is officially guaranteed unless the source confidence is `official`.

## 14. Out of Scope

v0.9.1 design excludes:

- scraping implementation
- cache generation implementation
- UI move search changes
- changing existing cache files
- advisor damage engine changes
- probability engine changes
- final stats or EV/IV/nature UI
- Turn Engine
- LLM prompt behavior changes
- automatic cache refresh
- committing generated logs or temporary files

## 15. Recommendation

Build v0.9.1 as a data-contract milestone before changing move search behavior.

Recommended next implementation order:

1. Add schema and verification tests for Champions move legality cache.
2. Add a small hand-authored fixture with sentinel entries such as `tera-blast`, `froslass`, and `vanilluxe`.
3. Wire `ChampionsMoveRepository` behind `MainWindow._sync_move_search_candidates()`.
4. Only then add scraping/build scripts.

This keeps the UI from continuing to expose invalid PokeAPI learnset moves while avoiding a large, fragile scraping change as the first step.
