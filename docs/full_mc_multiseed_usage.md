# Full M-C independent CPU studies

Use a Python3.11 learning environment (`uv sync --extra learning`) and the pinned
Showdown checkout942cda71d14bf0618bd57991708a2e2734b6daba. Run from the migration
worktree on codex/showdown-mc-integration-v1; preserve the original master checkout.
No providers/public server/GPU are used. These commands preserve default advice.

```powershell
uv run --extra learning python scripts/train_showdown_autonomous.py --config config/learning/full_mc_disjoint_cpu.json --checkout C:\path\to\pokemon-showdown --output C:\training\mc-disjoint-new
uv run --extra learning python scripts/train_showdown_autonomous.py --config config/learning/full_mc_roster_cpu.json --checkout C:\path\to\pokemon-showdown --output C:\training\mc-roster-new
```

Run sequentially. Each study caps its owned process tree at8spawn workers,
50%CPU,12GiBRAM,7200s; three independent seeds and one matched initialization control each allow
131072newPPOtransitions. Default tensor deviceCPU. Checkpoints every32768steps
include optimizer state, and fixed validation runs select the earliest maximum
without truncated battles. Neither study runs final tests while tuning.
Output `state.json` records actual transitions/terminal versus truncated battles,
curves, model identities, worker memory/CPU and coordinator coverage. `STOP`:

```powershell
uv run --extra learning python scripts/train_showdown_autonomous.py --output C:\training\mc-roster-new --stop
uv run --extra learning python scripts/train_showdown_autonomous.py --config config/learning/full_mc_roster_cpu.json --checkout C:\path\to\pokemon-showdown --output C:\training\mc-roster-new --resume
```

Resume preserves weights/Adam and rejects changed config/domain/catalog/source
bindings. Native episodes and partial rollouts restart; interrupted rollouts are
not exactly recovered. Foreground Codex execution does not guarantee survival
after disconnect. Use the standalone process in your own terminal for unattended
runs, within its deadline/STOP control. `--detach` only accepts verified process
job separation; do not assume it works on every launcher.

V7 fresh seeds41011/41017/41023 train168species and preserve12validation,
12test and39historical reserved species. The matched warm control starts from
PPO2477, whose ancestor training may have exposed some V7 holdout species; its
results are not species-unseen evidence. V8 warm seeds42013/42019/42023 and
matched fresh control use all231species,4096native-validated training teams.
V8 validation/final/rare-Mega banks use unique unordered teams and joint
species/moveset combinations with independent seeds. Individual native sets may
recur; overlap is reported. V8 exposes historical held-out species, so only
team/configuration generalization applies to its future evaluations.

The `catalog_bindings` copies keep historical zip bytes/optimizer unchanged;
explicit manifest conversion checks every old public catalog fact recursively.
Added static form facts are untrained and are not promoted into observations.
Original models and their original catalogs remain usable unchanged.

After both studies finish, use `prepare_showdown_full_mc_evaluation.py` with their
common run-root. It freezes per-seed validation selections without reading final
results and emits predeclared final-study configs. Inspect `plan.json` before any
new research: these final IDs become **previously inspected** after closure and
must never be reused as tuning targets. Repeated future studies need new IDs and
a new artifact directory; preparation refuses to overwrite selected artifacts.

Training remains battle-action learning35native choices. Bring6/pick3 is an
explicit coordinator fixture. No120action ordered-preview policy is trained.
Legal random-team diversity is not competitive usage realism. Public-state-v2
preserves unknowns/history but the compact V3 encoder does not represent every
public volatile/transformation/history interaction. These limits remain visible.

Rollback: leave learned inference disabled, or select the original model with its
original catalog/SHA. Default guaranteed-first ranking has not been modified.
