# Initial public-conditioned reserve sampler v1

This opt-in **coordinator** tool constructs initial native states, not returns,
teacher labels, policy features, or a belief model. Nothing in training,
evaluation, `LearnedPolicy`, or the advisor imports or enables it automatically.
`sample_initial_reserves(..., enabled=False)` and the CLI without `--enable`
perform no file reads/writes, model construction, or native calls.

## Frozen support and admission

Only the pinned V8 **256-team TRAIN subset**, independent random ordered-three
selection, `turn == 1`, native `decisions == 0`, revision zero, a move request,
complete ordered six-member public preview, and an unambiguous native active
`slot-N` identity are supported. Illusion teams, transformed introductions,
multiple compatible TRAIN roster classes, and later-history roots fail closed.
The owner team, owner ordered-three, and original initial seed must reproduce
the hash-bound reference checkpoint through the existing generator and native
`reset`. Checkpoint fields are never edited.

The equivalence relation removes **only the fresh episode UUID**. Every other
delivered field, including revision, incremental events, full public history,
own request, visible health, structured state, choices, and legal mask, must
match. Foundation encoder arrays must also be byte-identical. This deliberately
strengthens the older action-signal comparator that ignores events/revision.
UUID equivalence does not assert that raw observation JSON objects are identical.

The unique opponent TRAIN team is found from the *entire public ordered
six-species preview*, not from its private request or the actual hidden brought
three. All subset species names must be canonical in the pinned native Dex, so
the prefilter cannot silently discard alias matches. Given the visible lead,
the other five slots yield twenty ordered reserve pairs. The other 100 of the
120 ordered triples are excluded by that visible lead **inside this restricted,
non-Illusion support**, not counted as globally impossible hidden states.

A local, separately recorded proposal RNG selects 1–20 candidates uniformly
without replacement. It never advances global Python/Torch RNG or the native
initial seed. Selection is frozen before native admission; no outcomes exist.
Every selected candidate must pass. Public disagreement, invalid native state,
duplicate candidate/snapshot, source conflict, STOP, or bounds failure aborts
the entire batch. Partial files/receipts remain ineligible; no replacement,
automatic retry, or successful-results-only reweighting is implemented.

## Probability interpretation

Each record separates:

- draw-conditional proposal probability `1 / (20 - draw_index)`;
- proposal inclusion probability `sample_size / 20`;
- normalized selected-proposal weight `1 / sample_size`;
- untested pre-admission proposal support mass `(20 - sample_size) / 20`;
- idealized generator team/ordered-three structural mass `1 / (256 * 120)`,
  explicitly an assumption following `choice`/`sample`, **not an audited actual
  TRAIN prior**;
- actual TRAIN prior mass, public-conditioned prior, and missing TRAIN mass:
  **unknown/null**, with reasons.

Testing all twenty only exhausts this declared initial-seed/owner-setup/unique
roster/lead proposal. It never establishes completeness of all hidden native
states. Testing fewer never proves the untested candidates compatible with `h`.
The original case-index generator is deterministic and no empirical index
distribution or initial-seed marginalization is inferred here. Post-reset PRNG
may differ between candidates despite the same input seed; keep the native
states as generated. No calibrated moves/items/abilities posterior is supplied.

## Provenance, storage, and execution

`source_identity()` binds the sampler, generator, encoder dependency owners,
bridge, pinned team-bank/catalog files, and runtime identities. Plans additionally
bind subset, catalog, runtime-manifest, reference public JSON, and original
checkpoint gzip by SHA. Python/installed learning-library/Node versions are
recorded and verified. Snapshot source, case/side, seed stratum, roster hashes,
draw order, exclusion reasons, duplicate keys, and per-start receipts are durable.

All outputs must be outside every Git worktree. Native states and coordinator
manifests stay under `private/`; `public/` contains the unchanged owner view only.
The small returned handle is coordinator-only and never goes in Gym `info` or
actor/critic input. This is a data-flow boundary, not encryption or an OS sandbox.
Model loading, Adam updates, native `step`, terminal continuations, and teacher
integration are absent. A source-binding reset may be reused when that exact
selection is sampled; it is not a duplicated candidate/start.

The bounded CLI requires explicit `--enable`, an external frozen plan, and a new
external output directory. It uses maintained WindowsJob/RuntimeLimit and local
network protections: CPU 25%, RAM 4GiB, one native worker, no GPU, 600 seconds
including watchdog grace, at most 21 native resets. A started output is never
overwritten or resumed automatically. Direct API callers must provide equivalent
isolated owner resource containment; the library does not modify its host's job.

```powershell
python scripts/sample_foundation_initial_reserves.py --enable --plan C:\external\plan.json --output C:\external\new-run
```

`make_plan` only hashes inputs and freezes dependencies; it does not validate a
native world. Enabled execution regenerates the source, checks the original
native checkpoint and full `h`, then samples candidates. A receipt with status
`complete` is required before any state is considered admitted. Neither a plan
nor a partial folder is an accepted sample set.

Focused tests cover both seats, strict equality/unknowns, seed separation,
proposal versus unknown prior mass, incomplete support, native-source binding,
duplicates, source drift, illegal states, STOP/storage/start caps, and default
off. Real fixture validation is separately budgeted outside Git. No model or
teacher is promoted by these checks.
