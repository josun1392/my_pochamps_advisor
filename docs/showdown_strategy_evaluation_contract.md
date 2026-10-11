# Native strategic evaluation v2

`showdown-shadow-config-v1` remains compatible. Opt-in v2 adds a bounded native
rollout policy and an explicit `opponent_actions` array to each hypothetical set.
Each `{action_id, choice}` is a separate conditional evaluation. There is no
implicit probability prior over sets or actions and no averaging across them.

`showdown-rollout-policy-v1` reuses the pinned Showdown `RandomPlayerAI` request
consumer. Both sides' future actions and forced replacements are hypothetical.
They use separate reproducible native PRNG instances, independent of battle RNG.
The initial human candidate and initial hypothetical opponent action are fixed.
All mechanics, legal requests, PP, pivot queues, faint replacements, items,
abilities, status and end-of-turn effects execute in Showdown. The rollout stops
on native termination or its decision-request budget (not a turn count).

`showdown-strategy-shadow-v2` binds the complete runtime capture, session, decision
owner/branch, config, seeds, native root checkpoint, initial candidate choices,
opponent action and hypothesis identities. The evidence class is explicitly
`monte_carlo_estimate`. Unsupported roots/candidates remain rejected, never dropped
from a probability denominator. Known/Unknown observation compatibility uses the
existing observation adapter and fails closed on contradictions.

Wins, losses, draws and unfinished samples sum to the seed count. `win_rate` is
the empirical probability of a native win **within the configured horizon**,
conditioned on this state, opponent set/action and rollout policy. Completion
bounds are `[wins/n, (wins+unfinished)/n]`: they describe unresolved samples, not
statistical confidence or exact probability. Complete samples estimate the
chosen policy's win rate, not optimal play or an unconditional real-battle win rate.

First-choice evidence is retained separately as `showdown-sampled-first-request-v1`.
It measures outcomes at the first native request after the explicit initial
choices, with a request-state histogram and pending-action count. A pivot may
stop before the opponent's queued move; this scope does not promise a complete
turn or a complete selected-action KO probability. Extending the rollout horizon
does not change these first-request aggregates.

Experimental ranking is disabled by default and separately enabled. It compares
the worst configured scenario's mean position value: terminal win/loss/draw is
+1/-1/0; unfinished value is normalized remaining team HP difference. It has no
exact or guaranteed authority and does not alter the existing preferred frontier,
selected-action ledger, ranking policy, observation ledger or replay. Incomplete
scenario/candidate coverage makes experimental ranking unavailable.

Rollback removes the opt-in configuration, closes the local worker and restores
the existing behavior. No network, LLM/provider or public battle server is used.

The existing Qt strategy button evaluates v2 in a background worker, after
displaying its original captured recommendation. Results require the same full
runtime capture, session, UI basis and configuration generation before display.
Disabling or closing cancels the local process and invalidates pending callbacks.

When the legacy cycle reports `no_selectable_candidates`, v2 alone may use
`showdown-ui-candidate-intents-v1` to capture the user's assigned move IDs and
known bench identities. This is never a live selectability authority: its native
intent rows are `conditional`, and actual legality is tested separately for
every hypothetical root. `showdown-conditional-strategy-explanation-v1` carries
an empty default frontier, no guaranteed facts, no exact ledger and an explicit
notice that the old recommendation remains unavailable. It cannot bypass an
invalid session/snapshot/capture. Its results are not retained in the existing
exact C6 transition feature capture.

An optional `conditional_candidate_ids` list can narrow this hypothetical-only
comparison to the user's explicit attack/switch intents (for example the chosen
three of a registered six-member roster). IDs must be a nonempty unique subset
of the captured intents; no action is invented and the default candidate universe
is untouched. Without an explicit filter, illegal hypothetical choices stay in
the grid as rejected and make experimental ranking unavailable.

## Running the opt-in system

Install/build the existing external pinned engine with `scripts/setup_showdown.py`.
Export an explicit example config (all sets/history remain hypothetical):

```powershell
uv run python scripts/verify_showdown_strategy.py --export-demo <local-demo.json>
uv run python main.py --showdown-checkout <pinned-checkout> --showdown-shadow <local-demo.json>
```

Adapt the config's full teams, selected three, slot mapping/history, assumptions,
opponent action IDs/choices and seed bank to the battle being advised. Recorded
known observations are checked against these hypotheses; they are not changed by
the configuration. A literal empty opponent choice is permitted only when that
side's native request is waiting. `max_decisions` includes forced replacements.
The global limit is 32,768 possible decision requests, at most 64 seeds and 16
set/action cells; use a smaller seed/horizon budget for quick live comparisons.

Add `--showdown-experimental-ranking` only to display the separate experimental
comparison. The flag is false by default; the default recommendation is unchanged
even when enabled. The API rollback is `window.configure_showdown_shadow()`;
pending results and displayed experimental evidence are retired as well.

Reproduce the actual UI, seeded evidence, old/new comparison and performance:

```powershell
uv run python scripts/verify_showdown_strategy.py --showdown-checkout <pinned-checkout> --iterations 20 --seeds 16 --horizon 32
```

Upstream MIT request policy reused directly:
https://github.com/smogon/pokemon-showdown/blob/942cda71d14bf0618bd57991708a2e2734b6daba/sim/tools/random-player-ai.ts
Champions Lab's native-fork search corroborates the conditional rollout approach;
its doubles heuristic and custom value model are not copied into M-C Singles.
