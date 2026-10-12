"""Gymnasium adapter around the validated local environment, no new mechanics."""

import gymnasium as gym
import numpy as np
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_scenarios import scenario


class ShowdownLearningEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        checkout,
        encoder,
        *,
        split="train",
        index_offset=0,
        max_decisions=256,
        curriculum_version="showdown-learning-curriculum-v1",
        opponents=None,
        opponent_factory=None,
    ):
        self.native = ShowdownEnvironment(checkout, max_decisions=max_decisions)
        self.encoder, self.split, self.index, self.offset = (
            encoder,
            split,
            0,
            index_offset,
        )
        self.action_space = gym.spaces.Discrete(35)
        self.observation_space = None
        self.completed = []
        self.current = None
        self.curriculum_version = curriculum_version
        self.opponents = opponents or ("random", "max_power", "heuristic")
        self.opponent_factory = opponent_factory
        try:
            self.reset()
        except BaseException:
            self.native.close()
            raise

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.index = seed * 1000 + self.offset
        index = self.index
        self.index += 1
        current = (
            scenario(self.split, index, version=self.curriculum_version)
            if self.curriculum_version != "showdown-learning-curriculum-v1"
            else scenario(self.split, index)
        )
        from advisor.learned_tactical_curriculum import reset_learning_episode

        self.start_info = reset_learning_episode(self.native, current)
        kind = (options or {}).get(
            "opponent", self.opponents[index % len(self.opponents)]
        )
        self.opponent = (
            self.opponent_factory(kind, index + 91)
            if self.opponent_factory
            else VisibleBaseline(kind, index + 91)
        )
        self.opponent_kind = kind
        self.current = self.native.observation("self", include_history=True)
        encoded = self.encoder.encode(self.current)
        if self.observation_space is None:
            self.observation_space = gym.spaces.Box(
                -2, 4, shape=encoded.shape, dtype=np.float32
            )
        return encoded, self._policy_info()

    def _policy_info(self):
        return {
            "schema_version": "showdown-learning-info-v2",
            "episode_id": self.current["episode_id"],
            "revision": self.current["revision"],
            "request_state": self.current["request_state"],
        }

    def action_masks(self):
        return np.asarray(self.current["action_mask"], dtype=bool)

    def step(self, action):
        if (
            not isinstance(action, (int, np.integer))
            or not 0 <= int(action) < 35
            or not self.action_masks()[int(action)]
        ):
            raise ValueError("masked_learning_action")
        result = self.native.step(
            {
                "self": int(action),
                "opponent": self.opponent.act(
                    self.native.observation("opponent", include_history=True)
                ),
            },
            revision=self.current["revision"],
        )
        self.current = self.native.observation("self", include_history=True)
        while (
            not (result["terminated"] or result["truncated"])
            and self.current["action_mask"][26]
        ):
            result = self.native.step(
                {
                    "self": 26,
                    "opponent": self.opponent.act(
                        self.native.observation("opponent", include_history=True)
                    ),
                },
                revision=self.current["revision"],
            )
            self.current = self.native.observation("self", include_history=True)
        if result["terminated"] or result["truncated"]:
            self.completed.append(
                {
                    "winner": result["winner"],
                    "truncated": result["truncated"],
                    "decisions": result["decisions"],
                    "opponent": self.opponent_kind,
                }
            )
        return (
            self.encoder.encode(self.current),
            float(result["rewards"]["self"]),
            result["terminated"],
            result["truncated"],
            {
                **self._policy_info(),
                "native_outcome": {
                    k: result[k]
                    for k in (
                        "revision",
                        "decisions",
                        "terminated",
                        "truncated",
                        "winner",
                        "action_rejected",
                        "rewards",
                    )
                },
            },
        )

    def drain_completed(self):
        rows, self.completed = self.completed, []
        return rows

    def learning_resources(self):
        return dict(self.native.resources)

    def close(self):
        self.native.close()
