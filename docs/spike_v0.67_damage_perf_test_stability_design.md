# v0.67 Damage Perf Test Stability Design

## Current State

The damage formula and raw damage rolls are core calculation paths:

- `advisor/damage/formula.py` owns `DamageContext` and `calc_damage_rolls()`.
- `advisor/damage/rolls.py` owns KO chance helpers over damage roll lists.
- `advisor/damage/item_modifiers.py` owns supported item modifier lookup for the damage engine.
- `tests/test_damage_perf.py` contains microbenchmark-style regression tests for baseline, field, item, and ability damage calculations.

The specific flaky test observed during v0.60 was:

- `tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average`

The current implementation measures one timed loop:

- build one representative `DamageContext`
- run `calc_damage_rolls(ctx)` for 1000 iterations
- compute average milliseconds per call
- assert the average is below `0.12ms`

Observed history:

- v0.60 full pytest had one failure against the `< 0.12ms` threshold.
- The failed value was reported as about `0.149357ms`.
- The same perf test passed when rerun in isolation three times.
- v0.60 changed LLM/context code and docs, not damage formula or raw roll code.
- Later full pytest runs in v0.61, v0.63, v0.64, and v0.66 passed.
- v0.66 full pytest result was `826 passed, 2 deselected`.

`pyproject.toml` currently defines a `slow` marker but no dedicated `perf` marker. Default pytest options exclude `slow` tests, not perf tests.

## Problem Definition

Microbenchmark-style perf tests are useful, but they are sensitive to local runtime noise:

- CPU scheduling
- background tasks
- thermal or power state
- full-suite order
- Python warmup/cold caches
- file system or import churn near the measurement window

If the threshold is too tight and the measurement uses only one timed sample, a transient outlier can look like a real performance regression. That makes push decisions harder, especially when the touched code is unrelated to the damage engine.

At the same time, simply loosening the threshold or skipping the test is unsafe:

- true damage formula regressions could be missed
- the performance budget would become unclear
- future work could accidentally make the core calculator slower

The project needs a clearer distinction between:

- correctness tests
- lightweight performance smoke tests
- dedicated performance investigation / benchmark runs
- exceptional push decisions after T1/T2 review

## Goals

- Continue detecting damage formula performance regressions.
- Reduce flaky full-suite failures caused by transient local load.
- Do not arbitrarily relax the existing threshold.
- Do not hide the test with skip or xfail.
- Keep damage formula and raw roll code untouched during perf test policy work.
- Make local failure triage repeatable.
- Keep regular feature work separate from perf policy changes.
- Improve failure messages so the next person has a clear rerun command.

## Options Comparison

### Option A - keep current test unchanged

Pros:

- Simplest option.
- Keeps the current threshold and behavior.
- No implementation risk.

Cons:

- Full-suite flake can recur.
- One outlier can fail the run.
- Failure output does not guide isolated rerun policy.

Assessment:

- Acceptable as a short-term baseline, but it does not solve the observed issue.

### Option B - recommend isolated perf mode

Run perf tests separately when investigating performance:

```powershell
uv run pytest tests/test_damage_perf.py -q
```

Pros:

- Reduces full-suite contamination.
- Easy to document.
- Matches the v0.60 triage path that passed isolated reruns.

Cons:

- If perf tests are removed from normal full pytest, full-suite performance regression detection becomes weaker.
- Requires policy discipline.

Assessment:

- Useful as a triage policy, but should not be the only solution unless CI is explicitly split.

### Option C - repeated measurement with median or percentile

Run several measurement rounds and assert on the median, or another robust statistic.

Pros:

- Outlier-resistant.
- Still detects sustained slowdown.
- Keeps the threshold meaningful without loosening it.

Cons:

- Slightly increases test runtime.
- Needs careful failure output so it remains easy to debug.

Assessment:

- Strong candidate for v0.68.

### Option D - warmup before measurement

