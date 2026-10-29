"""Typed reward-contract persistence around unchanged Foundation PPO/GAE."""
import gzip
import json
from pathlib import Path

import numpy as np
import torch

from advisor.learned_combat_foundation import FoundationCombatPPO
from advisor.learned_execution_alignment import digest, durable_json
from advisor.learned_ppo_contract_audit import AuditedSignalRecorder
from advisor.learned_public_potential import potential_contract, validate_contract, PARENT_SHA

RECORDER_VERSION = "foundation-public-potential-rollout-audit-v1"


def validate_model(model):
    marker = getattr(model, "public_potential_reward", None)
    if marker is None and type(model) is not PotentialFoundationPPO:
        return
    validate_contract(marker)
    if (type(model) is not PotentialFoundationPPO or model.gamma != 1. or model.gae_lambda != .95
            or model.rollout_buffer.gamma != 1. or model.rollout_buffer.gae_lambda != .95
            or any(getattr(model, k, None) is not None for k in (
                "gae_lambda_experiment", "parent_policy_anchor", "masked_temperature", "move_slot_consistency"))):
        raise ValueError("public_potential_algorithm_or_objective_mismatch")


class PotentialFoundationPPO(FoundationCombatPPO):
    def __init__(self, *args, public_potential_reward=None, **kwargs):
        self.public_potential_reward = (validate_contract(public_potential_reward)
            if public_potential_reward is not None else None)
        self.public_potential_trained = 0
        super().__init__(*args, **kwargs)

    def collect_rollouts(self, env, *args, **kwargs):
        validate_model(self)
        actual = env.get_attr("public_potential_reward")
        if actual != [self.public_potential_reward] * env.num_envs:
            raise ValueError("public_potential_environment_checkpoint_mismatch")
        return super().collect_rollouts(env, *args, **kwargs)

    def train(self):
        validate_model(self)
        c = self.public_potential_reward
        size = self.n_steps * self.n_envs
        if size != c["rollout"] or not 0 <= self.public_potential_trained <= c["budget"] - size:
            raise ValueError("public_potential_training_budget")
        super().train()  # No critic coordinate correction, new loss or optimizer.
        self.public_potential_trained += size


def validate_loaded(model, metadata):
    marker = getattr(model, "public_potential_reward", None)
    if marker != metadata.get("public_potential_reward"):
        raise ValueError("public_potential_checkpoint_metadata_mismatch")
    validate_model(model)
    if marker is not None and (type(model.public_potential_trained) is not int
            or model.public_potential_trained != metadata.get("public_potential_trained")
            or not 0 <= model.public_potential_trained <= 65536 or model.public_potential_trained % 512):
        raise ValueError("public_potential_checkpoint_progress")


def initial_model(model, path, experiment, *, resume):
    requested = experiment.get("public_potential_reward")
    actual = getattr(model, "public_potential_reward", None)
    if requested is None:
        if actual is not None:
            raise ValueError("resume_public_potential_opt_in_removed")
        return model
    validate_contract(requested)
    if actual is not None:
        if actual != requested or type(model) is not PotentialFoundationPPO:
            raise ValueError("resume_public_potential_contract_mismatch")
        return model
    if (resume or type(model) is not FoundationCombatPPO or model.gae_lambda != .95
            or model.gamma != 1. or digest(path) != PARENT_SHA or experiment.get("fresh_optimizer") is not False):
        raise ValueError("public_potential_requires_original_parent_and_Adam")
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest
    converted = PotentialFoundationPPO.load(path, device="cpu",
        public_potential_reward=requested, public_potential_trained=0)
    if (tensor_digest(model.policy.state_dict()) != tensor_digest(converted.policy.state_dict())
            or optimizer_digest(model.policy) != optimizer_digest(converted.policy)):
        raise ValueError("public_potential_initial_weights_or_Adam_changed")
    validate_model(converted)
    return converted


