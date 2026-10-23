"""Opt-in CPU observation of maintained PPO updates; never a policy feature.

Captures original sampler output, loss locals, gradients and Adam boundaries.
No sampler replacement, extra forward pass, loss mutation or optimizer step is
performed by the recorder. Trusted local artifacts include LOSS-ONLY labels.
"""
from contextlib import ExitStack
from copy import deepcopy
import importlib.metadata
import inspect
from pathlib import Path
import random
import numpy as np
import torch

VERSION = "foundation-exact-update-capture-v1"
BUFFER_ARRAYS = ("observations", "actions", "values", "log_probs", "advantages",
                 "returns", "action_masks", "rewards", "episode_starts")
TERMS = ("policy", "value", "entropy", "uniform_kl", "parent_kl", "auxiliary")


def clone(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, np.ndarray):
        return value.copy()
    if isinstance(value, dict):
        return {k: clone(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return type(value)(clone(v) for v in value)
    return deepcopy(value)


def rng_state():
    return {"python": random.getstate(), "numpy": clone(np.random.get_state()),
            "torch_cpu": torch.get_rng_state().clone()}


def restore_rng(state):
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch_cpu"])


def policy_state(policy):
    return {"parameters": clone(policy.state_dict()),
            "optimizer": clone(policy.optimizer.state_dict())}


def restore_policy(policy, state):
    policy.load_state_dict(state["parameters"], strict=True)
    policy.optimizer.load_state_dict(deepcopy(state["optimizer"]))
    policy.optimizer.zero_grad(set_to_none=True)


def group(name):
    return ("prediction" if "prediction_" in name else
            "critic_only" if ".critic." in name or "value_net" in name else
            "actor_only" if any(s in name for s in (".scorer.", ".context.", "action_net")) else "shared")


def atomic_torch(path, value):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    temporary = path.with_suffix(path.suffix + ".writing")
    torch.save(value, temporary)
    temporary.replace(path)


def load_capture(path):
    # Only trusted locally produced diagnostic files, never downloaded pickle.
    return torch.load(path, map_location="cpu", weights_only=False)


def compare_trees(a, b):
    """Exact recursive comparison plus maximum numeric error (not allclose)."""
    errors, maximum = [], 0.
    def visit(x, y, path):
        nonlocal maximum
        if isinstance(x, torch.Tensor):
            if not isinstance(y, torch.Tensor) or x.dtype != y.dtype or x.shape != y.shape:
                errors.append(path + ":tensor_shape_or_dtype"); return
            if not torch.equal(x, y):
                errors.append(path)
                maximum = max(maximum, float((x.double()-y.double()).abs().max()))
        elif isinstance(x, np.ndarray):
            if not isinstance(y, np.ndarray) or x.shape != y.shape or x.dtype != y.dtype:
                errors.append(path + ":array_shape_or_dtype"); return
            if not np.array_equal(x, y):
                errors.append(path)
                maximum = max(maximum, float(np.max(np.abs(x.astype(float)-y.astype(float)))))
        elif isinstance(x, dict):
            if not isinstance(y, dict) or x.keys() != y.keys():
                errors.append(path + ":keys"); return
            for key in x: visit(x[key], y[key], path + "/" + str(key))
        elif isinstance(x, (list, tuple)):
            if type(x) is not type(y) or len(x) != len(y):
                errors.append(path + ":sequence"); return
            for i, (u, v) in enumerate(zip(x, y)): visit(u, v, path + "/" + str(i))
        elif x != y:
            errors.append(path)
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                maximum = max(maximum, abs(x-y))
    visit(a, b, "root")
    return {"exact": not errors, "mismatched_leaves": len(errors),
            "max_absolute_numeric_error": maximum, "first_mismatches": errors[:12]}


def restore_training(model, saved):
    if saved["schema_version"] != VERSION:
        raise ValueError("unknown_exact_update_capture")
    restore_policy(model.policy, saved["before"])
    for key, value in saved["model_attributes"].items():
        setattr(model, key, clone(value))
    for key, value in saved["buffer"].items():
        setattr(model.rollout_buffer, key, clone(value))
    model._auxiliary_observations = clone(saved["auxiliary_observations"])
    model._auxiliary_rows = clone(saved["loss_only_auxiliary_labels"])
    model._aux_groups = clone(saved["aux_groups"])
    # Last rollout's proposal weights may be stale but are explicitly restored.
    model._aux_weights = clone(saved["aux_weights"])
    restore_rng(saved["rng"])


class ExactUpdateCapture:
    """Instance-local, removable read-only hooks around ONE upstream train()."""
    def __init__(self, model, directory, *, expected_transitions=512):
        if importlib.metadata.version("sb3-contrib") != "2.7.1":
            raise ValueError("unsupported_upstream_exact_capture")
        if model.device.type != "cpu" or torch.get_num_threads() != 1:
            raise ValueError("exact_capture_requires_cpu_one_thread")
        if model.n_steps * model.n_envs != expected_transitions or expected_transitions > 512:
            raise ValueError("exact_capture_single_rollout_cap")
        self.model, self.directory = model, Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.current = None
        self.steps = 0
        self.training_calls = 0
        self.stack = ExitStack()

    def replace(self, owner, name, wrapper):
        previous = owner.__dict__.get(name)
        had = name in owner.__dict__
        original = getattr(owner, name)
        setattr(owner, name, wrapper(original))
        def restore():
            if had: setattr(owner, name, previous)
            else: delattr(owner, name)
        self.stack.callback(restore)

    def __enter__(self):
        model, policy = self.model, self.model.policy
        def train(original):
            def observed():
                self.training_calls += 1
                if self.training_calls != 1:
                    raise ValueError("exact_capture_forbids_second_rollout_update")
                buffer = model.rollout_buffer
                saved = {"schema_version": VERSION, "before": policy_state(policy), "rng": rng_state(),
                    "model_attributes": {k: clone(getattr(model,k)) for k in
                        ("num_timesteps", "_current_progress_remaining", "_n_updates")},
                    "buffer": {k: clone(getattr(buffer,k)) for k in
                        (*BUFFER_ARRAYS, "pos", "full", "generator_ready")},
                    "auxiliary_observations": clone(model._auxiliary_observations),
                    "loss_only_auxiliary_labels": clone(model._auxiliary_rows),
                    "aux_groups": clone(getattr(model,"_aux_groups",None)),
                    "aux_weights": clone(getattr(model,"_aux_weights",None)),
                    "coefficients": {"entropy":model.ent_coef,"value":model.vf_coef,
                        "uniform_kl":model.zero_avoiding_beta,
                        "parent_kl":model.parent_policy_anchor["coefficient"],
                        "auxiliary":model.auxiliary_metadata()["coefficient"]},
                    "layout": "time_major_buffer; minibatch_indices_use_SB3_env_major_swap_and_flatten",
                    "private_label_boundary": "loss_only_never_actor_critic_input"}
                atomic_torch(self.directory/"training.pt", saved)
                result = original()
                atomic_torch(self.directory/"after.pt", policy_state(policy))
                return result
            return observed
        self.replace(model, "train", train)

        def sample(original):
            def observed(indices, *args, **kwargs):
                if self.current is not None:
                    raise ValueError("unsettled_minibatch_or_early_KL_stop")
                self.current = {"index":self.steps,"minibatch_indices":clone(indices),
                                "rng_before_forward":rng_state(),"gradient_before_clip":{}}
                return original(indices,*args,**kwargs)
            return observed
        self.replace(model.rollout_buffer, "_get_samples", sample)

        def aux_indices(original):
            def observed(n):
                result = original(n)
                self.current["auxiliary_indices"] = clone(result)
                self.current["auxiliary_weights"] = clone(model._aux_weights)
                return result
            return observed
        self.replace(model, "_auxiliary_indices", aux_indices)

        def supervised(original):
            def observed(*args,**kwargs):
                result=original(*args,**kwargs)
                self.current["auxiliary_loss"] = clone(result[0])
                return result
            return observed
        self.replace(model, "_supervised_loss", supervised)

        def evaluate(original):
            def observed(*args,**kwargs):
                result=original(*args,**kwargs)
                dist=policy.action_dist.distribution
                self.current["raw_evaluate"] = clone({"value":result[0],"logp":result[1],
                    "entropy":result[2],"probabilities":dist.probs,"masked_logits":dist.logits})
                return result
            return observed
        self.replace(policy, "evaluate_actions", evaluate)

        def logits(_module,_inputs,value):
            if self.current is not None:self.current["raw_logits"]=clone(value)
        self.stack.callback(policy.action_net.register_forward_hook(logits).remove)
        for name, parameter in policy.named_parameters():
            def capture(gradient, name=name):
                if self.current is None:raise ValueError("gradient_outside_original_minibatch")
                if not torch.isfinite(gradient).all():raise ValueError("nonfinite_captured_gradient")
                target=self.current["gradient_before_clip"]
                target[name]=clone(gradient) if name not in target else target[name]+clone(gradient)
                return gradient
            self.stack.callback(parameter.register_hook(capture).remove)

        def pre_step(_optimizer,_args,_kwargs):
            frame=inspect.currentframe()
            try:
                while frame is not None and not (frame.f_code.co_name=="train" and
                        frame.f_globals.get("__name__")=="sb3_contrib.ppo_mask.ppo_mask"):
                    frame=frame.f_back
                if frame is None:raise ValueError("optimizer_not_in_pinned_upstream_train")
                values=frame.f_locals
                self.current["upstream"]={k:clone(values[k]) for k in
                    ("loss","policy_loss","value_loss","entropy_loss","advantages","approx_kl_div","epoch")}
            finally:del frame
            self.current["before"]=policy_state(policy)
            self.current["rng_before_step"]=rng_state()
            self.current["gradient_after_clip"]={n:clone(p.grad) for n,p in policy.named_parameters() if p.grad is not None}
        def post_step(_optimizer,_args,_kwargs):
            self.current["after"]=policy_state(policy)
            atomic_torch(self.directory/f"step_{self.steps:02d}.pt",self.current)
            self.steps+=1;self.current=None
        self.stack.callback(policy.optimizer.register_step_pre_hook(pre_step).remove)
        self.stack.callback(policy.optimizer.register_step_post_hook(post_step).remove)
        return self

    def __exit__(self,*exc):
        self.stack.close()
        # Early KL stopping can leave a final sampled but unoptimized minibatch.
        if self.current is not None and exc[0] is None:
            atomic_torch(self.directory/"not_optimized_minibatch.pt",self.current)
        return False


def minibatch(saved, step):
    from sb3_contrib.common.maskable.buffers import MaskableRolloutBufferSamples
    def gather(name):
        a=saved["buffer"][name]
        # Exactly SB3's swap_and_flatten, preserving original float32 transport.
        if len(a.shape)<3:a=a.reshape((*a.shape,1))
        a=a.swapaxes(0,1).reshape((-1,*a.shape[2:]))
        return torch.as_tensor(a[step["minibatch_indices"]])
    return MaskableRolloutBufferSamples(gather("observations"),gather("actions"),gather("values").flatten(),
        gather("log_probs").flatten(),gather("advantages").flatten(),gather("returns").flatten(),gather("action_masks"))


def loss_terms(model, saved, step):
    """Offline diagnostic recomposition, gated against captured upstream loss/grad.

    This is NOT a replacement training algorithm. Entropy-seam arithmetic order
    intentionally mirrors Parent -> auxiliary -> uniform -> upstream mean.
    """
    from advisor.learned_regularized_ppo import legal_uniform_kl
    from advisor.learned_parent_anchor import parent_policy_kl
    b=minibatch(saved,step);policy=model.policy
    values,logp,entropy=policy.evaluate_actions(b.observations,b.actions.long().flatten(),action_masks=b.action_masks)
    dist=policy.action_dist.distribution
    with torch.no_grad():
        ref=model.prepare_parent_reference().model.policy.get_distribution(b.observations,action_masks=b.action_masks).distribution
    pk=parent_policy_kl(ref.probs,ref.logits,dist.logits,b.action_masks)
    uk=legal_uniform_kl(dist.logits,b.action_masks)
    ids=step["auxiliary_indices"]
    model._aux_weights=clone(step["auxiliary_weights"])
    model.foundation_timings={"auxiliary_forward_seconds":0.}
    aux,_=model._supervised_loss(torch.as_tensor(saved["auxiliary_observations"][ids]),
                               [saved["loss_only_auxiliary_labels"][i] for i in ids])
    advantage=b.advantages
    if model.normalize_advantage:advantage=(advantage-advantage.mean())/(advantage.std()+1e-8)
    ratio=(logp-b.old_log_prob).exp();clip=model.clip_range(model._current_progress_remaining)
    pg=-torch.min(advantage*ratio,advantage*torch.clamp(ratio,1-clip,1+clip)).mean()
    vf=values.flatten()
    if model.clip_range_vf is not None:
        width=model.clip_range_vf(model._current_progress_remaining)
        vf=b.old_values+torch.clamp(vf-b.old_values,-width,width)
    vl=torch.nn.functional.mse_loss(b.returns,vf)
    c=saved["coefficients"]
    terms={"policy":pg,"value":c["value"]*vl,"entropy":-c["entropy"]*entropy.mean(),
           "uniform_kl":c["uniform_kl"]*uk.mean(),"parent_kl":c["parent_kl"]*pk.mean(),
           "auxiliary":c["auxiliary"]*aux}
    def combine(omit=None):
        # Completely disconnected omitted terms, NOT zero gradients that would
        # still advance Adam's stale momentum in otherwise unused parameters.
        e=entropy
        if omit!="parent_kl":e=e-(c["parent_kl"]/c["entropy"])*pk
        if omit!="auxiliary":e=e-(c["auxiliary"]/c["entropy"])*aux
        if omit!="uniform_kl":e=e-(c["uniform_kl"]/c["entropy"])*uk
        if omit=="entropy":e=e-entropy
        actor=pg if omit!="policy" else None
        rest=-c["entropy"]*e.mean()
        if actor is not None:rest=actor+rest
        if omit!="value":rest=rest+c["value"]*vl
        return rest
    return terms,combine,{"value":values,"logp":logp,"probabilities":dist.probs,"masked_logits":dist.logits,
                          "normalized_advantages":advantage}
