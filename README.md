# Pokemon Copilot

PySide6 desktop skeleton for a Pokemon battle copilot.

## Pokémon Champions Roster

The project includes a static Pokémon Champions roster at `data/static/champions_roster.json`.

- Format: `champions`
- Roster version: `Regular Roster M-A`
- Valid until: `2026-06-16`
- Primary data source: Bulbapedia
- Cross-check source: Serebii
- Official reference: Pokémon Champions official site

The roster is species-centered: regional and battle forms live under each species in `forms[]`, while Mega Evolutions live under `mega_evolutions[]`. Cosmetic forms that do not have distinct PokeAPI `/pokemon/{form}` endpoints are retained with `pokeapi_supported: false`.

Run verification:

```powershell
uv run python scripts/verify_champions_roster.py
uv run pytest tests/test_champions_roster.py -v
```