class PotentialSignalRecorder(AuditedSignalRecorder):
    """Raw, shaped and timeout-corrected rewards are distinct audit fields."""
    def __init__(self, directory, encoder, reference=None):
        super().__init__(directory, encoder)
        self.reference = Path(reference) if reference else None

    def start(self, model, clock):
        super().start(model, clock)
        self._model = model

    def step(self, infos, dones):
        super().step(infos, dones)
        for row, info in zip(self.infos[-1], infos):
            native = info["native_outcome"]
            raw = float(native["rewards"]["self"])
            proof = info.get("public_potential")
            if proof is not None and proof["raw_native_reward"] != raw:
                raise ValueError("public_potential_raw_reward_receipt_mismatch")
            timeout_value = 0.
            if row["truncated"]:
                terminal = info.get("terminal_observation")
                if terminal is None:
                    raise ValueError("public_potential_missing_timeout_bootstrap_observation")
                with torch.no_grad():
                    tensor = self._model.policy.obs_to_tensor(terminal)[0]
                    timeout_value = float(self._model.policy.predict_values(tensor).flatten()[0])
            row.update(raw_native_reward=raw, shaped_env_reward=proof["shaped_env_reward"] if proof else raw,
                phi_before=proof["phi_before"] if proof else 0., phi_next=proof["phi_next"] if proof else 0.,
                potential_delta=proof["delta"] if proof else 0., potential_receipt=proof,
                native_terminated=native["terminated"], expected_timeout_bootstrap=timeout_value)

    def end(self, model, clock):
        super().end(model, clock)
        name = self.pending[0]
        shape = (model.n_steps, model.n_envs)
        def array(key):
            return np.array([[r[key] for r in step] for step in self.infos]).reshape(shape)
        raw, shaped = array("raw_native_reward"), array("shaped_env_reward")
        before, nxt, delta = array("phi_before"), array("phi_next"), array("potential_delta")
        terminated = array("native_terminated").astype(bool)
        truncated = array("truncated").astype(bool)
        reward = model.rollout_buffer.rewards.copy()
        correction = reward.astype(float) - shaped
        expected_correction = array("expected_timeout_bootstrap")
        if (not np.isfinite(shaped).all() or abs(shaped-raw-delta).max() > 1e-6
                or abs(delta-(nxt-before)).max() > 1e-6 or nxt[terminated].any()
                or abs(correction-expected_correction).max() > 2e-6):
            raise ValueError("public_potential_reward_or_timeout_audit_failed")
        arrays = {"raw_native_rewards": raw, "shaped_env_rewards": shaped, "phi_before": before,
            "phi_next": nxt, "potential_delta": delta, "timeout_bootstrap_correction": correction,
            "expected_timeout_bootstrap": expected_correction}
        path = self.directory / (name + ".potential.npz")
        with path.open("xb") as stream:
            np.savez_compressed(stream, **arrays)
        proof = {"capture_SHA256": digest(path), "transitions": raw.size,
            "potential_nonzero_transitions": int(np.count_nonzero(delta)),
            "max_abs_phi": float(max(abs(before).max(), abs(nxt).max())),
            "max_abs_delta": float(abs(delta).max()), "timeout_count": int(truncated.sum()),
            "native_reward_sum": float(raw.sum()), "shaped_env_reward_sum": float(shaped.sum()),
            "first_preupdate_comparison": None}
        if clock == 32768:
            proof["first_preupdate_comparison"] = self.compare_first(name, arrays)
        durable_json(self.directory / (name + ".potential.json"), proof)

    def compare_first(self, name, own):
        path = self.directory / (name + ".audit.npz")
        if self.reference is None:
            return {"role": "reference", "capture": str(path), "SHA256": digest(path)}
        refs = list(self.reference.glob("rollout_1049088_*.audit.npz"))
        if len(refs) != 1:
            raise ValueError("potential_first_rollout_reference_missing_or_ambiguous")
        fields = ("raw_logits", "probabilities", "native_masks", "actions", "old_logp", "values",
            "episode_starts", "last_values", "last_dones")
        with np.load(path) as a, np.load(refs[0]) as b:
            if any(not np.array_equal(a[k], b[k]) for k in fields):
                raise ValueError("potential_first_rollout_policy_or_execution_mismatch")
        with np.load(refs[0].with_name(refs[0].name.replace(".audit.npz", ".potential.npz"))) as b:
            if not np.array_equal(own["raw_native_rewards"], b["raw_native_rewards"]):
                raise ValueError("potential_first_rollout_native_rewards_changed")
        def rows(file):
            with gzip.open(file, "rt", encoding="utf8") as stream:
                return [json.loads(line) for line in stream]
        a = rows(self.directory / (name + ".jsonl.gz"))
        b = rows(refs[0].with_name(refs[0].name.replace(".audit.npz", ".jsonl.gz")))
        keys = ("observation_sha256", "legal_mask_bits", "action", "old_logp", "value",
            "raw_native_reward", "episode_start", "done", "truncated")
        if len(a) != 512 or len(b) != 512 or any(x[k] != y[k] for x, y in zip(a, b) for k in keys):
            raise ValueError("potential_first_rollout_public_or_boundary_mismatch")
        return {"role": "matched_before_any_B_update", "reference": str(refs[0]),
            "reference_SHA256": digest(refs[0]), "exact_fields": list(fields) + ["raw_native_rewards"],
            "public_rows_exact": 512, "shaped_rewards_GAE_returns": "intentional_treatment_difference"}
