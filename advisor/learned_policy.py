"""Trusted local model inference; distributions are policy choices, not win odds."""

from hashlib import sha256
import json
import math
import random
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from advisor.learned_encoder import ENCODER_VERSION
from advisor.learned_action_encoder import make_encoder
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
from advisor.learned_objective import objective_contract, CATEGORICAL_VERSIONS


class LearnedPolicy:
    def __init__(
        self, model_path, catalog, *, require_manifest=True, expected_model_id=None
    ):
        torch.set_num_threads(1)
        path = Path(model_path).with_suffix(".zip")
        self.model_id = sha256(path.read_bytes()).hexdigest()
        if expected_model_id is not None and self.model_id != expected_model_id:
            raise ValueError("unexpected_learned_model_version")
        self.metadata = (
            json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            if require_manifest
            else {}
        )
        self.encoder = make_encoder(
            catalog,
            self.metadata.get("encoder_version")
            if require_manifest
            else ENCODER_VERSION,
        )
        if require_manifest and (
            self.metadata.get("schema_version") != "showdown-learned-model-v1"
            or self.metadata.get("evidence_class") != "learned_policy_value"
            or self.metadata.get("algorithm") != "sb3-contrib-MaskablePPO"
            or self.metadata.get("interpretation")
            != "experimental_policy_distribution_and_discounted_return_not_exact_win_probability"
            or self.metadata.get("model_sha256") != self.model_id
            or self.metadata.get("catalog_fingerprint")
            != self.encoder.catalog_fingerprint
            or self.metadata.get("engine_commit") != SHOWDOWN_COMMIT
            or self.metadata.get("format_id") != FORMAT_ID
            or self.metadata.get("action_schema_version")
            != "showdown-policy-actions-v1"
        ):
            raise ValueError("model_manifest_or_contract_mismatch")
        # SB3 zip uses pickle internally. Only artifacts produced/verified locally
        if hasattr(self.encoder, "feature_contract") and self.metadata.get(
            "feature_contract"
        ) != self.encoder.feature_contract:
            raise ValueError("public_categorical_feature_contract_mismatch"
                             if self.encoder.version in CATEGORICAL_VERSIONS
                             else "own_move_feature_contract_mismatch")
        # by the trusted coordinator are accepted; hashes do not sandbox untrusted files.
        # SB3 loading calls set_random_seed. Validation/inference must not reset
        # another learner's global sampling stream as a hidden side effect.
        py_state, np_state = random.getstate(), np.random.get_state()
        devices = (
            list(range(torch.cuda.device_count()))
            if torch.cuda.is_initialized()
            else []
        )
        with torch.random.fork_rng(devices=devices):
            try:
                from advisor.learned_regularized_ppo import checkpoint_algorithm, validate_loaded_regularizer
                self.model = checkpoint_algorithm(self.metadata).load(path, device="cpu")
                validate_loaded_regularizer(self.model, self.metadata)
            finally:
                random.setstate(py_state)
                np.random.set_state(np_state)
        if self.model.action_space.n != 35 or self.model.observation_space.shape != (
            self.encoder.dimension,
        ):
            raise ValueError("incompatible_model_spaces")
        if require_manifest:
            actual = objective_contract(self.model.gamma, self.model.gae_lambda)
            if (type(self.metadata.get("gamma", self.model.gamma)) not in (int, float)
                    or self.metadata.get("gamma", self.model.gamma) != self.model.gamma
                    or self.metadata.get("gae_lambda", self.model.gae_lambda) != self.model.gae_lambda
                    or ("training_objective" in self.metadata and self.metadata["training_objective"] != actual)
                    or (self.model.gamma == 1 and (self.encoder.version not in CATEGORICAL_VERSIONS
                        or self.metadata.get("training_objective") != actual))):
                raise ValueError("model_training_objective_mismatch")
        if hasattr(self.encoder, "feature_contract"):
            from advisor.learned_move_identity_policy import OwnMoveTokenPolicy
            from advisor.learned_public_categories_policy import PublicCategoricalPolicy
            from advisor.learned_strategic_public_policy import StrategicPublicCategoricalPolicy

            required = (StrategicPublicCategoricalPolicy if self.encoder.version == "showdown-public-categorical-observation-v4"
                        else PublicCategoricalPolicy if self.encoder.version in CATEGORICAL_VERSIONS
                        else OwnMoveTokenPolicy)
            if type(self.model.policy) is not required:
                raise ValueError("public_categorical_policy_required"
                                 if self.encoder.version in CATEGORICAL_VERSIONS
                                 else "own_move_categorical_policy_required")

    def infer(self, observation):
        features = self.encoder.encode(observation)
        mask = np.asarray(observation["action_mask"], dtype=bool)
        if mask.shape != (35,) or not mask.any():
            raise ValueError("no_native_policy_action")
        with torch.no_grad():
            tensor = torch.tensor(features)[None, :]
            distribution = self.model.policy.get_distribution(
                tensor, action_masks=mask[None, :]
            )
            probabilities = distribution.distribution.probs[0].cpu().numpy()
            value = float(self.model.policy.predict_values(tensor).flatten()[0])
        if (
            not math.isfinite(value)
            or not np.all(np.isfinite(probabilities))
            or np.any(probabilities[~mask] != 0)
            or not np.isclose(probabilities.sum(), 1)
        ):
            raise ValueError("invalid_learned_distribution")
        action = int(probabilities.argmax())
        return {
            "schema_version": "showdown-learned-inference-v1",
            "evidence_class": "learned_policy_value",
            "interpretation": "experimental_policy_choice_and_discounted_return_not_exact_or_win_probability",
            "encoder_version": self.encoder.version,
            "action_schema_version": "showdown-policy-actions-v1",
            "model_id": self.model_id,
            "public_catalog_coverage": self.encoder.coverage(observation),
            "public_state_version": observation["state"].get("state_version"),
            "episode_id": observation["episode_id"],
            "revision": observation["revision"],
            "side": observation["side"],
            "turn": observation["turn"],
            "request_state": observation["request_state"],
            "action_index": action,
            "native_choice": observation["choices"][action],
            "action_probabilities": [float(x) for x in probabilities],
            "discount_factor": self.model.gamma,
            "reward_scope": "native_sparse_terminal_win_loss_draw",
            **({"training_objective": self.metadata["training_objective"]}
               if "training_objective" in self.metadata else {}),
            "discounted_return_estimate": value,
        }

    def act(self, observation):
        return self.infer(observation)["action_index"]
