"""Gymnasium adapter around the validated local environment, no new mechanics."""

import gymnasium as gym
import numpy as np
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_scenarios import scenario


class ShowdownLearningEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self, checkout, encoder, *, split="train", index_offset=0, max_decisions=256
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
        current = scenario(self.split, index)
        self.native.reset(current)
        kind = (options or {}).get(
            "opponent", ("random", "max_power", "heuristic")[index % 3]
        )
        self.opponent = VisibleBaseline(kind, index + 91)
        self.current = self.native.observation("self", include_history=True)
        encoded = self.encoder.encode(self.current)
        if self.observation_space is None:
            self.observation_space = gym.spaces.Box(
                -2, 4, shape=encoded.shape, dtype=np.float32
            )
        return encoded, {"opponent": kind}

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
                "opponent": self.opponent.act(self.native.observation("opponent")),
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
                    "opponent": self.opponent.act(self.native.observation("opponent")),
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
                    "opponent": self.opponent.kind,
                }
            )
        return (
            self.encoder.encode(self.current),
            float(result["rewards"]["self"]),
            result["terminated"],
            result["truncated"],
            {"native_outcome": result},
        )

    def close(self):
        self.native.close()
