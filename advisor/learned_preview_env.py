"""One preview decision -> frozen native battle -> terminal reward.

This coordinator owns scenarios. Only PreviewEncoder output enters PPO. An
artificial native timeout fails closed (no false draw/MC label or PPO update).
"""
from copy import deepcopy
import gymnasium as gym
import numpy as np
import torch

from advisor.learned_preview import PreviewEncoder, public_preview, selection, DIMENSION
from advisor.learned_policy import LearnedPolicy
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_encoder import fingerprint
from advisor.showdown_environment import ShowdownEnvironment


def freeze_battle_policy(path, catalog, identity):
    player = LearnedPolicy(path, catalog, expected_model_id=identity)
    if player.encoder.version != "showdown-public-categorical-observation-v4":
        raise ValueError("preview_requires_frozen_categorical_v4_battle_policy")
    player.model.policy.set_training_mode(False)
    for parameter in player.model.policy.parameters():
        parameter.requires_grad_(False)
    return player


def execute_preview_battle(env, case, candidate_side, preview_action, player, rival, *, stopping=None):
    """Submit the exact ordered slots through the existing native team choices."""
    native = deepcopy(case)
    native["preview"][candidate_side] = selection(preview_action)
    transition = env.reset(native)
    rejections = 0
    while not (transition["terminated"] or transition["truncated"]):
        if stopping and stopping():
            raise InterruptedError("preview_battle_interrupted_no_return_label")
        views = {s: env.observation(s, include_history=True) for s in ("self", "opponent")}
        with torch.no_grad():
            actions = {s: (player if s == candidate_side else rival).act(views[s]) for s in views}
        if any(not views[s]["action_mask"][a] for s, a in actions.items()):
            raise ValueError("preview_frozen_battle_policy_mask_violation")
        transition = env.step(actions, revision=views["self"]["revision"])
        rejections += int(transition["action_rejected"])
    # No synthetic reward for an artificial limit. A partial battle never
    # becomes a native draw/loss, nor a completed preview learning episode.
    if transition["truncated"]:
        raise RuntimeError("preview_native_timeout_no_terminal_learning_label")
    reward = transition["rewards"][candidate_side]
    return {"reward": reward, "outcome": "win" if reward == 1 else "loss" if reward == -1 else "draw",
            "terminated": True, "truncated": False, "native_decisions": transition["decisions"],
            "native_rejections": rejections, "selected_slots": selection(preview_action),
            "candidate_side": candidate_side}


class PreviewLearningEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, checkout, catalog, battle_model, battle_sha, case_provider, *,
                 index_offset=0, stride=1, opponents=("tactical_heuristic", "champions_heuristic")):
        torch.set_num_threads(1)
        self.encoder = PreviewEncoder(catalog)
        self.player = freeze_battle_policy(battle_model, catalog, battle_sha)
        self.native = ShowdownEnvironment(checkout, max_decisions=4096)
        self.provider, self.offset, self.stride = case_provider, index_offset, stride
        self.index, self.opponents = index_offset, tuple(opponents)
        self.action_space = gym.spaces.Discrete(120)
        self.observation_space = gym.spaces.Box(-8, 8, (DIMENSION,), dtype=np.float32)
        self.current = None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            # Shared experiment seed, disjoint worker streams; no model-visible ID.
            self.index = int(seed) * 100000 + self.offset
        self.case_index = self.index
        self.index += self.stride
        self.current = self.provider("train", self.case_index)
        self.rival_kind = self.opponents[(self.case_index // self.stride) % len(self.opponents)]
        # Seat and rival are independently crossed, not confounded by parity.
        self.side = "self" if (self.case_index // (self.stride * len(self.opponents))) % 2 == 0 else "opponent"
        self.public = public_preview(self.native.preview(self.current, self.side))
        return self.encoder.encode(self.public), {}

    def action_masks(self):
        return np.ones(120, dtype=bool)  # full native-validated six, distinct ordered slots

    def step(self, action):
        if self.current is None:
            raise RuntimeError("preview_reset_required")
        action = int(action)
        selection(action)
        rival = VisibleBaseline(self.rival_kind, self.case_index + 919)
        record = execute_preview_battle(self.native, self.current, self.side, action, self.player, rival)
        record.update({"case_index": self.case_index, "case_sha256": fingerprint(self.current),
            "team_sha256": {s: fingerprint(t) for s, t in self.current["teams"].items()},
            "native_seed": self.current["seed"], "opponent_selected_slots": self.current["preview"]["opponent" if self.side == "self" else "self"],
            "opponent": self.rival_kind, "preview_action": action})
        self.current = None
        return np.zeros(DIMENSION, np.float32), float(record["reward"]), True, False, {"preview_episode": record}

    def close(self):
        self.native.close()
