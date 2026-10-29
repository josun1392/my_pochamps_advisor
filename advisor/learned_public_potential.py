"""Opt-in public faint-progress reward; no policy features or native truth.

Counts are cumulative delivered events, NOT a current living-Pokemon estimate.
Whole histories are recomputed; request refreshes cannot count an event twice.
"""
from collections import Counter
from hashlib import sha256
import json
import math
import re

import gymnasium as gym

VERSION = "PUBLIC_FAINT_PROGRESS_PHI_V1"
TRAINING_VERSION = "foundation-public-faint-potential-PPO-v1"
PARENT_SHA = "9b3eb94aabea1fb25e75dfdba0b733c2a9acd45434ae368a86e14d8979950ccf"
ENTITY = re.compile(r"^(p[12])[a-z]?: .+$")


def potential_contract():
    return {"schema_version": TRAINING_VERSION, "potential_version": VERSION,
        "alpha": .10, "normalizer": 3, "count_cap": 3, "gamma": 1., "gae_lambda": .95,
        "reward": "native_reward_plus_Phi_next_minus_Phi_current",
        "terminal": "Phi_zero_only_actual_native_termination",
        "history": "complete_owner_public_history_causal_append_only_episode_bound",
        "value": "raw_initial_critic_unchanged_then_shaped_return_no_fixed_subtraction",
        "parent_model_sha256": PARENT_SHA, "budget": 65536, "rollout": 512}


def validate_contract(value):
    # Python numeric equality alone would accept bools in integer fields.
    expected = potential_contract()
    if (not isinstance(value, dict) or value != expected
            or any(type(value[k]) is not type(v) for k, v in expected.items())):
        raise ValueError("invalid_public_potential_contract")
    return dict(value)


