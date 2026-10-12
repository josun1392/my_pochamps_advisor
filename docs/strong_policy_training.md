# Public-trajectory offline learning with the existing autonomous trainer

This experimental CPU workflow retains guaranteed-first production ranking. BC
and AWR candidates are local learned evidence only. Existing checkpoints and UI
rollback remain valid. Data contains executed partial-observation trajectories,
not optimal labels or perfect-information search results.

## Standalone PowerShell workflow

From the migration checkout, install the existing learning extra and supply the
clean pinned native engine checkout. Keep the roughly1GiB trajectory data outside
the repository. The versioned native team bank is already included.

```powershell
uv sync --extra learning --dev
$engine = 'C:\path\to\pinned-pokemon-showdown'
$data = Join-Path $env:LOCALAPPDATA 'PokeAdvice\training\public-v6'
$run = Join-Path $env:LOCALAPPDATA 'PokeAdvice\training\strong-policy'
uv run --extra learning python scripts/collect_showdown_public_trajectories.py --config config/learning/strong_collection_cpu.json --checkout $engine --output $data
uv run --extra learning python scripts/train_showdown_autonomous.py --config config/learning/strong_offline_cpu.json --checkout $engine --offline-dataset $data --output $run
```

Preset:8real spawn workers,4parent tensor threads,50% process-tree CPU cap,
12GiB committed-memory cap,30min trainer runtime,3independent learning seeds.
The collector has a10min cap and retains complete episode targets. It refuses
an existing output; unfinished collection is not claimed to resume exactly.
Dataset files are memory-mapped and SHA-verified before learning. The supplied
training preset is an experimental configuration, not an endorsed best policy.

Stop and restore with the existing trainer:

```powershell
uv run --extra learning python scripts/train_showdown_autonomous.py --output $run --stop
uv run --extra learning python scripts/train_showdown_autonomous.py --config config/learning/strong_offline_cpu.json --checkout $engine --offline-dataset $data --output $run --resume
```

Immutable checkpoints preserve model and Adam state. Offline epochs checkpoint
every4completed epochs and after fitting. A partial/unsaved epoch restarts from
the last persisted epoch; incomplete PPO rollouts are discarded. Dataset and
frozen-opponent identities must remain unchanged. A changed configuration
requires a new run directory. Validation and terminal counters are program-managed.

Use an independently opened terminal for unattended learning. Codex-launched
processes can inherit its lifetime job; disconnect survival is not guaranteed.
Existing `--detach` verifies job independence and rejects unverifiable launch.
Every process has explicit runtime/resource limits and owns its native children.
Do not describe an interrupted rollout as exactly recovered.

## Comparison and evidence

`scripts/evaluate_showdown_study.py --config STUDY.json --output NEW_DIRECTORY`
reuses the existing native paired evaluator for up to4scopes/20policies/6rivals.
Specify SHA-resolved local models, separate validation/test/unseen scopes,
fresh offsets and bounded runtime. Results include per-opponent wins/losses,
case-cluster confidence intervals and tactical diagnostics. Full records use
lossless gzip JSON. Keep final scopes unopened until selection ends.

The native bank contains191training base species and40reserved unseen base
species with varying maintained Champions movesets. M-C TeamValidator rejects
duplicate items and other illegal teams. Native random spreads are legal
coverage fixtures, not expert competitive spreads; bring6/pick3selection is
random and is not learned in this experiment. No full legal-roster coverage or
human-level strategy claim follows from this dataset.
