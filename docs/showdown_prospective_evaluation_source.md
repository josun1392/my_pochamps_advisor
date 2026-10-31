# Prospective sealed policy evaluation source v1

`advisor.learned_prospective_evaluation` is a coordinator-only input contract.
It neither loads policies nor executes evaluation/training. Historical V8,
Foundation/Adam, preview and production behavior remain unchanged.

The new source is **Q_eval_source_v1**, not a historical TRAIN prior:

- One predeclared native generator call returns 200 teams with the maintained
  pinned `full-domain.cjs` / `TeamValidator`; it creates no battles. The new
  wrapper only adds the maintained headless process options.
- Teams 0..199 form 100 fixed pairs, with no resampling or replacement. Cases
  0..3 are protocol/development; cases 4..99 are the 96 sealed source clusters.
- Each sealed case has two candidate team ownerships, both real native player
  seats, and three frozen rivals: Champions heuristic, tactical heuristic and
  the fixed V4 endpoint. There are **1,152 points per evaluated policy**, each
  mass **1/1,152**, with case mass 1/96.
- Ordered three-of-six and lead/reserve order are frozen per team/case. This
  is random preview fixed before outcomes, not learned preview.
- Four initial native seeds per case are frozen for ownership/seat conditions.
  Across policies and rivals a matched cell uses the same full scenario/seed.
  Divergent choices can consume RNG differently; equal downstream rolls are
  not claimed.

Full sets, case IDs, seeds and native snapshots are private coordinator inputs.
Actors receive only their actual authenticated player observations and native
35-action masks. No case, pool membership or source identity becomes a feature.

## Sealing and admission

The source manifest binds the private generated-team asset and exact 100 cases.
The readiness receipt additionally binds metadata-only historical overlap and
nonterminal protocol audits. `points()` refuses missing readiness, failed
admission, mass changes, duplicate seeds/teams and changed assets. Public
manifest access returns a copy. Runtime/source/model hashes must be checked
again before a separately approved comparison.

“Sealed” means immutable and performance-unexamined, not encryption or an OS
access-control guarantee. Git contains code/tests/contracts only, never the
private team asset, native snapshots, model ZIPs or evaluation results.

Historical overlap auditing covers the original Foundation's 82,569 retained
completed episodes, accessible source manifests/cases/roots/subsets and native
banks. Report exact covered files, semantic full-team/base-roster/seed/case
overlap and missing sources; never claim coverage of deleted/unarchived data.
Source novelty is not species-unseen or individual-set-unseen generalization.

Any duplicate, unsupported encoding, invalid team, unresolved request or hash
failure stops execution. No outcome-dependent rejection, replacement or
renormalization is allowed. An incomplete source remains incomplete.

## This stage's native permission

Only two fixed **protocol** cases may each reset, reset again with identical
inputs, and restart the saved checkpoint: six starts total, **zero native
steps**, no terminal games or policy/value outputs. Native generated teams
are already validated by the maintained native generator. Encoding public
fixtures for shape/finite-value checks is allowed; model forward is not.

## Future comparison procedure (not authorized here)

1. Bind the original Foundation ZIP and each future fixed-budget candidate ZIP,
   encoder/action/public-information contract and code hashes in a signed-off
   addendum before examining any result. Do not select candidates by this panel.
2. Execute all 1,152 points per approved policy, T=1 argmax, with actual seat
   assignment and unchanged frozen opponents. Use the maintained native
   evaluator's legality/retry/progress guards and bounded CPU/RAM controls.
3. Key results by source SHA + candidate SHA + case/ownership/seat/rival. Skip
   only verified complete receipts. A STARTED item with no result is an error,
   not permission to silently start an extra game. STOP/resume preserves files;
   no unlimited restart or extra budget is implied.
4. Report W/L/draw/truncation/rejection/encoding failures explicitly. Primary
   win rate is W/N over the full scheduled valid panel, with draw-as-half score
   secondary. Unresolved/missing outcomes prevent a final primary comparison;
   do not count them as losses or shrink the denominator.
5. Compare each candidate with Foundation on corresponding cells. Bootstrap
   all 12 cells together in each of the 96 case clusters (20,000 frozen draws).
   Report per-rival results and training repetitions separately. Cases are not
   1,152 independent observations. No automatic promotion or best-checkpoint
   substitution is allowed.
6. After first use, mark the panel consumed. Reusing it for paired diagnostics
   is allowed only with that label; it is not a new independent confirmation.

Read-only verifier:

```powershell
uv run python scripts/verify_prospective_evaluation_source.py `
  --manifest <external-source-manifest> --sha256 <source-sha> `
  --readiness <external-readiness-receipt> --readiness-sha256 <receipt-sha>
```

No command in this document authorizes terminal evaluation or model training.
