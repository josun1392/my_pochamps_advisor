# Practical-2.0 Deterministic Turn Engine Substrate Final

**Status:** `PRACTICAL_2_0_DETERMINISTIC_SUBSTRATE_FINAL`
**Release baseline:** `f6674272b06c220ac7e3be86a1a192f9e96375aa`
**Final offline validation:** 3703 passed, 2 deselected
**Execution boundary:** explicit caller-owned actions only; no provider, network,
desktop, or global automation is part of this milestone.

Practical-2.0 is the completed deterministic execution substrate for the
approved bounded action and switch-entry families. It is not strategic ranking,
opponent modelling, exhaustive Pokémon mechanics, or arbitrary multi-turn
search.

## Executed capability inventory

### Action transitions

- Exact direct-damage transitions, including exact nonterminal damage and
  guaranteed terminal KOs, use branch-bound hypothetical direct mechanics.
- Explicit self stage change, deterministic recovery, ordinary poison/Toxic,
  and ordinary Protect-style prevention compose only through their respective
  trusted contracts.
- Explicit two-turn execution accepts caller-supplied Turn 1 and Turn 2
  actions. It does not select actions, predict an opponent, branch, rank, or
  recurse to a third turn.

### Branch-state and lifecycle mutations

- Detached active HP, faint state, predictive conditions, stat stages, and
  Toxic lifecycle advance only from exact supported evidence.
- Ordinary poison and newly applied Toxic use the bounded EOT path. Toxic
  begins at stage 1, EOT consumes that stage, and a surviving lifecycle carries
  stage 2 through next-turn handoff.
- An immutable turn-root fingerprint remains overall-turn provenance. A
  predicted Toxic condition and lifecycle share their exact application-source
  branch fingerprint, which may legitimately be a later branch generation.

### Manual switch and entry effects

- An explicitly owned, legal self manual switch materializes only
  identity-bound incoming authority into a detached active branch.
- Detached side-owned hazard context carries Stealth Rock, Spikes, Sticky Web,
  and Toxic Spikes independently of the active Pokémon.
- Supported entry execution is materialization, side-hazard projection,
  Stealth Rock/Spikes HP mutation, terminal entry-KO check, Sticky Web Speed
  stage mutation, then Toxic Spikes condition or absorption/removal handling.
- One Toxic Spikes layer applies predicted ordinary poison; two layers apply
  predicted Toxic; exact Poison-type absorption removes only Toxic Spikes from
  the affected detached side context. SR, Spikes, Sticky Web, and opponent-side
  hazards remain isolated.
- A surviving incoming Pokémon receives fresh hypothetical direct evaluation
  against the final post-entry branch. An entry KO stops before later entry
  effects, opponent action, or replacement synthesis.

## Authority and provenance contract

| Domain | Canonical owned authority |
| --- | --- |
| Pokémon | HP/max HP, fainted state, condition, stages, item, ability, current type, Toxic lifecycle |
| Side | `branch_side_hazard_context` and supported entry-hazard values |
| Turn/branch | immutable turn root, detached generation fingerprints, predictive application-source provenance |
| Transient | current-turn Protect effect; it expires before `next_turn_start` |

Incoming active materialization never copies outgoing HP, condition, stage,
item, ability, type, Toxic lifecycle, predictive overlays, or direct evidence.
Side hazards remain side-owned across active replacement. Handoff preserves
persistent detached authority and excludes completed-turn action/evidence.

## Canonical bounded lifecycle

```text
authoritative source
  -> explicit owned actions
  -> exact established ordering
  -> supported detached transition and mutations
  -> terminal check
  -> pre_end_of_turn
  -> bounded EOT
  -> next_turn_start handoff
  -> newly fingerprint- and owner-bound Turn 2 actions
```

For the switch variant, the supported entry sequence above produces the final
branch before fresh opponent direct evidence is generated. Turn 2 must bind to
the handoff fingerprint and actual resulting active identity; stale or
outgoing-bound actions reject.

## Fail-closed boundary

Practical-2.0 does not infer missing material authority. Unknown HP, stage,
condition, item, ability, type, groundedness, hazard state/layer, action order,
or branch ownership remains incomplete or unsupported. Stale/foreign
fingerprints, malformed predictive overlays, and unsupported mechanics reject
or fail closed. Unknown is never converted to absent, neutral, zero, false, or
`none`.

## Deferred scope

The following are normal deferred work, not defects in this milestone:

- switch-in abilities and additional entry-effect families;
- additional action families and broader protection families;
- repeated-Protect probability and bypass/secondary-effect coverage;
- broader EOT scheduling and effect families;
- replacement policy, forced switching, and pivot moves;
- opponent-response branching, dynamic horizons, and search;
- strategic utility and ranking.

## Final evidence and next phase

Focused transition, switch-entry, hazard-context, Toxic lineage, EOT, handoff,
Protect, and two-turn contracts are green. The final offline suite is 3703
passed, 2 deselected.

The next phase must receive a separate T1 decision. The highest-value
deterministic direction is a narrowly specified switch-in ability or additional
entry/EOT family; strategic ranking and opponent-response branching remain
separate product-policy work.
