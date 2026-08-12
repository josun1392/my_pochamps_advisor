# Observed hazard-state replacement

The bounded hazard-removal transition accepts a user-confirmed,
side-owned `switch_hazards_observed` record. It is a complete replacement of
the canonical affected-side hazard authority: Stealth Rock and Sticky Web must
be explicitly present or absent, while Spikes and Toxic Spikes must carry
their exact canonical layer counts. A fully absent observation therefore
proves hazard removal without inferring it from Rapid Spin, Defog, Mortal
Spin, or any other move.

Lifecycle confirmation, observation collection, and replay map the result to
the existing `set_switch_hazards` reducer effect. Later frozen switch requests
therefore use the new side/session-bound authority, and existing Stealth Rock,
Spikes, Toxic Spikes, and Sticky Web evaluators read the updated absence or
layers normally.

Partial, unknown, inferred, or move-only removal claims are rejected. This
transition does not model which move removed hazards, partial move success,
Defog's other effects, Court Change, or generic reward/ranking for removal.
