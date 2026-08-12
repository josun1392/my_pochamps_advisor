# Switch Entry Hazards v2

Frozen candidate-local evaluation supports Stealth Rock and Spikes only. The
session-bound hazard authority is owned by the affected side and records Rock
as present/absent/unknown plus exact Spikes layers (0–3) or unknown. Unknown
hazard state remains incomplete; it is never treated as absent.

Stealth Rock uses only B's frozen current type and the repository's canonical
type-effectiveness mechanics. Spikes uses only B's identity-bound prospective
groundedness authority; the active Pokemon's groundedness is never borrowed.
Both hazards use deterministic maximum-HP fractions and are subtracted before
the existing direct incoming evaluator sees B's HP.

Exact Heavy-Duty Boots or Magic Guard proves zero supported Stealth Rock and
Spikes damage. An unknown item or ability otherwise leaves the result
incomplete. A deterministic entry KO, including without an opponent move
candidate, feeds the existing danger tier. Ordinary hazard chip has no reward
or new switch-native score. Removal and entry abilities other than the bounded
Intimidate contract below remain unsupported.

## Toxic Spikes and Sticky Web

The v2 hazard authority additionally records exact Toxic Spikes layers (0–2)
and Sticky Web present/absent/unknown. A legacy v1 handoff upgrades only the
already-represented Stealth Rock and Spikes facts; the new hazard facts remain
unknown rather than being assumed absent.

Toxic Spikes evaluates only B-owned prospective groundedness, frozen current
type, item, ability, persistent condition, and a B-bound entry-interaction
authority. Grounded Poison types absorb it; grounded Steel types and explicit
interaction blocks have no status effect. One layer applies poison and two
layers apply toxic only when every prerequisite is exact. Heavy-Duty Boots
prevents the supported effect; an unknown item, condition, type, ability, or
interaction remains incomplete.

Sticky Web likewise requires exact B-owned groundedness, item, ability,
entry-interaction authority, and prospective Speed stage. Its supported
application clamps the canonical Speed stage at -6. The frozen direct-incoming
adapter replaces active-A condition and Speed-stage records with B's post-entry
records, preventing identity leakage. No extra Speed model, chip reward,
safety reward, or ranking score is introduced; currently these non-damaging
effects do not add a danger tier by themselves.

## Intimidate on switch-in

After the supported hazard phase proves B survives, a B whose frozen ability is
exactly `intimidate` may affect the opposing active only through a separate,
frozen `switch-entry-intimidate-authority-v1` record. It binds B's exact
identity, the exact opposing active identity, the opposing active's canonical
pre-entry Attack stage, and an authoritative interaction outcome: `lowered`,
`blocked`, or `reversed`. The existing -6..+6 stage clamp produces the post-
entry Attack stage. Unknown ability, interaction, target identity, or stage is
explicitly incomplete; no species-default immunity or ability behavior is
inferred. A proven entry-hazard KO means Intimidate does not activate.

The direct incoming adapter installs that post-entry Attack stage only if the
frozen opponent move candidate names the same opposing identity. It creates no
switch permission, chip/safety reward, or switch-native score; only an already
supported deterministic incoming danger consequence can affect ranking.

## Download on switch-in

After hazards prove B survives, exact B-owned `download` ability authority may
raise one B-owned prospective offensive stage only with a frozen exact B-to-
opposing-active Download authority. That authority supplies ability
applicability and the opposing active's exact Defense and Special Defense.
Download raises Attack when Defense is lower; otherwise, including an exact
tie, it raises Special Attack. The canonical +6 clamp is used. Unknown
applicability, defensive value, identity, or selected B stage remains
incomplete. No base-stat/species fallback, boost reward, switch permission, or
switch-native score is introduced.

## Trace on switch-in

After hazards prove B survives, exact B-owned `trace` ability authority can
copy an opposing ability only through a frozen exact B-to-opposing-active Trace
authority. It includes the opposing active's exact current ability and an
explicit trusted `traceable`/`untraceable` mechanics result. A traceable
ability is copied into a detached B-owned post-entry ability authority; the
opponent's authority is never mutated or aliased. Unknown ability,
traceability, or identity remains incomplete. An untraceable result is a
deterministic no-copy outcome. Copied abilities receive downstream treatment
only where already-supported mechanics recognize them; this adds no ability
catalog, reward, permission, or switch-native score.

## Weather-setting abilities on switch-in

