# Pokémon Champions Roster Metadata

- Format: `champions`
- Roster version: `Regular Roster M-A`
- Valid until: `2026-06-16`
- Extracted at: `2026-04-27`

## Sources

- Primary roster data: https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_in_Pok%C3%A9mon_Champions
- Cross-check source: https://www.serebii.net/pokemonchampions/pokemon.shtml
- Official reference: https://champions.pokemon.com/en-us/

## Trust Notes

The official Pokémon Champions site confirms the game and high-level transfer/recruit flow, but does not expose a complete machine-readable roster list. The roster JSON therefore uses Bulbapedia as the primary structured source and Serebii as the manual cross-check source.

Bulbapedia reports `187` available species and `59` Mega Evolutions for `Regular Roster M-A`. Cosmetic variants such as Vivillon patterns, Furfrou trims, Florges colors, and Alcremie creams do not have distinct `/pokemon/{form}` endpoints in PokeAPI. These entries are preserved as forms with `pokeapi_supported: false` and reuse the base `form_id` for cache compatibility.

`Eternal Flower Floette` is represented as `floette-eternal` and marked `transfer_only` with a HOME transfer note.

## Generated Counts

- Species: `187`
- Form variants: `75`
- Mega Evolutions: `59`
- Total battle/display entities: `321`