def history_digest(history):
    return sha256(json.dumps(history, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def public_progress(view):
    """Read only owner binding, terminal flags and delivered public protocol.

    Identical text at different positions is not globally deduplicated: revival
    can legitimately produce another faint. A repeated faint without intervening
    public positive-health evidence is rejected, rather than guessed away.
    """
    if (not isinstance(view, dict) or view.get("side") not in ("self", "opponent")
            or not isinstance(view.get("episode_id"), str) or not view["episode_id"]
            or type(view.get("revision")) is not int or view["revision"] < 0
            or type(view.get("turn")) is not int or view["turn"] < 0
            or type(view.get("terminated")) is not bool or type(view.get("truncated")) is not bool
            or view["terminated"] and view["truncated"]):
        raise ValueError("public_potential_owner_or_boundary_binding")
    lines = view.get("public_history")
    if (not isinstance(lines, list) or any(not isinstance(x, str) for x in lines)
            or lines.count("|start") != 1):
        raise ValueError("public_potential_requires_complete_history")
    counts, fainted, turn = Counter(), set(), 0
    for line in lines:
        parts = line.split("|")
        if len(parts) < 2 or parts[0] != "":
            raise ValueError("public_potential_malformed_public_line")
        event, args = parts[1], parts[2:]
        if event in {"split", "request", "sideupdate", "input", "seed"}:
            raise ValueError("private_protocol_in_public_potential")
        if event == "turn":
            if len(args) != 1 or not args[0].isdigit() or int(args[0]) != turn + 1:
                raise ValueError("public_potential_turn_order_or_duplicate")
            turn = int(args[0])
        if event == "faint":
            if len(args) != 1 or not ENTITY.fullmatch(args[0]) or args[0] in fainted:
                raise ValueError("public_potential_faint_binding_or_duplicate")
            counts[ENTITY.fullmatch(args[0]).group(1)] += 1
            fainted.add(args[0])
        elif event in {"-heal", "switch", "drag", "replace"} and args:
            # This is duplicate validation, not a mechanics/identity interpreter.
            index = 2 if event in {"switch", "drag", "replace"} else 1
            if len(args) > index:
                health = args[index].split(" ")[0]
                if "/" in health and health.split("/", 1)[0].isdigit() and int(health.split("/", 1)[0]) > 0:
                    fainted.discard(args[0])
    if turn != view["turn"]:
        raise ValueError("public_potential_turn_view_mismatch")
    own = "p1" if view["side"] == "self" else "p2"
    other = "p2" if own == "p1" else "p1"
    value = 0. if view["terminated"] else (.10 / 3) * (min(counts[other], 3) - min(counts[own], 3))
    return {"phi": value, "own_faints": counts[own], "opponent_faints": counts[other],
        "history_length": len(lines), "history_sha256": history_digest(lines)}


def public_phi(view):
    return public_progress(view)["phi"]


class PublicPotentialReward(gym.Wrapper):
    """One difference per complete learner step, before VecEnv auto-reset.

    Native rewards/infos and inner wait/retry/mask behavior stay unchanged.
    The maintained PPO alone adds the time-limit value bootstrap afterwards.
    """
    def __init__(self, env, contract):
        super().__init__(env)
        self.public_potential_reward = validate_contract(contract)
        self._bound = None
        self._raw_sum = self._shaped_sum = 0.

    @property
    def current(self):
        return self.env.current

    def _binding(self, view):
        return (view["episode_id"], view["side"], view["revision"], tuple(view["public_history"]))

    def reset(self, **kwargs):
        self._bound = None
        result = self.env.reset(**kwargs)
        progress = public_progress(self.current)
        if progress["own_faints"] or progress["opponent_faints"] or self.current["terminated"] or self.current["truncated"]:
            raise ValueError("public_potential_reset_not_fresh_native_episode")
        self._bound = self._binding(self.current)
        self._raw_sum = self._shaped_sum = 0.
        return result

    def step(self, action):
        if self._bound is None or self._binding(self.current) != self._bound:
            raise ValueError("public_potential_predecision_history_changed")
        before = public_progress(self.current)
        old = self._bound
        # Close on any exception: no second execution of an uncertain transition.
        self._bound = None
        features, raw, terminated, truncated, info = self.env.step(action)
        nxt = self.current
        after = public_progress(nxt)
        binding = self._binding(nxt)
        if (binding[:2] != old[:2] or binding[2] <= old[2]
                or binding[3][:len(old[3])] != old[3]):
            raise ValueError("public_potential_history_not_causal_append")
        native = info["native_outcome"]
        if (terminated != nxt["terminated"] or truncated != nxt["truncated"]
                or native["terminated"] != terminated or native["truncated"] != truncated
                or type(raw) not in (float, int) or not math.isfinite(raw)
                or raw != native["rewards"]["self"] or raw not in (-1., 0., 1.)):
            raise ValueError("public_potential_native_reward_or_boundary_changed")
        delta = after["phi"] - before["phi"]
        shaped = raw + delta
        self._raw_sum += raw
        self._shaped_sum += shaped
        if terminated and abs(self._shaped_sum - self._raw_sum) > 1e-6:
            raise ValueError("public_potential_episode_return_identity_failed")
        self._bound = None if terminated or truncated else binding
        proof = {"schema_version": VERSION, "episode_id": binding[0],
            "revision_before": old[2], "revision_after": binding[2],
            "raw_native_reward": float(raw), "phi_before": before["phi"], "phi_next": after["phi"],
            "delta": delta, "shaped_env_reward": shaped,
            "history_before_sha256": before["history_sha256"], "history_next_sha256": after["history_sha256"],
            "history_before_length": before["history_length"], "history_next_length": after["history_length"],
            "terminated": terminated, "truncated": truncated,
            "timeout_bootstrap": "not_added_here_maintained_PPO_adds_shaped_value_once"}
        if terminated:
            proof.update(episode_raw_return=self._raw_sum, episode_shaped_return=self._shaped_sum)
        return features, shaped, terminated, truncated, {**info, "public_potential": proof}
