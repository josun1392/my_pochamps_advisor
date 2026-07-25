# v15.16 Trusted Used-Move and Exact HP-Transition Provenance

## Inventory and purpose

`MainWindow` selected move state and structured recommendation candidates mean intended/selected move only; deterministic selected-move estimates and Q12 are calculated evidence, not actual usage. No actual used-move dialog, history, or log producer exists. `CurrentHPDialog` accepts exact integer current/max HP, while panel `hp_percent` is percentage display state; neither records an HP before/after transition. The v15.15 Previous Damage dialog remains exact amount-only opponent-to-self confirmation.

| source | meaning/unit | production | structured status | gap |
|---|---|---|---|---|
| selected move / candidate / Q12 | selected or calculated | yes | not used-move evidence | must not promote |
| Current HP dialog | exact current/max snapshot | yes | current-state only | no before/after pair |
| panel HP percent | percent display | yes | no transition | never exact-converted |
| v15.15 Previous Damage | exact amount only | yes | observed damage | no move/transition |
| v15.16 private records | confirmed used move / exact transition | contract only | structured copied input | no UI producer yet |

## Contract

An explicitly confirmed used move has `observation_id`, `move_id`, `move_slot`, attacker side/slot/Pokémon/session provenance, `source=ui_used_move_confirmation`, and `trust=user_confirmed_observation`. It must be a current self active move slot with matching ID; selected/recommended moves, species movepool membership, stale/wrong owners, and provenance-free records are rejected.

An exact transition has the same explicit `observation_id`, defender provenance, integer non-negative `hp_before >= hp_after`, `hp_unit=exact`, `source=ui_exact_hp_transition_confirmation`, trust, and confirmation. Percent, partial, rising, negative, stale, or wrong-owner transitions are rejected and never converted to exact. Zero damage is allowed by the existing amount contract, but the current UI does not emit it.

Only a same-observation-ID record links to a v15.15 event. Used move and transition may enrich independently; a complete event requires both. If `damage_amount != hp_before - hp_after`, the amount remains unchanged, transition is not attached, and `enrichment_status=conflicting_damage_amount` is retained. Session equality, amount, or timestamps alone never link records.

## Boundaries

All records are detached private inputs to `capture_ui_current_state_provenance`, then frozen under `TurnSnapshot.current_state.observed_damage_context`. Amount-only v15.15 events remain valid. Q12 and observed evidence stay separate; no roll selection, stats, ability/item, level, critical, weather, terrain, or modifier inference occurs. Legacy input/prompt, public confirmation payload, provider schema/adapters, candidate ranking, and Q12 formula/API are unchanged. Provider budget: 0.

Future work needs actual used-move and transition UI/log producers, opponent move-slot ownership, turn/sequence provenance, multi-turn state, and only then comparison or modifier work. Turn Engine, battle-log automation, OCR, persistence, and reverse inference are non-goals.
