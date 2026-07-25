# v15.13 Trusted Level Provenance and Q12 Candidate Wiring

## Inventory and policy

| Source | Availability | Trust decision |
| --- | --- | --- |
| `ui.main_window._stat_profile_payload` | fixed `level: 50` default/profile display | not trusted; it is an assumption |
| final-stat confirmation dialog | exact six stats only | no level producer |
| `attacker_level_context` legacy fixed-damage input | caller-shaped legacy context | not promoted into structured Q12 input |
| repository species metadata | no battle level | not a source |
| `trusted_level_context.current_levels` | canonical fixture/import boundary | accepted only with active owner/session provenance |

No production UI level producer exists. v15.13 therefore does not create a
level input, infer level 50/100, or derive it from final stats. A canonical
entry has `value`, `side`, and provenance containing `slot_index`, `pokemon_id`,
`session_id`, `source`, and `trust`. Only
`user_confirmed_current_level`/`user_confirmed_current` and
`deterministic_rules_metadata`/`deterministic_rules_metadata` are accepted.

## Wiring

`MainWindow._start_structured_recommendation` now supplies its existing
`PokemonRepository` to the structured worker. The pure path is:

```
prepare_ui_recommendation_cycle
→ evaluate_move_candidate
→ build_snapshot_damage_input + build_snapshot_stat_provenance
→ build_snapshot_trusted_level_provenance
→ invoke_existing_q12_from_snapshot
```

The invocation runs at most once for each damaging candidate. Missing/stale or
wrong-owner level, unavailable final stats, status moves, and invalid snapshot
ownership retain the candidate and attach a sanitized internal `q12_damage`
unavailable result. `q12_damage` stays in prepared candidates but is stripped
from provider `candidate_comparisons`; no prompt schema or legacy payload is
changed.

## Scope and limitations

Physical and special candidates retain the v15.12 Attack/Defense and Special
Attack/Special Defense mapping. Status candidates make no Q12 call. Existing
formula exceptions remain sanitized. Stat stages, ability/item, weather,
terrain, field/side effects, and observed events remain unsupported modifiers.
The result and its detached snapshot inputs remain stable across source mutation
and session rollover. Provider/network calls: 0.
