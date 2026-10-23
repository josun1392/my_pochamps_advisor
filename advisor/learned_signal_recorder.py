"""Optional bounded public snapshots and scalar PPO joins, never policy inputs."""
import gzip
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4
import numpy as np

from advisor.learned_execution_alignment import durable_json

VERSION = "showdown-public-rollout-scalar-joins-v1"


class PublicSignalRecorder:
    def __init__(self, directory, encoder):
        self.directory = Path(directory)
        self.encoder = encoder
        self.directory.mkdir(parents=True, exist_ok=True)
        self.pending = None
        self.infos = []

    def settled(self, clock, model=None):
        if self.pending is not None:
            name, before = self.pending
            groups = {}
            if model is not None:
                for key, parameter in model.policy.named_parameters():
                    group = ("prediction" if "prediction_" in key else "critic_only" if ".critic." in key or "value_net" in key
                             else "actor_only" if any(s in key for s in (".scorer.", ".context.", "action_net")) else "shared")
                    if parameter.grad is not None:
                        groups[group] = groups.get(group, 0.) + float(parameter.grad.detach().square().sum())
            durable_json(self.directory / (name + ".settled.json"), {
                "rollout": name, "Adam_before": before, "Adam_after": clock,
                "optimizer_advanced": clock > before,
                "last_minibatch_clipped_parameter_group_gradient_norms": {k:v**.5 for k,v in groups.items()},
                "gradient_scope": "combined_loss_parameter_groups_not_causal_PPO_vs_auxiliary_loss_decomposition",
                "scope": "whole_rollout_update_boundary_not_action_optimality"})
            self.pending = None

    def start(self, model, clock):
        self.settled(clock, model)
        self.infos = []
        # Four views every fourth rollout, hard bounded to 128 across restarts.
        count = len(list(self.directory.glob("public_*.json")))
        if count < 128 and (model.num_timesteps // (model.n_steps * model.n_envs)) % 4 == 0:
            for view in model.get_env().get_attr("current")[:128-count]:
                # Encoder's public-key validation is authoritative; do not copy
                # coordinator infos/labels or a simulator checkpoint.
                self.encoder.encode(view)
                durable_json(self.directory / ("public_" + uuid4().hex + ".json"), {
                    "schema_version": VERSION, "model_timesteps": model.num_timesteps,
                    "scope": "current_own_player_visible_view_only", "observation": view})

    def step(self, infos, dones):
        self.infos.append([{"episode_id_after_step": i.get("episode_id"),
            "revision_after_step": i.get("revision"), "done": bool(done),
            "truncated": bool(i.get("TimeLimit.truncated", False))}
            for i, done in zip(infos, dones)])

    def end(self, model, clock):
        buffer = model.rollout_buffer
        if len(self.infos) != model.n_steps or any(len(i) != model.n_envs for i in self.infos):
            raise ValueError("public_signal_rollout_join_shape")
        name = "rollout_" + str(model.num_timesteps) + "_" + uuid4().hex
        path = self.directory / (name + ".jsonl.gz")
        temporary = path.with_suffix(path.suffix + ".writing")
        with gzip.open(temporary, "xt", encoding="utf-8") as stream:
            for t in range(model.n_steps):
                for env in range(model.n_envs):
                    mask = buffer.action_masks[t, env].astype(bool)
                    action = int(buffer.actions[t, env, 0])
                    if not mask[action]:
                        raise ValueError("public_signal_masked_action")
                    row = {"schema_version": VERSION, "t": t, "env": env,
                        "model_timesteps_end": model.num_timesteps, "Adam_before": clock,
                        "observation_sha256": sha256(buffer.observations[t, env].tobytes()).hexdigest(),
                        "legal_mask_bits": sum(int(v) << k for k, v in enumerate(mask)),
                        "action": action, "old_logp": float(buffer.log_probs[t, env]),
                        "value": float(buffer.values[t, env]), "reward": float(buffer.rewards[t, env]),
                        "return": float(buffer.returns[t, env]), "advantage": float(buffer.advantages[t, env]),
                        "episode_start": bool(buffer.episode_starts[t, env]),
                        "scope": "pre_update_GAE_labels_not_optimal_actions_or_exact_replay",
                        **self.infos[t][env]}
                    stream.write(json.dumps(row, allow_nan=False) + "\n")
        temporary.replace(path)
        self.pending = (name, clock)
