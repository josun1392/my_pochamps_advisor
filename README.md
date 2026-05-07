# Pokemon Copilot

PySide6 desktop skeleton for a Pokemon battle copilot.

## Pokemon Champions Roster

The project includes a static Pokemon Champions roster at `data/static/champions_roster.json`.

- Format: `champions`
- Roster version: `Regular Roster M-A`
- Valid until: `2026-06-16`
- Primary data source: Bulbapedia
- Cross-check source: Serebii
- Official reference: Pokemon Champions official site

The roster is species-centered: regional and battle forms live under each species in `forms[]`, while Mega Evolutions live under `mega_evolutions[]`. Cosmetic forms that do not have distinct PokeAPI `/pokemon/{form}` endpoints are retained with `pokeapi_supported: false`.

Run verification:

```powershell
uv run python scripts/verify_champions_roster.py
uv run pytest tests/test_champions_roster.py -v
```

Run tests:

```powershell
uv run pytest
uv run pytest -m slow
```

## Data Prefetch

Pokemon Champions battle data is cached under `data/cache/pokemon/` for offline damage calculation.

Run the full prefetch:

```powershell
uv run python scripts/prefetch_champions_data.py
```

Refresh selected entities:

```powershell
uv run python scripts/prefetch_champions_data.py --only charizard charizard-mega-y
```

Force a full refresh:

```powershell
uv run python scripts/prefetch_champions_data.py --force
```

Verify the cache:

```powershell
uv run python scripts/verify_champions_cache.py
```

## Parity Bridge

The Python damage engine is validated against `@smogon/calc` through a Node.js subprocess bridge.

Install the Node dependency once:

```powershell
cd tools/smogon_bridge
npm install
cd ../..
```

Verify the bridge:

```powershell
uv run python scripts/verify_parity_bridge.py
```

Run the bridge tests:

```powershell
uv run pytest tests/test_parity_bridge.py -v
```

## Damage Engine

The pure Python damage engine lives under `advisor/damage/` and is checked against
`@smogon/calc` parity cases.

Run core and field verification:

```powershell
uv run python scripts/verify_damage_engine.py
uv run python scripts/verify_field_engine.py
```

Verify item modifiers:

```powershell
uv run python scripts/build_items_catalog.py
uv run python scripts/verify_item_engine.py
uv run pytest tests/test_damage_parity_items.py -v
```

Verify weather/terrain ability modifiers:

```powershell
uv run python scripts/build_abilities_catalog.py
uv run python scripts/verify_ability_engine_weather.py
uv run pytest tests/test_damage_parity_abilities_weather.py -v
```
