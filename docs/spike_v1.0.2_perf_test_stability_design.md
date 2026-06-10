# v1.0.2 Perf Test Stability Design

## Current State

`tests/test_damage_perf.py` contains four timing tests around `advisor.damage.formula.calc_damage_rolls()`.

The repeatedly unstable test is:

```text
tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average
```

Current settings:

- `PERF_ITERATIONS = 1000`
- `PERF_REPEATS = 5`
- `PERF_WARMUP_ITERATIONS = 100`
- assertion uses the median of five average-per-call samples
- threshold is `0.120000ms`

The test builds a `DamageContext` with:

- Fire-type `flamethrower`
- Charizard-like attacker and Venusaur-like defender types
- sun weather
- defender Light Screen
- grounded inputs
- attacker item: `life-orb`
- defender item: `occa-berry`
- attacker species: `charizard`
- defender species: `venusaur`

Then it directly calls `calc_damage_rolls(ctx)` in a tight loop.

## What The Test Measures

The test measures core damage calculation hot-path timing, not LLM item context overhead.

The measured path includes:

- `calc_damage_rolls()`
- type chart loading via cached `load_type_chart()`
- grounded checks
- move flags
- item modifier resolution
- Life Orb final damage modifier
- Occa Berry defender berry modifier
- weather modifier
- screen modifier
- Q12 modifier chaining and damage roll generation

The measured path does not include:

- `llm/advisor_client.py`
- default advice payload filtering
- registry constants
- `build_ui_advice_payload()`
- Gemini prompt construction
- `llm/advisor_damage_estimate.attach_selected_move_damage_estimate()`
- item/advice context helpers such as `resist_berry_context`, `type_boost_context`, or `speed_order_context`
- `ko_context`
- UI code

Therefore, recent v0.94-v1.0.1 LLM context and registry work is unlikely to directly affect this timing test unless it changed imported core damage modules, which it did not.

## Observed Failure Pattern

Recent failures have clustered near the threshold:

- `0.122099ms` over `0.120000ms`
- `0.124845ms` over `0.120000ms`
- `0.123070ms` over `0.120000ms`
- `0.146497ms` over `0.120000ms`

The same test often passes on isolated reruns or after rerunning the perf file:

- isolated rerun 3x has repeatedly passed
- full `tests/test_damage_perf.py` rerun has repeatedly passed after a first failure
- full suite can still fail the same timing gate

This pattern points to timing sensitivity rather than deterministic correctness failure.

## Correctness vs Timing Failure

This is not currently evidence of damage correctness failure.

Reasons:

- No damage roll mismatch is reported.
- No formula assertion fails.
- `tests/test_advisor_damage_estimate.py` continues to pass.
- The unstable test only asserts elapsed time.
- The same calculation passes in isolated reruns without code changes.
- Recent failures occur even when no damage formula, raw roll, Q12, or `ko_context` code changed.

The failure should be treated as an environment/load-sensitive timing gate until proven otherwise.

## Threshold Sensitivity

The threshold is very tight:

- threshold: `0.120000ms`
- common failures: roughly `0.122ms` to `0.125ms`
- margin: about 2-5 microseconds above threshold for several runs

The larger `0.146497ms` failure still appeared in a full-suite run, where prior test load, process state, imports, CPU scheduling, and thermal/power state may affect timing.

The threshold may still be useful as a local performance guard, but it is fragile as a hard correctness-style CI gate on shared or busy environments.

This design does not recommend changing the threshold in v1.0.2. It recommends first improving measurement diagnostics and stability.

## Isolated Pass / Full-suite Fail Meaning

When isolated reruns pass but full-suite runs fail, likely explanations include:

- CPU scheduling noise
- background system load
- interpreter state after a long test run
- cache state differences
- thermal/power management
- garbage collection or memory pressure
- antivirus / filesystem / OneDrive interference
- Python process warmup differences

This does not automatically mean there is a real regression in `calc_damage_rolls()`.

However, repeated full-suite-only failures should still be tracked because they reduce confidence in the usefulness of the perf gate.

## Recent Item Context Impact Analysis

Recent v0.94-v1.0.1 changes added or refactored:

- `type_boost_context`
- `focus_band` `survival_context`
- `speed_order_context`
- registry-backed advice payload filtering
- prompt/contract/tests/docs

These changes affect LLM payload assembly and default advice serialization.

The unstable perf test directly imports and calls:

- `DamageContext`
- `calc_damage_rolls`
- `Field`
- `SideField`
- `GroundedInputs`
- `get_item`

It does not call the LLM payload/context layer. The registry cleanup in v1.0 lives in `llm/advisor_payload_contract.py` and `llm/advisor_client.py`, and should not directly affect `calc_damage_rolls()` timing.

Possible indirect effects are limited to normal Python process noise from importing more modules in the full suite, not hot-path logic changes in the tested function.

## Additional Measurements Needed