After hazards prove B survives, exact B-owned `drizzle`, `drought`,
`sand-stream`, and `snow-warning` use the existing frozen
`field_state_context.current_field.weather` authority. With an exact standard
current weather (`none`, rain, sun, sandstorm, or snow), they respectively set
rain, sun, sandstorm, or snow; an already matching weather is an explicit
no-op. Missing weather and special/unsupported weather remain incomplete. The
post-entry standard weather replaces the direct incoming snapshot's existing
field weather so existing weather-aware mechanics may consume it. No new
weather engine, weather damage catalog, permission, reward, or switch-native
score is created.

## Focus Sash on switch-in

The direct incoming adapter now recognizes an exact B-owned Focus Sash only
after supported entry hazards prove B remains at exact full HP. For a supported
single-hit incoming move with a proven guaranteed OHKO, it refines the existing
KO evidence to no one-hit KO, allowing the established danger-only reduction to
use that deterministic consequence. It does not change damage rolls or claim a
full switch outcome. Unknown item/HP, entry damage, multi-hit moves, indirect
damage, consumption, and later-turn survival remain outside this bounded slice.

## Sturdy on switch-in

The switch pipeline now evaluates exact B-owned `sturdy` after hazards. It
requires a detached, identity-bound B-to-current-opposing-active applicability
authority, exact post-entry full HP, and a supported single-hit incoming move
with a proven guaranteed OHKO. Only that combination refines the existing KO
evidence to no one-hit KO; it does not alter raw damage or add a survival
reward. Suppressed, unknown, stale, non-full-HP, multi-hit, indirect-damage,
and later-turn cases remain outside the deterministic subset.

## Full-HP defensive abilities

The existing trusted direct-damage path now recognizes exact defender-owned
`multiscale` and `shadow-shield`, reusing the canonical formula's full-HP
damage reduction. Their exact current HP and maximum HP are passed to that
formula, so the reduction is absent below full HP. Unknown ability or HP, and
attacker interaction/bypass mechanics not already supported by the direct
evaluator, remain incomplete rather than being assumed favorable.

## Assault Vest defense

The trusted direct-damage path now consumes an exact defender-owned
`assault-vest` through the existing canonical Special Defense item modifier.
It applies only to supported special damage. Unknown defender item authority
remains incomplete; species-, transform-, activation-, or consumption-dependent
defensive items (including Eviolite) remain unsupported in this bounded slice.

## Offensive type-effectiveness abilities

The direct incoming path now consumes exact attacker-owned `adaptability` and
`tinted-lens` through the canonical damage formula. Adaptability is applied
only for a same-type attack, while Tinted Lens is applied only for a
type-resisted, non-immune attack. Both require the existing trusted current
attacker ability and current attacker/defender type authority; unknown ability
or types remain incomplete. Other ability interactions, suppression, and
unsupported attacker abilities remain outside this bounded slice.

## Offensive static items

The same direct incoming path now consumes exact attacker-owned `wise-glasses`
for supported special attacks and `expert-belt` for supported super-effective
attacks. Both reuse the canonical item modifier phases and require the existing
trusted item authority; Expert Belt additionally relies on the same trusted
current defender type authority used for type effectiveness. Unknown items or
types remain incomplete. Activation-, consumption-, species-, or other
unsupported item interactions remain outside this bounded slice.

## Super-effective defensive abilities

The direct incoming path now consumes exact defender-owned `solid-rock` and
`prism-armor` alongside its existing Filter support, reusing the canonical
super-effective damage-reduction phase. They apply only where trusted current
typing proves the incoming attack is super-effective. Unknown ability or type
authority remains incomplete. Attacker interactions not already supported by
the direct evaluator, including ability-bypass authority, remain incomplete.

## Wonder Guard

The direct incoming path now consumes exact defender-owned `wonder-guard`
through the canonical immunity check. With trusted current typing, it reduces a
supported neutral or resisted incoming attack to zero damage; a
super-effective attack proceeds normally. Unknown ability/type authority and
attacker bypass or suppression interactions not already supported by the direct
evaluator remain incomplete rather than being treated as immunity.

## Grassy Glide action order

The narrow action-order evaluator now applies Grassy Glide's priority increase
only when trusted current terrain is `grassy` and the acting side's own current
groundedness is exact. It uses existing field and side-owned groundedness
authority; unknown terrain or groundedness remains incomplete. Ungrounded
Grassy Glide receives no priority increase. This changes only deterministic
action-order evidence and creates no switch permission or strategic score.
