"""Spawn-safe factories for maintained SB3 vector environments.

Only immutable paths/hashes cross startup. Child opponents see their own public
policy view; no model/scenario/native handles are pickled from the parent.
"""

from dataclasses import dataclass
from advisor.learned_action_encoder import make_encoder
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_gym import ShowdownLearningEnv
from advisor.learning_resources import enforce_local_network_only


@dataclass(frozen=True)
class LearningEnvFactory:
    checkout: str
    catalog: str
    encoder_version: str
    index_offset: int
    curriculum_version: str
    opponents: tuple
    references: dict
    collect_tactical_metrics: bool = False
    max_decisions: int = 256
    diagnostic_directory: str | None = None
    collect_public_trajectories: bool = False
    terminal_transport_version: str | None = None
    training_subset_path: str | None = None
    training_subset_sha256: str | None = None

    def __call__(self):
        import torch

        torch.set_num_threads(1)
        enforce_local_network_only()
        cache = {}

        def opponent(kind, seed):
            if kind == "public_failure_aware_v1":
                from advisor.learned_failure_opponent import PublicFailureAwareOpponent
                if kind not in self.references:
                    return PublicFailureAwareOpponent(seed)
                if kind not in cache:
                    from advisor.learned_policy import LearnedPolicy
                    path, identity = self.references[kind]
                    cache[kind] = LearnedPolicy(path, self.catalog, expected_model_id=identity)
                return PublicFailureAwareOpponent(seed, base=cache[kind])
            if kind not in self.references:
                return VisibleBaseline(kind, seed)
            if kind not in cache:
                from advisor.learned_policy import LearnedPolicy

                path, identity = self.references[kind]
                cache[kind] = LearnedPolicy(
                    path, self.catalog, expected_model_id=identity
                )
            return cache[kind]

        subset = None
        if self.training_subset_path:
            from advisor.learned_training_subset import NativeTrainingSubset
            subset = NativeTrainingSubset(self.training_subset_path, self.training_subset_sha256)
        return ShowdownLearningEnv(
            self.checkout,
            make_encoder(self.catalog, self.encoder_version),
            index_offset=self.index_offset,
            curriculum_version=self.curriculum_version,
            opponents=self.opponents,
            opponent_factory=opponent,
            collect_tactical_metrics=self.collect_tactical_metrics,
            max_decisions=self.max_decisions,
            diagnostic_directory=self.diagnostic_directory,
            collect_public_trajectories=self.collect_public_trajectories,
            terminal_transport_version=self.terminal_transport_version,
            training_subset=subset,
            collect_v5_supervision=self.encoder_version in ("showdown-public-categorical-observation-v5-integrated-v1", "showdown-public-categorical-observation-v5-integrated-v2"),
        )
