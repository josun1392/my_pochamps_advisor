# v15.70 status-move provider grounding smoke

## Fixture boundary

The approved pair uses one rankable direct-damage candidate in each fixture so
the existing minimal provider response remains valid. Status candidates are
present only as deterministic evidence: the first pair mixes recovery/setup
with damage; the second carries known, missing, and malformed canonical role
metadata.

## Authority and assertions

The provider still returns only a selected slot and bounded explanation code.
The smoke verifies canonical role status/tags and candidate-local comparison
facts before calling the provider, then verifies completed candidate evidence,
selected-result evidence, and presentation boundaries after it. It rejects
mixed status/damage evidence without treating a status move as zero damage.

## Safety

The smoke prints only its existing bounded result surface. It never writes raw
provider data, canonical metadata details, prompt data, or presentation text.
There is no status-effect simulation, utility score, or ranking-policy change.

## Offline validation

Fake-provider fixture, candidate/result/presentation regressions, the full
offline suite, and compilation pass before the separately approved actual
round. Retry, fallback, and repair remain zero.