Run a small number of untimed calls before timing begins.

Pros:

- Reduces cold start and cache noise.
- Cheap and simple.
- Keeps production code untouched.

Cons:

- Does not fully solve CPU scheduling or background load.
- Works best combined with repeated measurement.

Assessment:

- Good small improvement for v0.68.

### Option E - add a perf marker

Mark perf tests separately:

```python
@pytest.mark.perf
```

Pros:

- Makes test categories explicit.
- Allows CI/local policies to run perf separately if desired.
- Cleaner long-term suite structure.

Cons:

- Requires `pyproject.toml` marker registration.
- Requires a clear CI/local command policy.
- Might be misused to skip perf tests too often.

Assessment:

- Good follow-up, but not required for the first stabilization pass.

### Option F - adjust the threshold

Raise the `< 0.12ms` threshold.

Pros:

- Fastest way to reduce failures.

Cons:

- Weakens the performance guard without evidence.
- Could mask real regressions.
- Conflicts with the v0.67 goal.

Assessment:

- Not recommended for v0.67/v0.68 unless repeated evidence shows the budget itself is unrealistic.

## Recommended Direction

T3 recommendation:

- Do not change damage formula code.
- Do not relax the threshold in v0.68.
- Do not skip or xfail the perf test.
- Stabilize the measurement harness first.

Recommended v0.68 implementation package:

- Add warmup calls before timed measurement.
- Run multiple measured rounds.
- Assert on median average milliseconds per call.
- Keep the current threshold unless T1/T2 explicitly approve changing it later.
- Improve assertion messages with:
  - measured samples
  - median
  - threshold
  - isolated rerun command
- Keep changes limited to `tests/test_damage_perf.py`.

This approach preserves the intent of the existing perf guard while making it less vulnerable to one noisy sample.

## Proposed v0.68 Candidate

`v0.68 - Damage Perf Test Stability Implementation`

Include:

- modify only `tests/test_damage_perf.py`
- helper for repeated average measurement
- warmup run before timing
- median-based assertion
- existing thresholds preserved by default
- clearer failure messages
- full pytest verification

Exclude:

- damage formula optimization
- threshold relaxation
- skip or xfail
- production code changes
- LLM/context code changes
- fixture changes

Possible helper shape:

```python
def _measure_average_ms(func, *, iterations: int, rounds: int, warmup: int) -> tuple[float, list[float]]:
    for _ in range(warmup):
        func()
    samples = []
    for _ in range(rounds):
        start = time.perf_counter()
        for _ in range(iterations):
            func()
        samples.append((time.perf_counter() - start) * 1000 / iterations)
    return statistics.median(samples), samples
```

Example assertion message:

```text
median 0.119ms exceeded threshold 0.12ms; samples=[...].
If this appears load-related, rerun:
uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q
```

## Test Policy

Default policy:

- `uv run pytest -q` remains the normal full-suite gate.
- Perf tests remain meaningful and should not be ignored by default.
- A perf failure is not automatically considered a flake.

When a perf test fails:

1. Save the full pytest failure output.
2. Check whether the current branch changed damage formula, rolls, item modifiers, or other perf-path code.
3. Rerun the failing test in isolation three times.
4. Compare full-suite failure with isolated reruns.
5. If isolated reruns fail consistently, treat it as a likely performance regression.
6. If isolated reruns pass and touched code is unrelated, record it as possible environment/load flake.
7. A push with a perf flake exception requires explicit T1/T2 approval.
8. Do not relax the threshold, skip, xfail, or optimize unrelated code without a dedicated task.

Recommended commands:

```powershell
uv run pytest -q
uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q
```

If a repeated isolated check is needed:

```powershell
1..3 | ForEach-Object { uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q }
```

## Out of Scope

- code implementation
- test implementation
- threshold modification
- skip or xfail
- damage formula changes
- raw damage roll changes
- LLM/context changes
- UI changes
- fixture changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits
