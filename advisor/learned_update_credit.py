"""Read-only instrumentation of maintained PPO updates on captured public states.

No loss, gradient, minibatch order, policy architecture or optimizer replacement.
GAE, normalized minibatch advantage and fixed-policy counterfactual returns have
different estimands. Their observed signs are not optimal-action labels.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import torch

from advisor.learned_decision_snapshots import write_new, outside_git
from advisor.learned_parent_anchor import optimizer_clock, optimizer_digest, tensor_digest
from advisor.learned_tactical_diagnostics import action_class
from scripts.train_showdown_autonomous import BudgetCallback

VERSION = "foundation-PPO-update-credit-native-v1"


def score_public(policy, features, mask):
    """Deterministic forward, preserving mode/RNG; the actor sees features only."""
    mask = np.asarray(mask, bool)
    if mask.shape != (35,) or not mask.any(): raise ValueError("credit_native_mask")
    raw = []; was_training = policy.training
    hook = policy.action_net.register_forward_pre_hook(lambda _, a: raw.append(a[0].detach().cpu().numpy().copy()))
    try:
        policy.set_training_mode(False)
        with torch.no_grad():
            _, value, _ = policy(torch.as_tensor(features)[None], action_masks=mask[None], deterministic=True)
            dist = policy.action_dist.distribution
            p = dist.probs[0].cpu().numpy().copy(); logp = dist.logits[0].cpu().numpy().copy()
        if len(raw) != 1 or not np.isfinite(raw[0]).all() or not np.isfinite(logp).all() or np.any(p[~mask] != 0):
            raise ValueError("credit_invalid_distribution")
        return {"raw_logits": raw[0][0].tolist(), "probabilities": p.tolist(),
                "log_probabilities": logp.tolist(), "value": float(value.item()), "argmax": int(p.argmax())}
    finally:
        hook.remove(); policy.set_training_mode(was_training)


def choose_alternative(public, sampled, probabilities):
    """Fixed before outcomes: pre-update argmax, else best other legal family."""
    legal = [i for i, m in enumerate(public["action_mask"]) if m]
    if sampled not in legal or len(legal) < 2: raise ValueError("credit_alternative_unavailable")
    best = max(legal, key=lambda a: (probabilities[a], -a))
    if best != sampled: return best
    family = action_class(public, sampled)
    other = [a for a in legal if a != sampled]
    different = [a for a in other if action_class(public, a) != family]
    return max(different or other, key=lambda a: (probabilities[a], -a))


def normalized_advantage(advantages, position, normalize):
    a = advantages.detach()
    if normalize: a = (a - a.mean()) / (a.std() + 1e-8)
    return float(a[position].item())


class UpdateCreditObserver:
    def __init__(self, directory, encoder, snapshots, parent_model_id):
        self.directory = outside_git(directory); self.directory.mkdir(exist_ok=False)
        for name in ("policies", "updates", "credits"): (self.directory / name).mkdir()
        self.encoder, self.snapshots, self.parent_model_id = encoder, snapshots, parent_model_id
        self.pending = None; self.before = None; self.original_samples = None; self.step_handle = None

    def start(self, model, update):
        if self.pending is not None: raise ValueError("credit_unsettled_update")
        state = {k: v.detach().cpu().clone() for k, v in model.policy.state_dict().items()}
        path = self.directory / "policies" / f"update_{update:03d}_before.pt"
        with path.open("xb") as f: torch.save(state, f)
        self.before = {"update": update, "parameters_SHA256": tensor_digest(state),
            "policy_state_file": str(path), "policy_state_file_SHA256": sha256(path.read_bytes()).hexdigest(),
            "Adam_clock": optimizer_clock(model.policy), "Adam_SHA256": optimizer_digest(model.policy)}
        self.before_state = state
        self.snapshots.policy_id = self.before["parameters_SHA256"]
        write_new(self.directory / "updates" / f"update_{update:03d}_before.json", self.before)

    def prepare(self, env, *, step, t):
        update = self.before["update"]
        if t < (0, 32, 64, 96)[update % 4]: return
        self.snapshots.prepare(env, step=step, rollout=update, t=t)
        root = self.snapshots.prepared
        if root is not None:
            root.update(parent_model_SHA256=self.parent_model_id, policy_id_kind="policy_parameter_SHA256",
                        behavior_update=update, policy_state_file=self.before["policy_state_file"],
                        policy_state_file_SHA256=self.before["policy_state_file_SHA256"],
                        Adam_at_collection=self.before["Adam_clock"])
            root["training_episode_identity"] = deepcopy(env._episode_identity)

    def before_update(self, model):
        if (tensor_digest(model.policy.state_dict()) != self.before["parameters_SHA256"]
                or optimizer_digest(model.policy) != self.before["Adam_SHA256"]):
            raise ValueError("credit_policy_or_Adam_changed_during_collection")
        update = self.before["update"]
        roots = [r for r in self.snapshots.roots if r["rollout"] == update]
        for r in roots:
            public = json.loads((self.snapshots.directory / "public" / (r["id"] + ".json")).read_text())["observation"]
            features = self.encoder.encode(public)
            if sha256(features.tobytes()).hexdigest() != r["observation_sha256"]: raise ValueError("credit_public_SHA")
            pre = score_public(model.policy, features, r["action_mask"])
            if abs(pre["value"]-r["value"]) > 2e-5 or abs(pre["log_probabilities"][r["action"]]-r["old_logp"]) > 2e-5:
                raise ValueError("credit_preupdate_value_or_logp")
            r["alternative_action"] = choose_alternative(public, r["action"], pre["probabilities"])
            r["family"] = action_class(public, r["action"])
            r["alternative_family"] = action_class(public, r["alternative_action"])
            r["pre_update_scores"] = pre
        self.pending = {**self.before, "roots": roots, "minibatches": []}
        b = model.rollout_buffer
        if "_get_samples" in b.__dict__: raise ValueError("credit_nested_sample_observer")
        original = b._get_samples; self.original_samples = b

        def samples(indices, *a, **kw):
            batch = original(indices, *a, **kw)
            event = {"index": len(self.pending["minibatches"]), "indices": np.asarray(indices).tolist(),
                     "Adam_before": optimizer_clock(model.policy), "optimizer_applied": False, "roots": []}
            for r in roots:
                # SB3 swaps time-major to env-major: env0 flat index is t.
                positions = np.flatnonzero(np.asarray(indices) == r["t"])
                for j in positions:
                    if (sha256(batch.observations[j].detach().cpu().numpy().tobytes()).hexdigest() != r["observation_sha256"]
                            or int(batch.actions[j].item()) != r["action"]
                            or abs(float(batch.advantages[j].item())-r["advantage"]) > 1e-7):
                        raise ValueError("credit_minibatch_row_binding")
                    event["roots"].append({"id": r["id"], "position": int(j), "raw_GAE": r["advantage"],
                        "normalized_advantage": normalized_advantage(batch.advantages, int(j), model.normalize_advantage)})
            self.pending["minibatches"].append(event)
            return batch  # Original tensors and autograd graph, unchanged.

        b._get_samples = samples
        def stepped(*_):
            event = self.pending["minibatches"][-1]
            event.update(optimizer_applied=True, Adam_after=optimizer_clock(model.policy))
        self.step_handle = model.policy.optimizer.register_step_post_hook(stepped)

    def cleanup(self):
        if self.original_samples is not None:
            del self.original_samples._get_samples; self.original_samples = None
        if self.step_handle is not None:
            self.step_handle.remove(); self.step_handle = None

    def settle(self, model):
        if self.pending is None: return
        self.cleanup(); p = self.pending
        after_clock = optimizer_clock(model.policy)
        if after_clock <= p["Adam_clock"]: raise ValueError("credit_no_actual_optimizer_update")
        state = model.policy.state_dict(); after_digest = tensor_digest(state)
        update = p["update"]; credits = []
        for r in p["roots"]:
            public = json.loads((self.snapshots.directory / "public" / (r["id"] + ".json")).read_text())["observation"]
            features = self.encoder.encode(public)
            if sha256(features.tobytes()).hexdigest() != r["observation_sha256"]: raise ValueError("credit_postupdate_public_SHA")
            post = score_public(model.policy, features, r["action_mask"]); pre = r["pre_update_scores"]
            a, alt = r["action"], r["alternative_action"]
            appearances = [dict(e, minibatch=m["index"], Adam_before=m["Adam_before"],
                Adam_after=m.get("Adam_after"), optimizer_applied=m["optimizer_applied"])
                for m in p["minibatches"] for e in m["roots"] if e["id"] == r["id"]]
            credit = {"schema_version": VERSION, "root": r["id"], "update": update,
                "observation_SHA256": r["observation_sha256"], "action_mask": r["action_mask"],
                "sampled_action": a, "alternative_action": alt, "family": r["family"],
                "alternative_family": r["alternative_family"], "GAE": r["advantage"],
                "pre": pre, "post": post, "policy_before_SHA256": p["parameters_SHA256"],
                "policy_after_SHA256": after_digest, "Adam_before": p["Adam_clock"], "Adam_after": after_clock,
                "selected_logp_delta": post["log_probabilities"][a]-pre["log_probabilities"][a],
                "selected_probability_delta": post["probabilities"][a]-pre["probabilities"][a],
                "sampled_vs_alternative_logit_gap_delta": (post["raw_logits"][a]-post["raw_logits"][alt])-(pre["raw_logits"][a]-pre["raw_logits"][alt]),
                "minibatch_appearances": appearances,
                "selected_row_optimizer_applications": sum(e["optimizer_applied"] for e in appearances),
                "unconsumed_row_scope": None if appearances else "upstream_early_stop_no_forced_resampling",
                "scope": "actual_combined_PPO_update_not_single_row_or_GAE_causal_attribution"}
            write_new(self.directory / "credits" / (r["id"] + ".json"), credit); credits.append(r["id"])
        deltas = {}
        for k, v in model.policy.named_parameters():
            group = "prediction" if "prediction_" in k else "critic" if ".critic." in k or "value_net" in k else "actor" if ".scorer." in k or ".context." in k else "shared"
            deltas[group] = deltas.get(group, 0.) + float((v.detach().cpu()-self.before_state[k]).double().square().sum())
        write_new(self.directory / "updates" / f"update_{update:03d}_after.json", {
            "schema_version": VERSION, "update": update, "before": {k:v for k,v in p.items() if k not in ("roots", "minibatches")},
            "after_parameters_SHA256": after_digest, "Adam_after": after_clock,
            "Adam_after_SHA256": optimizer_digest(model.policy), "credited_roots": credits,
            "parameter_delta_L2": {k: v**.5 for k,v in deltas.items()}, "minibatches": p["minibatches"],
            "training_metrics": {k:float(v) for k,v in model.logger.name_to_value.items()
                if (k.startswith("train/") or k.startswith("foundation/")) and isinstance(v, (int, float, np.number))}})
        self.pending = None


class UpdateCreditCallback(BudgetCallback):
    """Env0 snapshot, all four environments' original PPO/auxiliary handling."""
    def __init__(self, budget, native_env, observer, *, signal_recorder, transition_cap, progress=None):
        super().__init__(budget, signal_recorder=signal_recorder)
        self.native_env, self.observer = native_env, observer
        self.steps, self.rollout, self.cap, self.credit_progress = 0, -1, transition_cap, progress

    def _on_rollout_start(self):
        super()._on_rollout_start(); self.observer.settle(self.model)
        if self.steps >= self.cap: raise ValueError("credit_transition_cap")
        self.rollout += 1; self.observer.start(self.model, self.rollout)
        self.observer.prepare(self.native_env, step=self.steps // 4, t=0)

    def _on_step(self):
        if self.locals["env"].num_envs != 4: raise ValueError("credit_original_four_env_contract")
        self.observer.snapshots.selected(action=int(self.locals["actions"][0]),
            value=float(self.locals["values"][0].item()), logp=float(self.locals["log_probs"][0].item()),
            features=self.model._last_obs[0], mask=self.locals["action_masks"][0])
        self.steps += 4
        if self.steps > self.cap: raise ValueError("credit_transition_cap")
        result = super()._on_step()
        if result and self.locals["n_steps"] + 1 < self.model.n_steps:
            self.observer.prepare(self.native_env, step=self.steps // 4, t=self.locals["n_steps"] + 1)
        return result

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.observer.snapshots.join(self.model.rollout_buffer, self.rollout)
        self.observer.before_update(self.model)

    def _on_training_end(self):
        super()._on_training_end(); self.observer.settle(self.model)
