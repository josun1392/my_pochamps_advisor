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

    def __call__(self):
        import torch

        torch.set_num_threads(1)
        enforce_local_network_only()
        cache = {}

        def opponent(kind, seed):
            if kind not in self.references:
                return VisibleBaseline(kind, seed)
            if kind not in cache:
                from advisor.learned_policy import LearnedPolicy

                path, identity = self.references[kind]
                cache[kind] = LearnedPolicy(
                    path, self.catalog, expected_model_id=identity
                )
            return cache[kind]

        return ShowdownLearningEnv(
            self.checkout,
            make_encoder(self.catalog, self.encoder_version),
            index_offset=self.index_offset,
            curriculum_version=self.curriculum_version,
            opponents=self.opponents,
            opponent_factory=opponent,
            collect_tactical_metrics=self.collect_tactical_metrics,
        )
