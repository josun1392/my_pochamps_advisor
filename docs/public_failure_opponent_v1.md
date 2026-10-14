# Public failure-aware opponent V1

An opt-in `public_failure_aware_v1` wraps a separately hash-bound frozen learned
opponent (or the existing max-power script). Existing opponents are unchanged.
The source trainer accepts its frozen model through `frozen_opponents`; the
spawn factory loads the same strict model/encoder contract as before.

The guard requires two explicit public failures of the same own executed move
and a confirmed own prerequisite: awake Snore/Sleep Talk without Comatose,
Fling without an item or with a pinned-catalog Mega Stone, or repeated explicit
heal failures at full HP. Unknown information never establishes a guard.
Misses, immunity, target-dependent failures and called moves are insufficient.
Switching clears evidence. Own HP changes invalidate healing evidence; own
status/ability changes invalidate sleep-move evidence; own item changes
invalidate Fling evidence. A successful subsequent attempt clears its guard.

If the original proposed action is guarded, choose a deterministic legal
alternative using the existing nominal base-power prior, then stable native
action order. With no alternative, retain the legal original action. Native
requests, masks, reward and execution remain authoritative. These are cautious
preferences, not claims that a move is universally illegal or an alternative
optimal. Full-HP healing can have value after incoming damage.

Coordinator-only public metrics distinguish availability, selection and native
public failure. Rest, Wish and allies-target heals are included in the new
metrics; historical tactical counters retain their original meaning. Consecutive
voluntary switches are descriptive, not automatically redundant or bad.

The Gym adapter counts rejected choices in primary and automatic-wait steps.
Checkpoint retry audits contain the independently owned player-visible masks,
choice, phase and trapping flags before/after rejection; they are never returned
as policy features or privileged critic inputs. The native service still does
not expose exact choice-error reasons, so the audit explicitly records an
unknown reason. It cannot explain historical unrecorded rejections.

The new experiment replaces only the historical five-way mixture's frozen-v4
slot: nominal 20% of episodes, not guaranteed 20% of transitions. Initial
max-power-slot replacement was rejected before training due to insufficient
observed guard exposure. The original V8 teams/pick-three protocol, categorical
V2, PPO2477 transfer/fresh Adam, gamma 1, GAE .95, PPO hyperparameters and
guaranteed-first production recommendations remain unchanged. Experiment plans,
native sanity results, banks and trained models live outside the repository.
