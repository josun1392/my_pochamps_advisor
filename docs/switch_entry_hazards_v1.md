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
or new switch-native score. Toxic Spikes, Sticky Web, removal, entry abilities,
and other entry effects remain unsupported.

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