Before changing thresholds or test policy, collect more data:

- isolated test repeated at least 10 times
- full `tests/test_damage_perf.py` repeated at least 5 times
- full suite repeated when the machine is idle
- record median, min, max, and sample list for each failure
- compare first-run vs rerun behavior
- record Python version, CPU power mode, and whether OneDrive/antivirus activity is present
- optionally run with a small standalone timing script outside pytest to compare pytest overhead
- optionally compare with garbage collection disabled during the timing loop as an experiment, not as an immediate commit

Useful diagnostic output already exists in the assertion:

- median average
- threshold
- samples
- min / max
- isolated rerun command

## Stability Options

### Option A - Increase Warm-up

Increase `PERF_WARMUP_ITERATIONS`.

Pros:

- Conservative.
- Does not alter the measured function.
- May reduce first-run cache/interpreter warmup noise.

Cons:

- Does not solve full-suite CPU scheduling noise.
- Slightly increases test runtime.
- May hide cold-path regressions if those matter.

Risk: low.

### Option B - Increase Iterations Per Sample

Increase `PERF_ITERATIONS` for the tight item test.

Pros:

- Longer sample windows reduce timer noise.
- Median becomes less sensitive to one slow or fast call.

Cons:

- Increases runtime.
- Still sensitive to sustained CPU contention.

Risk: low to medium.

### Option C - Increase Repeats / Use More Robust Median

Use more repeats, such as 7 or 9, and keep median.

Pros:

- More robust to isolated spikes.
- Keeps the existing median-based style.

Cons:

- Increases runtime.
- Still fails if several samples are slow under full-suite load.

Risk: low.

### Option D - Outlier Handling

Use trimmed median or discard the first sample after warmup.

Pros:

- Can reduce first-sample or scheduling spike sensitivity.

Cons:

- Easy to make the test too forgiving.
- Needs clear documentation to avoid hiding real regressions.

Risk: medium.

### Option E - Threshold Reconsideration

Raise or recalibrate threshold based on observed environment data.

Pros:

- Directly reduces flake.
- May better match real local/CI environment.

Cons:

- Explicitly out of scope for v1.0.2.
- Can mask a real regression if done without enough baseline data.

Risk: medium; defer until data supports it.

### Option F - Separate Perf Tests From Correctness CI

Keep perf tests runnable but mark/report them separately from correctness tests.

Pros:

- Prevents environment noise from blocking unrelated correctness work.
- Makes performance work intentional.

Cons:

- Requires CI/test workflow policy change.
- Risk of ignoring performance regressions if not monitored.

Risk: medium; useful policy discussion, not a quick local fix.

### Option G - Environment-sensitive Marker

Introduce a marker such as `@pytest.mark.perf` or `@pytest.mark.environment_sensitive`.

Pros:

- Clear classification.
- Allows targeted local runs and separate CI lanes.

Cons:

- If used to skip by default, can weaken coverage.
- Requires test invocation policy updates.

Risk: medium; do not skip/xfail in v1.0.2.

### Option H - Baseline Comparison

Compare against a local baseline measured in the same run rather than a fixed absolute threshold.

Pros:

- More robust across machines.
- Can detect relative regressions.

Cons:

- More complex.
- Requires carefully chosen baseline contexts.
- Risk of hiding global slowdown if both baseline and target slow down.

Risk: medium to high; better as a later design if fixed thresholds remain noisy.

## Recommended v1.0.3 Path

Recommended:

**v1.0.3 - Perf Test Measurement Stabilization**

Conservative scope:

- Do not change thresholds.
- Do not skip or xfail.
- Do not change damage formula, raw rolls, Q12, or `ko_context`.
- Improve measurement stability and diagnostics only.
- Consider increasing warm-up and/or repeats modestly for `test_item_damage_calculation_under_point_12ms_average`.
- Keep the assertion and threshold unchanged.
- Add clearer documentation in the test or helper comment that isolated rerun should be used to distinguish environment-sensitive failures.
- Optionally add a local diagnostic helper test/script only if it does not alter CI behavior.

Preferred first implementation candidate:

- Increase warm-up for this test or helper from `100` to a slightly higher value.
- Consider increasing repeats from `5` to `7` while preserving median.
- Keep threshold `0.120000ms`.
- Re-run isolated 10x, perf file 5x, and full pytest.

If T1/T2 want zero timing behavior changes, choose:

**v1.0.3 - Perf Test Baseline Data Collection**

- Add documentation only.
- Keep tests unchanged.
- Collect repeated local measurements before implementation.

## Out of Scope

The v1.0.2 design excludes:

- threshold changes
- skip / xfail
- damage formula changes
- raw damage roll changes
- Q12 multiplier changes
- `ko_context` changes
- item context filtering changes
- new item mechanics
- Turn Engine
- item consumption
- fixture or legal fixture changes
- UI or sample changes
- logs, `.env`, secrets, API keys, or handoff capsule commits
