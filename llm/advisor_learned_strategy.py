"""Explicit opt-in learned evidence alongside native shadow, never ranking truth.

The default import path has no NumPy/Torch dependency. Trusted local model loading
is lazy and bounded; native checkpoints remain coordinator-only.
"""

from functools import lru_cache
from math import isfinite
from threading import RLock

SCHEMA = "showdown-learned-strategy-v1"
INTERPRETATION = (
    "hypothetical_learned_policy_and_discounted_return_not_exact_or_win_probability"
)
_MODEL_LOCK = RLock()
BINDING = (
    "session_id",
    "source_runtime_fingerprint",
    "source_capture_fingerprint",
    "decision_branch_fingerprint",
    "decision_owner",
)


@lru_cache(maxsize=2)
def _load_model(model_path, catalog_path, expected_model_id):
    from advisor.learned_policy import LearnedPolicy

    policy = LearnedPolicy(
        model_path, catalog_path, expected_model_id=expected_model_id
    )
    return policy


def learned_configuration(context):
    config = context.get("learned_policy")
    return (
        config if isinstance(config, dict) and config.get("enabled") is True else None
    )


def infer_native_root(*, checkpoint, binding, scenario, config, bridge):
    """One visible observation at the root, before the hypothetical rival acts."""
    from advisor.showdown_environment import ShowdownEnvironment

    result = {
        "schema_version": SCHEMA,
        "mode": "experimental_shadow",
        "default_policy_changed": False,
        "evidence_class": "learned_policy_value",
        "interpretation": INTERPRETATION,
        **{key: binding[key] for key in BINDING},
        "context_fingerprint": binding["context_fingerprint"],
        "scenario_id": scenario["scenario_id"],
        "root_checkpoint_fingerprint": checkpoint["checkpoint_fingerprint"],
    }
    try:
        if any(
            checkpoint.get(key) != binding[key]
            for key in ("session_id", "source_runtime_fingerprint")
        ):
            raise ValueError("learned_checkpoint_source_mismatch")
        if config.get("schema_version") != "showdown-learned-config-v1":
            raise ValueError("invalid_learned_configuration")
        expected = config["expected_model_id"]
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("explicit_learned_model_version_required")
        with _MODEL_LOCK:
            policy = _load_model(config["model_path"], config["catalog_path"], expected)
        with ShowdownEnvironment(worker=bridge) as env:
            env.from_native_checkpoint(checkpoint)
            visible = env.observation("self", include_history=True)
            inference = policy.infer(visible)
        return {
            **result,
            "status": "evaluated",
            "model_id": expected,
            "inference": inference,
            "action_mask": visible["action_mask"],
            "choices": visible["choices"],
            "action_label": _label(visible, inference["action_index"]),
        }
    except (
        ImportError,
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        TypeError,
        AttributeError,
    ):
        # Invalid model/dependency/phase cannot invalidate existing native evidence.
        return {
            **result,
            "status": "unavailable",
            "reason": "learned_model_or_native_phase_unavailable",
        }


def _label(observation, index):
    choice = observation["choices"][index]
    request = observation["own_request"]
    if choice.startswith("move "):
        slot = int(choice.split()[1]) - 1
        move = request["active"][0]["moves"][slot]["move"]
        return move + (" · Mega" if "mega" in choice else "")
    if choice.startswith("switch "):
        slot = int(choice.split()[1]) - 1
        return "교체 " + request["side"]["pokemon"][slot]["details"].split(",")[0]
    return "상대 후속 선택 대기"


def valid_learned_evidence(value, binding, scenario):
    try:
        if (
            value.get("schema_version") != SCHEMA
            or value.get("mode") != "experimental_shadow"
            or value.get("default_policy_changed") is not False
            or value.get("evidence_class") != "learned_policy_value"
            or value.get("interpretation") != INTERPRETATION
        ):
            return False
        if any(
            value.get(k) != binding.get(k) for k in BINDING + ("context_fingerprint",)
        ):
            return False
        if any(
            value.get(k) != scenario.get(k)
            for k in ("scenario_id", "root_checkpoint_fingerprint")
        ):
            return False
        if value.get("status") == "unavailable":
            return value.get("reason") == "learned_model_or_native_phase_unavailable"
        if value.get("status") != "evaluated":
            return False
        proof = value["inference"]
        if value.get("model_id") != binding.get("learned_model_id"):
            return False
        if (
            proof.get("schema_version") != "showdown-learned-inference-v1"
            or proof.get("evidence_class") != "learned_policy_value"
            or proof.get("interpretation")
            != "experimental_policy_choice_and_discounted_return_not_exact_or_win_probability"
            or proof.get("action_schema_version") != "showdown-policy-actions-v1"
            or proof.get("discount_factor") != 0.99
            or proof.get("reward_scope") != "native_sparse_terminal_win_loss_draw"
            or proof.get("encoder_version")
            not in {
                "showdown-learned-observation-v1",
                "showdown-learned-observation-v2",
            }
            or proof.get("side") != "self"
            or proof.get("model_id") != value["model_id"]
            or len(value["model_id"]) != 64
            or not isinstance(proof.get("episode_id"), str)
            or not proof["episode_id"]
            or type(proof.get("revision")) is not int
            or proof["revision"] < 0
            or type(proof.get("turn")) is not int
            or proof["turn"] < 0
            or proof.get("request_state") not in {"move", "switch"}
        ):
            return False
        phase = scenario["native_decision_phase"]
        if (
            proof["turn"] != phase["turn"]
            or proof["request_state"] != phase["request_state"]
        ):
            return False
        p, mask, choices, action = (
            proof["action_probabilities"],
            value["action_mask"],
            value["choices"],
            proof["action_index"],
        )
        if (
            len(p) != 35
            or len(mask) != 35
            or len(choices) != 35
            or type(action) is not int
            or not 0 <= action < 35
        ):
            return False
        if any(
            type(m) is not int
            or m not in (0, 1)
            or m != int(c is not None)
            or (c is not None and not isinstance(c, str))
            for m, c in zip(mask, choices)
        ):
            return False
        if any(
            type(x) not in (float, int)
            or not isfinite(x)
            or not 0 <= x <= 1
            or (not m and x != 0)
            for x, m in zip(p, mask)
        ):
            return False
        if (
            abs(sum(p) - 1) > 1e-6
            or not mask[action]
            or p[action] != max(p)
            or proof["native_choice"] != choices[action]
        ):
            return False
        if not isinstance(value.get("action_label"), str) or not value["action_label"]:
            return False
        return type(proof["discounted_return_estimate"]) in (float, int) and isfinite(
            proof["discounted_return_estimate"]
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
