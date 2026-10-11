# SHOWDOWN_M_C_AUTONOMOUS_INTEGRATION_V1

## Bounded contract

The first integration is an explicit offline call from an immutable
`runtime_snapshot_ready` capture to detached Showdown results. Existing
observation/reducer/store/session/UI/explanation and ranking owners retain
their behavior. There is no default backend switch, provider call, server,
ranking change, or simulation-to-observation writeback.

Pin: `smogon/pokemon-showdown@942cda71d14bf0618bd57991708a2e2734b6daba`.
Format: `gen9championsbssregmc`, native `champions` mod, singles, six registered
sets and exactly three explicit picks. Champions `evs` are stat points, at most
32 per stat and 66 total, not main-series EV units. Native team validation runs
before battle creation. Native choices own damage, accuracy, priorities,
status, residuals, item consumption and switch requests.

`simulate_detached_showdown(runtime_snapshot, scenarios, bridge)` requires:

- A validated same-session state fingerprint, confirmed singles format, and
  known positive current/max HP plus non-fainted active Pokémon on both sides.
- Each scenario's unique ID, explicit assumptions, four 16-bit seed values,
  complete six-set teams, three picks per side, explicit modeled history, and
  one explicit choice per requesting side. Empty choices mean a waiting side;
  actions are never automatically selected.
- Species, native maximum HP, and known item/ability/type/level/status must
  agree with the modeled state. Known moves must be present in the set. Active HP and known stat stages are overlaid
  on a detached move boundary. Observed final combat stats currently fail
  closed because no reverse set adapter has been validated. Other concrete
  runtime mechanics without an adapter reject the call with their field paths.

Results contain native pre/post summaries, legal requests including forced
replacement/pivot boundaries, protocol event strings, root/post native
checkpoints, scenario assumptions, seeded-sample interpretation and timing.
No probability or rank is assigned. Each scenario fails independently.

`resume_detached_showdown(runtime_snapshot, checkpoint, choices, bridge)`
validates the checkpoint digest, engine, format, session and originating
runtime fingerprint. A newer observation makes the checkpoint stale.
`Battle.toJSON/fromJSON` preserves the modeled PRNG and internal state, but
`fromJSON` must receive a deep copy every time: repeated deserialization of
one raw object can mutate nested state. Checkpoint digests are corruption
detection, not a security boundary or proof that a model is observed truth.

## Reconstruction limits

Reconstruction is a **partial observed overlay over an explicit hypothetical
history**, not recovery of the original game's complete hidden state. Native
checkpoint restoration is exact for that modeled state; it is not an exact
restore of the human battle. Unknown PP, counters, bench state, entry history,
volatiles remain assumptions. The supplied
history is an executable hypothesis, never an observation ledger. Generic
known runtime mechanics outside the fields above cause rejection, so these
results are experimental conditional evidence and do not feed recommendations.
Existing M-A roster data is neither relabeled nor used as M-C legality.

## Reproduction

Node >=22.18 and the project's Python/uv environment are required. Build in a
new external directory; setup refuses existing directories and repository
subdirectories. It fetches the exact pin and uses upstream's lockfile with
dependency lifecycle scripts disabled. Native optional dependency binaries
remain installed so esbuild can build. No battle server is started.

```powershell
uv run python scripts/setup_showdown.py --destination C:\temp\poke-showdown-mc
uv run python scripts/verify_showdown_integration.py --showdown-checkout C:\temp\poke-showdown-mc
$env:POKEADVICE_SHOWDOWN_CHECKOUT = 'C:\temp\poke-showdown-mc'
uv run pytest tests/test_showdown_integration.py -q
```

The checkout remains external and uncommitted. The transport checks the Git
pin and clean tracked source state before every batch. Default test runs skip
native integration tests when the checkout is not explicitly configured;
Python boundary tests still run. Missing dependencies/timeouts fail locally
without falling back to custom mechanics or changing live state.

## Decision and next milestone

CONDITIONAL GO for a foundation: native M-C execution and detached restoration
can replace mechanic implementation inside future bounded consumers. This
does not authorize removal of the custom engine or production ranking inputs.
Next: expand observation-to-native-state reconciliation for trusted turn,
PP/status progression, field/side conditions, final stats and owner-mapped
bench slots, retaining rejection for unsupported known mechanics. Then compare
Showdown samples against existing candidate evidence behind a disabled shadow
evaluation entry point without changing ranking or observed state.

## Verified evidence — 2026-10-11 KST

Fresh installer execution succeeded outside the repository. Windows x64,
Python 3.11.9, Node 22.20.0; no provider or battle server was used.

- A native M-C battle finished in 29 turns / 33 decisions. Native state
  roundtrips at every decision matched the independent control battle.
- Protect, priority, damage, Focus Sash consumption, forced replacement and
  Champions freeze-counter restoration executed in the native engine.
- Item hypotheses: no item, Focus Sash, Sitrus Berry and Choice Scarf; the
  first attack left Scizor at 0 / 1 / 0 / 0 HP respectively. These are seeded
  outcomes of these fixtures, not generally applicable item conclusions.
- 64 seeded Air Slash samples included 58 hits and 6 misses and multiple
  damage outcomes. These counts are not an accuracy probability estimate.
- Native restore plus explicit choice, 200 iterations: median 0.843 ms,
  p95 1.160 ms. Python four-scenario batches, 30 repetitions: first 431.66 ms,
  median 424.45 ms, maximum 451.22 ms. Each Python batch starts a process and
  revalidates source pin/teams; these measurements are fixture-specific.
- Integration/boundary tests: 21 passed. Related runtime, reducer, store,
  session, UI projection, ranking, strategy and explanation regressions:
  85 passed. Roster, existing damage, field and Smogon parity verification
  scripts passed after their respective dependency setup. Full L3 was not run.
- The first new environment selected Anaconda Python and failed Qt DLL
  import; a separate standard Python 3.11 environment resolved it. Initial
  existing parity checks lacked `@smogon/calc`; installing the locked bridge
  dependencies resolved them. No production fixes were needed for either.

Work is based on canonical remote `bde87bd3010b22ad02291396b13de6bf9e580529`
in a separate managed worktree. The original checkout's divergent commit and
five pre-existing changed/untracked files are preserved; no unrelated local
history is included in the integration branch.

References reviewed: [native simulator API](https://github.com/smogon/pokemon-showdown/blob/942cda71d14bf0618bd57991708a2e2734b6daba/sim/SIMULATOR.md),
[native formats](https://github.com/smogon/pokemon-showdown/blob/942cda71d14bf0618bd57991708a2e2734b6daba/config/formats.ts),
[Ai-vgc](https://github.com/Nisanth-Nimashakavi/Ai-vgc),
[champions-lab](https://github.com/joshuamatalon/champions-lab),
[poke-env](https://github.com/hsahovic/poke-env). The selected dependency is
Showdown's maintained simulator itself; no bot, training or server client
framework is added to the human-advisor architecture.
