# Showdown backend migration — 2026-10-11

Latest: [Continuation execution and validation](showdown_continuation_result_2026-10-11.md).

Continuation: [Versioned state compatibility](showdown_state_compatibility.md)
supersedes the decision-required status/counter discussion below. The approved
boundary now preserves old records and verifies native compatibility. The
original measurements and validation below describe the 9d5cbbd checkpoint.

Status: **PARTIAL / CONDITIONAL GO for opt-in shadow evidence**. The default
recommendation engine and its exact/guaranteed-first ranking authority remain
unchanged. No legacy mechanics have been retired.

## Executable integration

The external engine is pinned to Pokémon Showdown
`942cda71d14bf0618bd57991708a2e2734b6daba`. Native `gen9championsbssregmc`
validates six registered sets and three explicit picks, then owns every battle
action, damage roll, ability/item callback, residual and replacement request.
No battle server or provider is involved.

The Python path is captured runtime -> validated hypothetical root -> native
checkpoint forks -> structured per-scenario results -> optional existing
strategy explanation panel. Simulations do not write to runtime, reducer,
observation ledger, session or recommendation rank. Every candidate and result
retains its session, runtime fingerprint and decision identity.

Supported reconciliation includes roster slot identity across native reorder,
HP/max HP/faint history, known species including Mega identity, stats/stages,
types/ability/item/status, complete opponent moves and observed PP, move
usability, substitute HP, focus/crit volatiles, basic status/toxic counters,
screens/tailwind, switch permission, weather/terrain/rooms/gravity. Known facts
must agree with the explicit native model. Faint counters are established via
native history or explicit native faint initialization, never hand-written.

Unknown information remains unknown in the runtime. Complete sets, unobserved
history, initial effects/durations, unknown active HP and future opponent
choices are explicit scenario assumptions. Unknown active HP requires a value
per scenario. There is no implicit opponent prior or rollout policy.

`simulate_detached_showdown`, `resume_detached_showdown`,
`reconcile_detached_showdown` and `evaluate_detached_showdown` expose creation,
native restoration, conditioning on newer observations, and common-seed plan
evaluation. Reconciliation binds the same original teams, picks, assumptions
and session; changing a set requires a fresh root. Native move, forced
replacement and pivot boundaries retain the action queue. A plan entry is a
decision boundary, not necessarily a whole turn. Every restore deep-copies
`Battle.toJSON()` before `Battle.fromJSON()` because deserialization mutates
its input.

The persistent JSONL worker loads the engine once, serializes requests,
validates response IDs, discards timed-out workers and can restart. Pin and
tracked-source cleanliness are checked at worker startup; keep the external
built checkout immutable while a worker is running. Each request carries its
root; the worker retains no live session authority. The one-shot bridge remains
available for parity and simpler callers.

Samples are labeled conditional Monte Carlo estimates. Counts, mean remaining
team HP and individual seeded results are separate from exact probability
ledgers. Invalid plans are rejected as a whole rather than producing a biased
aggregate from only successful seeds.

## Opt-in and rollback

Install into a fresh external directory, using Python 3.11+ and Node >=22.18:

```powershell
uv run python scripts/setup_showdown.py --destination C:\temp\poke-showdown-mc
$env:POKEADVICE_SHOWDOWN_CHECKOUT = 'C:\temp\poke-showdown-mc'
uv run python scripts/verify_showdown_integration.py --showdown-checkout $env:POKEADVICE_SHOWDOWN_CHECKOUT
uv run python scripts/compare_showdown_legacy.py --checkout $env:POKEADVICE_SHOWDOWN_CHECKOUT
uv run python scripts/benchmark_showdown_backend.py --checkout $env:POKEADVICE_SHOWDOWN_CHECKOUT --iterations 20
uv run pytest tests/test_showdown_integration.py tests/test_showdown_reconciliation.py tests/test_showdown_mechanics.py tests/test_showdown_sampling.py tests/test_showdown_shadow_ui.py -q
uv run python main.py --showdown-shadow C:\temp\hypotheses.json --showdown-checkout $env:POKEADVICE_SHOWDOWN_CHECKOUT
```

The local JSON configuration has `schema_version: "showdown-shadow-config-v1"`,
`scenarios` in the detached simulation contract, and `seeds` (up to 64 distinct
four-uint16 arrays). Each scenario includes complete legal teams, preview,
explicit assumptions/history and `choices.opponent`. Existing selectable
human attacks/manual switches are mapped to native actions; the UI labels
these results as separate sampled evidence. Scenarios must match the actual
captured session state. Example teams and captures are executable fixtures in
`scripts/verify_showdown_integration.py`, not inferred observations.

Rollback: omit both CLI options, or call `configure_showdown_shadow()` on the
window to close the worker and disable the context. Missing/unsupported/stale
native evidence leaves the existing recommendation intact. Default startup
does not load Showdown.

## Evidence and remaining transition gates

Native tests cover full M-C battles/restoration, multiple item hypotheses,
seed reproducibility, multi-turn PP, forced replacements/pivots with queued
actions, hazards, Levitate immunity, Mega evolution, observed-state rebinding,
unknown-information isolation, worker lifecycle and the actual Qt explanation
panel. The offline comparison matches all 16 conditional damage rolls in 12
legal M-C cases (weather, burn, Technician, Life Orb/type items, screen/crit
bypass and Blaze). This is representative coverage, not exhaustive parity.

