# v0.40 Opponent Sample Candidate Validation

Status: validation record only  
Date: 2026-05-28

## 1. Validation Scope

This document records the validation-first review of the T2-1 `v0.40.0-final` 19-sample candidate package.

No merge was performed.

No project files were changed during validation:

- `data/static/pokemon_stat_samples.json` was not modified.
- Repository schema was not changed.
- Tests were not changed.
- UI was not changed.
- Damage and Speed integration were not changed.

The candidate was treated as input data to validate, not as a trusted final fixture.

## 2. Existing Fixture Structure

Current fixture:

```text
data/static/pokemon_stat_samples.json
samples: {
  species_id: [
    sample,
    ...
  ]
}
```

Structure:

- species-keyed dictionary
- sample entries use `species_id`
- SP distribution currently lives under `assumptions.sp_distribution`
- current fixture contains 3 samples:
  - `charizard_special_attacker_01`
  - `corviknight_bulky_01`
  - `garchomp_fast_physical_01`

Candidate structure:

- top-level `existing_samples`
- top-level `new_samples_v40`
- sample entries use `species`
- SP distribution is top-level `sp_distribution`
- candidate expects additional fields such as:
  - `korean_name`
  - `ability_korean`
  - `archetype_id`
  - `stats_truth_source`
  - `possible_items`
  - `calculation_usage`
  - `existing_pre_v40`

Conclusion:

- The candidate is compatible only through a schema-extension/migration step.
- It should not be copied directly into the existing fixture.

## 3. Candidate Summary

Candidate package metadata:

- total candidate samples: 19
- existing sample block: 3
- new sample block: 16
- expected policy:
  - `source_type: manual_estimate`
  - `confidence: estimated`
  - `status: sample_assumed`
  - `is_user_confirmed: false`
  - `prior_probability: null`
  - `coverage_probability: null`
  - `calculation_usage: context_only`

Sample id validation:

- no direct conflict with existing fixture sample ids
- existing fixture sample ids use `_01` suffixes
- candidate existing block uses different sample ids

Species key validation:

- candidate uses `rotom_wash`
- repository normalization converts `rotom_wash` to `rotom-wash`
- repo cache contains `data/cache/pokemon/rotom-wash.json`
- raw `rotom_wash` should not be merged without normalization policy

## 4. Stats Validation

Repo stat calculator:

- available: yes
- helper: `advisor.damage.stats.final_stats`
- ruleset: `champions`
- level: 50
- IV assumption: 31 all, matching candidate `iv_assumption: "31_all"`

Result:

- matched samples: 0
- mismatched samples: 13
- unverified samples: 6

Mismatched samples:

- `garchomp_scarf_revenge_killer`
- `charizard_special_attacker`
- `corviknight_defensive_pivot`
- `garchomp_sd_sweeper_v40`
- `tyranitar_dd_setup_v40`
- `tyranitar_specs_trickroom_v40`
- `archaludon_stamina_wall_v40`
- `archaludon_offensive_v40`
- `dragonite_dd_multiscale_v40`
- `dragonite_choice_band_v40`
- `rotom_wash_defensive_v40`
- `rotom_wash_specs_v40`
- `kingambit_sd_supremeoverlord_v40`

Unverified samples:

- `gholdengo_specs_v40`
- `gholdengo_nasty_plot_v40`
- `amoonguss_redirect_v40`
- `amoonguss_spd_v40`
- `metagross_offensive_v40`
- `metagross_bulky_ap_v40`

Reason for unverified status:

- required repo cache/base stats files were not available for those species in the current local data.

Conclusion:

- Candidate stats must not be merged as-is.
- The repo calculator found no exact matches among checked samples.
- Samples without base stats cannot be validated yet.

## 5. Korean / Ability Validation

Confirmed from repo data/cache or mapping:

- `tyranitar` ability `모래날림`
- `archaludon` ability `지구력`
- `rotom-wash` ability `부유`

Suspicious:

- `garchomp` ability_korean `사기`
  - Rough Skin is represented in repo/data mapping as `까칠한피부`.
- `kingambit` korean_name `키랑이`
  - no repo-backed confirmation was found during validation.

Unresolved:

- `amoonguss`
- `gholdengo`
- `metagross`
- `amoonguss` ability_korean `포자`

Reason:

- repo cache/base species files were not available for these species in the current local data, so T3 did not have enough local evidence to confirm or fix them.

Conclusion:

- Korean names and ability fields require T1/T2 review before fixture merge.
- T3 should not silently rewrite these values.

## 6. Item Legality Validation

Validation source:

- `core.champions_item_repository.ChampionsItemRepository`

Legal items:

- `black-glasses`
- `choice-scarf`
- `leftovers`
- `lum-berry`
- `mental-herb`
- `metal-coat`
- `occa-berry`
- `sitrus-berry`

Illegal / not normal Champions legal in current fixture:

- `choice-specs`
- `choice-band`
- `life-orb`

Unknown in current Champions legal item repository:

- `heavy-duty-boots`
- `loaded-dice`
- `weakness-policy`
- `assault-vest`
- `throat-spray`
- `power-herb`
- `covert-cloak`
- `air-balloon`
- `black-sludge`
- `rocky-helmet`

Banned pseudo item check:

- no banned pseudo-item was found
- no `metagrossite-banned` was present
- no item id containing `banned` was present

Conclusion:

- Candidate `possible_items` must not be merged as-is.
- T3 should not automatically delete or rewrite unknown/illegal items.
- T1/T2 should decide whether to:
  - remove non-legal items
  - keep them only in `risk_notes`
  - add explicit review status
  - expand legal item fixtures separately

## 7. Merge Decision

Merge allowed: no

Reasons:

- stats mismatch on 13 samples
- stats unverified on 6 samples
- illegal/unknown `possible_items` entries are present
- `rotom_wash` conflicts with repo normalization expectation `rotom-wash`
- Korean/ability fields have suspicious or unresolved entries
- candidate structure requires schema migration rather than direct merge

Commit created during validation: no

Fixture modified during validation: no

## 8. Recommended Next Candidates

Recommended next work:

- `v0.41 Repo-Native Minimal Sample Pack Design`
- `v0.41 Legal Item Filter for Possible Sample Items`
- `v0.41 Stat Calculator Based Sample Generation Plan`

T3 recommendation:

- Do not retry the 19-sample merge until stats are generated from repo-native base stats and `final_stats`.
- Normalize species keys before constructing sample ids.
- Restrict `possible_items` to Champions legal items or explicitly move non-legal items into notes.
- Resolve Korean/ability fields using repo-backed sources before fixture updates.
