# Bounded local strategy learning

This is an experimental CPU trainer. It never changes the guaranteed-first
production policy, contacts providers or joins a battle server. It uses the pinned
local Showdown M-C engine, SB3-contrib MaskablePPO and poke-env visible heuristics.
The old model and observation contract remain supported.

From the migration checkout, in PowerShell:

```powershell
$env:UV_PROJECT_ENVIRONMENT = Join-Path $env:LOCALAPPDATA 'PokeAdvice\learning-env'
uv sync --extra learning --dev --python 3.11
uv run python scripts/setup_showdown.py --help
# Set this to the pinned checkout installed by setup_showdown.py.
$engine = $env:POKEADVICE_SHOWDOWN_CHECKOUT
$run = Join-Path $env:LOCALAPPDATA 'PokeAdvice\training\my-run'
uv run --extra learning python scripts/train_showdown_autonomous.py --config config/learning/autonomous_cpu.json --checkout $engine --output $run
```

The sample config allows one hour, four native workers, one Torch thread, a 12.5%
CPU cap across the process tree and a 3 GiB aggregate committed-memory cap.
The standalone trainer blocks external Python network connections; only local
loopback traffic needed by Windows asyncio is allowed.
Runtime cannot exceed six hours; resource configuration is validated before start.
Copy the config to a new file to change seeds, budgets or opponent mixtures. Never
reuse a run directory with a different config. No GPU use is enabled.
To extend a completed run, create a new config/run directory and set an experiment's
`initial_model` to the preserved best checkpoint and `warmstart_decisions` to0.
Its encoder must match `encoder_version`. The optimizer is restored; `steps` is the
new additional PPO budget. An interrupted run instead uses the unchanged config
and `--resume`.

`state.json` records transitions, completed battles, optimizer steps, validation
results, resource usage and the strongest checkpoint path. Each checkpoint directory
contains immutable `model.zip`, its version/hash/catalog manifest, and validation
results. SB3 saves model and optimizer state. Trust only locally produced artifacts;
its pickle-based loader does not sandbox downloaded models.

The compatible `completed_battles` counter includes ended and time-limited episodes;
`episode_outcomes` separates wins, losses, draws and truncations. Checkpoints written
by older trainer builds did not persist that breakdown and are not retroactively relabeled.

Training is supervised heuristic warm-start followed by PPO.
`warmstart_learning_rate` can be set independently of the PPO learning rate;
it is restored before PPO. Teacher-data accuracy is a training-fit diagnostic,
not a battle win rate. Omitted warm-start rate preserves the older coupled setting.
The versioned v2 encoder uses a pooled public context and shared attack/switch rows. It sees only
the agent's private request, already revealed opponent information, public history
and static native Dex facts. It never reads hidden teams, checkpoints or RNG.
The v2 encoder requires `env.observation(side, include_history=True)` so its public
history features are identical during training, evaluation and UI inference;
missing history fails closed. v1 callers remain compatible.
Native slot actions and masks stay authoritative. The value is bounded discounted
sparse return, not an exact win probability. Hashed curriculum split namespaces
prevent the long-running additive seed overlap while preserving v1 replay semantics.

All checkpoint selection uses validation scenarios. More steps do not imply a
better model; ties retain the old best and plateaus advance to the next experiment.
An optional historical opponent is frozen from the best available model when an
experiment starts. It is a checkpoint-opponent experiment, not unrestricted self-play.
Final test/unseen-species grids run once after selection and are never used to tune
the candidate. Repeatedly inspecting them to choose new settings invalidates that
holdout; use a new versioned test offset for a later independent study.
`reference_models` optionally maps up to three names to trusted local checkpoints
for paired final evaluation, e.g. `previous_action` for the prior action-conditioned model.

Stop and resume:

```powershell
uv run --extra learning python scripts/train_showdown_autonomous.py --output $run --stop
uv run --extra learning python scripts/train_showdown_autonomous.py --config config/learning/autonomous_cpu.json --checkout $engine --output $run --resume
```

The trainer finishes the current safe operation, saves a recoverable checkpoint,
and closes native workers. A watchdog terminates the entire Windows job after a
30-second shutdown grace. On restart it restores the model/optimizer and starts
fresh native episodes. A partial rollout is discarded; interrupted episodes are
not claimed to have been recovered exactly. Resume grants a new bounded runtime.

`--detach` is optional and fails closed if the process remains in its launcher's
job. The current Codex host's breakaway probe remained in an inherited Windows job,
so continued execution after Codex disconnect/exit has **not been guaranteed**.
Use foreground mode from a separate user PowerShell terminal for unattended work;
keep that terminal/session open. Do not assume `--detach` succeeded unless its
`control.json` confirms no inherited job. The trainer's own kill-on-close job,
deadline, memory/CPU caps and saved checkpoints still contain each run.

Final artifacts are experimental opt-in inputs to the existing learned-strategy
interface: use the selected model path, its manifest SHA and the matching catalog.
They do not replace exact evidence or sampled native evaluation. v1 remains a
working rollback artifact at `models/showdown_initial_v1/model.zip`.

Tactical curriculum experiment (V4 curriculum; compatible V3 encoder/model):

```powershell
uv run --extra learning python scripts/train_showdown_autonomous.py --config config/learning/tactical_cpu.json --checkout $engine --output $run
```

This bounded 30-minute template uses three independent training seeds, a frozen
V3 source, public tactical demonstrations and native-progressed mid-battle
starts. Half the curriculum remains broad; unseen species remain reserved.
Change the output directory for a new run. Prefix/motif metadata is coordinator
only; agent tensors and rewards retain their original contracts. The new
`tactical_heuristic` teacher corrects poke-env's Target enum setup gate without
changing `heuristic` or `champions_heuristic` benchmark behavior.
Warm-start manifests report retained/attempted teacher action classes and fit
accuracy by class. These are supervised-fit metrics, not strategic strength.
Do not infer good switching from switching frequency alone.
For independent seed comparisons set each experiment's `historical_model` to
the same trusted frozen checkpoint. Omitting it preserves the existing league
behavior: a later experiment can freeze a previous experiment's selected best.
The opponent manifest records the actual SHA in either case.

For a NEW, predeclared held-out evaluation after validation-only selection:

```powershell
uv run --extra learning python scripts/evaluate_showdown_generalization.py --checkout $engine --frozen-opponent models/showdown_generalization_v3/model.zip --model "candidate=$model" --model "previous_action=models/showdown_action_v2/model.zip" --model "previous_generalization=models/showdown_generalization_v3/model.zip" --curriculum-version showdown-learning-curriculum-v4 --tactical-baseline --tactical-diagnostics --cases 96 --offset 180000 --output $evaluation
```

The recorded study's offset180000 is already inspected after its final report;
choose a fresh offset for later studies. Evaluate V3 broad curriculum separately
to avoid claiming that tactical fixture performance proves broad strength.
Affordance counts use only public type priors/HP/request legality. First-action
branch diagnostics (`evaluate_showdown_tactical_branches.py`) reuse native
checkpoints and fixed continuations; they are sampled conditional evidence,
never optimal-action or exact-probability labels.