A material discrepancy is deliberately recorded: for Early Bird and native
sleep duration 3, Showdown cancels the first attack as asleep; the legacy exact
gate predicts immediate wake/execute. Legacy `valid_progression` also encodes
`duration // 2`, and mechanics-derived status events can be admitted to runtime
truth. Translating this into sampled evidence cannot replace that authority.
Adjusted legacy counter states fail closed until the units/lifecycle contract
is migrated and validated. No ranking or runtime formula was silently changed.
Previously admitted mechanics-derived progression and persisted replay state
must not be silently rewritten to fit native counter units. Choosing a
versioned compatibility/migration rule at this truth-authority boundary is the
architectural decision needed before replacing those consumers.

Known unsupported contexts (including pending partial-action execution,
Taunt/Encore/Disable lifecycle, action/history counters and some persistent
effects) return field paths. The current observation model does not provide a
complete authoritative native action queue/phase transcript. Guessing that
every capture is a new move boundary would be unsafe. Exact native restoration
is exact for a modeled state, not proof of the human battle's hidden state.

**Next milestone:** define a native decision-phase/status-counter authority
contract that keeps actual observed facts separate from modeled continuations;
reconcile Early Bird and migrate the existing derived-event admission seam
with semantic regression fixtures. Then expand the remaining known-context
adapters and exact evidence consumers before considering default activation.
The guaranteed-first ranking policy can remain intact; Monte Carlo evidence
must not substitute for exact authority.

The default transition gates remain open: full representative mechanics and
live-state/phase coverage, resolution of material discrepancies, exact
consumer replacement, broad offline regressions and production performance.
`advisor/damage/`, `advisor/probability/` and the existing Python lifecycle/
ranking consumers remain required. No full migration completion is claimed.

## Validation and measured performance

Final focused native plus session/strategy/UI/ranking regressions: **145 passed**,
including **67 Showdown tests**. The full offline suite collected during
development finished with 7,570 passed, 3 failed and 2 deselected in 26m36s.
One failure executed a previously collected reconciliation test while native
faint validation was being updated; the final test passed on fresh reruns.
The other two are unchanged small-desktop UI layout regressions, reproduced
against isolated baseline UI source from `2ab6ec3` in the same environment.
The broad suite was not rerun wholesale after the final changes; the changed
paths and nearest regressions were rerun. There is no claim of an all-green
full suite. The offline network guard recorded zero connection attempts.

Windows x64, standard Python 3.11.9, Node 22.20.0; 20 benchmark repetitions:

| Workload | Median | p95 | Maximum |
| --- | ---: | ---: | ---: |
| Four explicit scenarios, warm worker | 17.920 ms | 21.423 ms | 22.216 ms |
| Four scenarios x three candidates x 64 seeds (768 branches) | 456.112 ms | 567.881 ms | 580.389 ms |

Worker startup took 403.687 ms. Sample outputs reproduced exactly after
discarding transport timing, and the worker matched the one-shot bridge.
The separate native proof finished 29 turns/33 decisions with restoration at
every decision; 200 restore-and-choice forks had median 0.913 ms/p95 1.451 ms.
These fixture-specific measurements do not guarantee latency for every legal
team or longer rollout.

## Task-owned files and Git

Based on verified `2ab6ec39f42dd3ad0e7f66448e3f75161ac9a9c4` on
`codex/showdown-mc-integration-v1`, canonical remote
`https://github.com/josun1392/my_pochamps_advisor.git`. The original master
checkout, its divergent commit and all five pre-existing changes remain intact.

Changed 20 paths relative to that baseline:

- Transport/execution: `advisor/showdown_bridge.py`, `advisor/showdown_worker.py`,
  `tools/showdown_bridge/bridge.cjs`, `worker.cjs`, `damage-oracle.cjs`.
- Runtime/consumer seam: `llm/advisor_showdown_simulation.py`,
  `llm/advisor_showdown_shadow.py`, `llm/advisor_ui_detached_strategy_bridge.py`,
  `main.py`, `ui/main_window.py`, `ui/strategy_explanation_presentation.py`.
- Evidence: `scripts/benchmark_showdown_backend.py`,
  `scripts/compare_showdown_legacy.py`, five `tests/test_showdown_*.py` files.
- Contracts/report: this file and `docs/showdown_m_c_integration_v1.md`.

## Upstream reuse

Reused Showdown's native validator, battle engine, conditions, PRNG and
serialization. Inspected MIT Champions Lab at
`09d59984631dd2a45fb21700970c65ee24cf7d0f` for serialize/restore/fork usage;
its doubles format and different pin were not imported. Inspected ai-vgc at
`0bd586d4b2c2cbca9e06d52dada06c46649a32a5` for its local JSONL bridge;
no source was copied because licensing was not established. poke-env's
observation/server integration was reviewed; no server/bot dependency was added.

Primary sources: [Showdown pin](https://github.com/smogon/pokemon-showdown/tree/942cda71d14bf0618bd57991708a2e2734b6daba),
[Champions Lab](https://github.com/joshuamatalon/champions-lab),
[ai-vgc](https://github.com/Nisanth-Nimashakavi/Ai-vgc),
[poke-env observations](https://github.com/hsahovic/poke-env/blob/master/examples/tracking_observations.py).
