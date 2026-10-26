"""Replay-only conditional policy signals, not rewards, labels or new PPO."""
from hashlib import sha256
import json
import numpy as np
import torch

from advisor.learned_action_signals import require_public_equivalence, public_identity
from advisor.learned_update_credit import score_public

VERSION = "foundation-policy-matched-counterfactual-v1"


class HistoricalSampler:
    """The captured actor/critic, T=1, with a local inference-only RNG stream."""
    def __init__(self, encoder, policy, seed):
        self.encoder, self.policy = encoder, policy
        self.generator = torch.Generator(device="cpu").manual_seed(seed)

    def scores(self, public):
        # No native handle, checkpoint, future seed or opponent view enters here.
        return score_public(self.policy, self.encoder.encode(public), public["action_mask"])

    def decision(self, public):
        scores = self.scores(public)
        p = torch.tensor(scores["probabilities"], dtype=torch.float32)
        action = int(torch.multinomial(p, 1, generator=self.generator).item())
        if not public["action_mask"][action]:
            raise ValueError("policy_matched_sample_not_native_legal")
        return action, scores


def return_signals(rows, *, gamma, gae_lambda, horizon):
    """Same Gym-step reward/time-limit bootstrap and finite-rollout GAE rules."""
    if not rows or gamma != 1. or gae_lambda != .95 or not 1 <= horizon <= 128:
        raise ValueError("policy_matched_return_contract")
    if not (rows[-1]["terminated"] or rows[-1]["truncated"]):
        raise ValueError("unfinished_branch_has_no_full_return")
    total = 0.
    for i, r in enumerate(rows):
        if (r["terminated"] and r["truncated"]) or not np.isfinite(
            [r["reward"], r["value"], r["next_value"]]).all():
            raise ValueError("invalid_policy_matched_return_row")
        if i + 1 < len(rows) and (r["terminated"] or r["truncated"]):
            raise ValueError("branch_crossed_episode_boundary")
        total += gamma**i * r["reward"]
    if rows[-1]["truncated"]:
        total += gamma**len(rows) * rows[-1]["next_value"]
    selected = rows[:horizon]
    carry = 0.
    for r in reversed(selected):
        done = r["terminated"] or r["truncated"]
        # SB3 first adds gamma*terminal_value to timeout reward, then cuts GAE.
        reward = r["reward"] + (gamma*r["next_value"] if r["truncated"] else 0.)
        delta = reward + (0. if done else gamma*r["next_value"]) - r["value"]
        carry = delta + (0. if done else gamma*gae_lambda*carry)
    return {"full_return": total, "finite_lambda_return": selected[0]["value"]+carry,
            "finite_critic_advantage": carry, "lambda_steps": len(selected),
            "bootstrap_kind": "public_critic_time_limit" if rows[-1]["truncated"] else "native_terminal"}


def policy_matched_branch(native, checkpoint, reference, *, actor, opponent,
                          forced_action, future_seed, horizon, stopping=None):
    """Two conditions differ only in first own action; future policies match.

    Opponent is the exact frozen historical learned policy, using its OWN view.
    Actor consumes the same first local categorical draw even in the forced arm,
    so subsequent sampling draws are aligned by owner Gym-decision index.
    """
    native.restart(checkpoint, future_seed=future_seed)
    require_public_equivalence(reference, native.observation("self", include_history=True))
    rows, trace, rejection_count, consecutive, native_steps = [], [], 0, 0, 0
    first_policy_action = None
    for t in range(4096):
        if stopping and stopping():
            raise TimeoutError("policy_matched_STOP_or_deadline")
        view = native.observation("self", include_history=True)
        sampled, before = actor.decision(view)
        if t == 0:
            first_policy_action = sampled
        action = forced_action if t == 0 and forced_action is not None else sampled
        if type(action) is not int or not 0 <= action < 35 or not view["action_mask"][action]:
            raise ValueError("policy_matched_forced_action_illegal")
        root_action = action
        while True:
            own = native.observation("self", include_history=True)
            rival = native.observation("opponent", include_history=True)
            other = int(opponent.act(rival))  # Never the learner view/private truth.
            if not own["action_mask"][action] or not rival["action_mask"][other]:
                raise ValueError("policy_matched_native_mask_violation")
            result = native.step({"self": action, "opponent": other}, revision=own["revision"])
            native_steps += 1
            rejected = bool(result["action_rejected"])
            rejection_count += rejected
            consecutive = consecutive + 1 if rejected else 0
            after = native.observation("self", include_history=True)
            trace.append({"native_step": native_steps, "gym_t": t,
                "own_public_SHA256": public_identity(own), "opponent_public_SHA256": public_identity(rival),
                "self_action": action, "opponent_action": other,
                "native_choices": {"self": own["choices"][action], "opponent": rival["choices"][other]},
                "rejected": rejected, "reward": result["rewards"]["self"],
                "terminated": result["terminated"], "truncated": result["truncated"]})
            if t == 0 and rejected:
                raise ValueError("forced_root_request_rejected_no_counterfactual_label")
            if consecutive >= 8:
                raise ValueError("policy_matched_unresolved_rejection_guard")
            done = result["terminated"] or result["truncated"]
            if done or not after["action_mask"][26]:
                break
            action = 26  # Preserve maintained Gym automatic wait, no actor draw.
        if result["terminated"]:
            next_value = 0.
        elif result["truncated"]:
            next_value = actor.scores(native.timeout_bootstrap_observation("self"))["value"]
        else:
            next_value = actor.scores(after)["value"]
        rows.append({"action": root_action, "value": before["value"], "next_value": next_value,
            "reward": result["rewards"]["self"], "terminated": result["terminated"],
            "truncated": result["truncated"]})
        if done:
            if rejection_count > .01*max(128, native_steps):
                raise ValueError("policy_matched_retry_rate_guard")
            return {"schema_version": VERSION, "first_policy_action": first_policy_action,
                "first_executed_action": rows[0]["action"], "gym_decisions": len(rows),
                "native_decisions": native_steps, "terminated": result["terminated"],
                "truncated": result["truncated"], "winner": result["winner"],
                "native_rejections": rejection_count,
                **return_signals(rows, gamma=1., gae_lambda=.95, horizon=horizon),
                "rows": rows, "trace": trace,
                "final_public_SHA256": public_identity(after),
                "final_native_digest": native.save()["digest"],
                "interpretation": "conditional_policy_return_not_PPO_observed_reward_or_optimal_label"}
    raise ValueError("policy_matched_branch_did_not_close")


