# Offline training environment v1

This interface finishes the existing simulator; it does not replace observation
authority or production ranking. All episodes are hypothetical. No server,
provider, neural training, or exhaustive RNG enumeration is required.

`ShowdownEnvironment.reset(scenario, seed)` validates the native M-C six-member
teams and selects three using Showdown. `from_native_checkpoint` instead imports
an already reconciled detached checkpoint. `step(actions, revision)` executes a
joint native decision, including waiting sides and mid-turn replacement requests.
`save`, `restart`, and `fork` preserve native RNG, queued actions, requests and
episode limits. A decision is a request boundary, not necessarily a full turn.

The agent receives only `observation(side)`: that player's native channel log,
own request, public facts with PokeAdvice Unknown markers, and a request-derived
action mask. Never pass the environment, both players' observations, checkpoint,
scenario, seed or transport response to a policy. Those are trusted coordinator
objects. Checkpoints are privileged hidden truth, explicitly marked as such.
No opponent native request, hidden selected roster, item, unrevealed move, native
counter, set, queued action or RNG is included in a policy observation.

Contracts: `showdown-environment-v1`, `showdown-policy-observation-v1`,
`showdown-policy-actions-v1`, `showdown-environment-checkpoint-v1`.
Action indices 0–5 are current own-request switch positions; 6–9 native move
positions; 10–13 Mega; 14–17 Z; 18–21 Dynamax; 22–25 Tera (the latter three
remain masked in M-C); 26 is wait; 27–30 Mega X; 31–34 Mega Y. This retains
poke-env's first 26 action meanings, with explicit wait and dual Mega extensions.
Switch positions follow the current native request; poke-env's persistent team
dictionary order is different after switching, so its masks are not plug-in
replacements. Offline parser/mask compatibility was executed against poke-env
`7ff6212e4e738efd46f1ea52035b37a8bba1e386` (0.16.1), without a battle server.
Masks use only player-visible native requests, never probes against hidden truth.
An uncertain native trap/disable rejection refreshes the request without moving
the battle or yielding a reward; the coordinator must retry with the new revision.
Malformed, masked and stale actions fail before choices are submitted.

Minimal trusted-coordinator loop (the policy receives one observation only):

```python
from advisor.showdown_environment import ShowdownEnvironment

with ShowdownEnvironment(checkout, max_decisions=512) as env:
    env.reset(complete_hypothetical_scenario, seed=[1, 2, 3, 4])
    while True:
        views = {side: env.observation(side) for side in ("self", "opponent")}
        actions = {side: policies[side].act(view) for side, view in views.items()}
        transition = env.step(actions, revision=views["self"]["revision"])
        if transition["terminated"] or transition["truncated"]:
            break
```

Policies select an enabled integer index and retain their own recurrent state and
RNG across restart. The coordinator alone receives joint rewards/terminal outcome.
`batch_step` accepts independent environment/action/revision tuples on one shared
worker, returns a result or sanitized error for every row, and never skips successful
rows following another episode's rejection. Use independent workers for CPU parallelism.

Sparse zero-sum reward: +1 winner, −1 loser, 0 draw/nonterminal. Environment
budget exhaustion is `truncated`, not a loss/draw/native termination. Native
termination takes precedence over the decision limit. No HP shaping is enabled.
Rewards and terminal outcomes are realized seeded executions, not probabilities.

Each environment owns a bounded local worker by default. Independent instances
can run in parallel; a shared worker serializes batched requests and binds every
handle to an owner and revision. Save explicitly before process loss; restart
from the last saved checkpoint is intentional and never silently replays actions.
Engine exceptions invalidate the native handle and cached observation; a process
generation change also invalidates other shared episodes. Unrelated episodes survive
an isolated native engine exception. All handles/processes close explicitly.
The checkpoint digest detects corruption, not malicious privileged mutation.
Legacy sleep/freeze observations are imported only through the existing approved
reconciliation boundary; native counters never rewrite historical replay facts.

Initial policy training can use structured dictionaries and recurrent protocol
history; fixed tensor embeddings, curriculum, dataset priors, PPO/DQN, GPU scale,
reward shaping and production ranking are separate future work.

The initial contract begins after the coordinator's explicit three-of-six preview
selection. It has no learned preview-selection action or human wall-clock timeout.
The compact public state is a feature summary, not a complete protocol parser;
public event history and the native own request remain available. Opponent HP
fractions are displayed Champions health bars, not exact hidden HP. Native status
duration counters remain hidden even when a major status itself is public.

Reproduce bounded offline readiness without training a model:

```powershell
uv run python scripts/verify_showdown_training.py --showdown-checkout C:\path\to\pinned-showdown --episodes 32 --workers 2 --lanes 4
```

Reuse references: [pinned Pokémon Showdown](https://github.com/smogon/pokemon-showdown/tree/942cda71d14bf0618bd57991708a2e2734b6daba)
and [tested poke-env revision](https://github.com/hsahovic/poke-env/tree/7ff6212e4e738efd46f1ea52035b37a8bba1e386).
The latter's offline protocol parser worked, but its server-centric environment and
persistent team-order masks are not directly compatible with this local worker.
No additional simulation engine, RL framework or mechanics implementation was added.

The Gym adapter's `showdown-learning-info-v2` reset/step metadata contains only
public episode/revision/phase identity and realized scalar outcomes. Opponent
policy kind, both private requests, hidden sets/checkpoints and future RNG do not
cross this boundary. Ended-episode coordinator metrics may retain the configured
opponent identity for evaluation accounting; those metrics are not actor inputs.
Native coordinator transitions/checkpoints remain privileged and unchanged.