def paired_summary(pairs, *, root_order, bootstrap_seed=2026102601, resamples=20000):
    """Roots are clusters; stochastic repeats stay nested inside each root."""
    root_rows = []
    for root in root_order:
        ps = [p for p in pairs if p["root"] == root]
        if not ps:
            raise ValueError("missing_policy_matched_root")
        f = np.array([p["forced"]["full_return"] for p in ps])
        b = np.array([p["baseline"]["full_return"] for p in ps])
        lf = np.array([p["forced"]["finite_lambda_return"] for p in ps])
        lb = np.array([p["baseline"]["finite_lambda_return"] for p in ps])
        d = f-b
        root_rows.append({"root": root, "pairs": len(ps), "forced_Q": float(f.mean()),
            "policy_V": float(b.mean()), "policy_relative_advantage": float(d.mean()),
            "pair_advantages": d.tolist(), "critic_value": ps[0]["critic_value"],
            "collected_GAE": ps[0]["GAE"],
            "forced_Q_minus_critic": float(f.mean()-ps[0]["critic_value"]),
            "forced_lambda_minus_critic": float(lf.mean()-ps[0]["critic_value"]),
            "policy_lambda_minus_critic": float(lb.mean()-ps[0]["critic_value"]),
            "paired_lambda_advantage": float((lf-lb).mean()),
            "nonzero_pair_count": int(np.count_nonzero(abs(d)>1e-8)),
            "baseline_first_differs": sum(p["forced"]["first_executed_action"] !=
                p["baseline"]["first_executed_action"] for p in ps)})
    x = np.array([r["collected_GAE"] for r in root_rows])
    y = np.array([r["policy_relative_advantage"] for r in root_rows])
    rng = np.random.default_rng(bootstrap_seed)
    idx = rng.integers(0, len(y), size=(resamples, len(y)))
    boot = y[idx].mean(1)
    corr = None
    corr_ci = None
    degenerate = resamples
    if len(y) > 2 and x.std() > 0 and y.std() > 0:
        corr = float(np.corrcoef(x, y)[0, 1])
        bx, by = x[idx], y[idx]
        valid = (bx.std(1)>1e-12)&(by.std(1)>1e-12)
        degenerate = int((~valid).sum())
        if degenerate == 0:
            bx=bx-bx.mean(1,keepdims=True);by=by-by.mean(1,keepdims=True)
            values=(bx*by).sum(1)/np.sqrt((bx**2).sum(1)*(by**2).sum(1))
            corr_ci=np.quantile(values,[.025,.975]).tolist()
    return {"root_rows": root_rows, "root_clusters": len(y), "paired_samples": len(pairs),
        "mean_policy_relative_advantage": float(y.mean()),
        "root_cluster_95CI": np.quantile(boot,[.025,.975]).tolist(),
        "GAE_advantage_correlation": corr, "correlation_95CI": corr_ci,
        "undefined_correlation_bootstrap_draws": degenerate,
        "nonzero_roots": sum(r["nonzero_pair_count"]>0 for r in root_rows),
        "nonzero_mean_roots": int(np.count_nonzero(abs(y)>1e-8)),
        "bootstrap_scope": "root cluster case uncertainty conditional on one behavior-training run"}
