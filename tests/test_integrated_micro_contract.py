"""Teacher transport tests only; synthetic targets do not establish coverage."""
from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import pytest

from advisor.learned_action_search_teacher import (
    PUBLIC_VERSION, PublicInformationSearchTeacher, public_teacher_binding,
    validate_public_teacher_target,
)
from scripts.pilot_foundation_integrated_micro import MicroLedger, coverage


def view():
    return {"schema_version": "showdown-policy-observation-v1", "episode_id": "fixture",
        "revision": 3, "side": "self", "turn": 2, "request_state": "move",
        "action_schema_version": "showdown-policy-actions-v1", "action_mask": [int(a in (6, 7)) for a in range(35)],
        "choices": [f"move {a-5}" if a in (6, 7) else None for a in range(35)],
        "own_request": {"side": {"id": "p1"}}, "public_history": [], "state": {}}


def fixture_target(v, **kwargs):
    _, binding = public_teacher_binding(v, **kwargs)
    return {"schema_version": PUBLIC_VERSION, "binding": binding, "status": "supported",
        "target": [float(a == 7) for a in range(35)], "evidence_scope": "public_only_admission"}


@pytest.mark.parametrize("field,value", [("revision", 4), ("turn", 3), ("episode_id", "next"),
    ("action_mask", [int(a in (6, 8)) for a in range(35)]), ("public_history", ["|turn|3"])])
def test_stale_mismatched_decision_is_rejected(field, value):
    v = view(); d = fixture_target(v, policy_id="fixture-policy", learning_step=10)
    changed = {**v, field: value}
    with pytest.raises(ValueError):
        validate_public_teacher_target(d, changed, policy_id="fixture-policy", learning_step=10)


@pytest.mark.parametrize("key", ["native_state", "opponent_request", "future_seed", "checkpoint",
    "auxiliary_labels", "coordinator_v5_supervision", "teams", "unreviewed_extra"])
def test_private_or_unreviewed_envelope_cannot_reach_provider(key):
    with pytest.raises(ValueError, match="public_observation_only"):
        public_teacher_binding({**view(), key: {}}, policy_id="p", learning_step=0)


def test_nested_private_payload_is_rejected_and_actual_seat_binding_is_checked():
    v = view(); v["state"] = {"opponent_side": {"native_state": {}}}
    with pytest.raises(ValueError, match="public_observation_only"):
        public_teacher_binding(v, policy_id="p", learning_step=0)
    v = view(); v["side"] = "opponent"; v["own_request"]["side"]["id"] = "p2"
    _, binding = public_teacher_binding(v, policy_id="p", learning_step=0)
    assert binding["side"] == "opponent"
    v["own_request"]["side"]["id"] = "p1"
    with pytest.raises(ValueError, match="role"):
        public_teacher_binding(v, policy_id="p", learning_step=0)


def test_policy_and_learning_time_are_bound():
    v = view(); d = fixture_target(v, policy_id="p", learning_step=10)
    for p, t in (("q", 10), ("p", 11)):
        with pytest.raises(ValueError, match="unbound"):
            validate_public_teacher_target(d, v, policy_id=p, learning_step=t)
    with pytest.raises(ValueError):
        validate_public_teacher_target({"status": "selected", "selected": 7}, v, policy_id="p", learning_step=10)


def test_unknown_mask_or_missing_choice_is_not_inferred():
    v = view(); v["action_mask"][6] = None
    with pytest.raises(ValueError, match="binding"):
        public_teacher_binding(v, policy_id="p", learning_step=0)
    v = view(); v["choices"][6] = ""
    with pytest.raises(ValueError, match="binding"):
        public_teacher_binding(v, policy_id="p", learning_step=0)


@pytest.mark.parametrize("kind", ["illegal", "nan", "negative", "unnormalized", "wrong_width"])
def test_invalid_target_is_never_renormalized_into_a_label(kind):
    v = view(); d = fixture_target(v, policy_id="p", learning_step=0)
    if kind == "illegal": d["target"] = [float(a == 0) for a in range(35)]
    if kind == "nan": d["target"][7] = float("nan")
    if kind == "negative": d["target"][6] = -.1; d["target"][7] = 1.1
    if kind == "unnormalized": d["target"][7] = .9
    if kind == "wrong_width": d["target"] = [1.]
    with pytest.raises(ValueError): validate_public_teacher_target(d, v, policy_id="p", learning_step=0)


def test_surrogate_fallback_and_unknowns_produce_no_teacher_label():
    teacher = object.__new__(PublicInformationSearchTeacher)
    response = SimpleNamespace(kind="fixture-response", last_decision={"fallback": None,
        "comparisons": [1, 2], "limitations": ["unknown_modifiers"],
        "responses": [{"current_availability": "unknown_no_private_request"}]})
    response.act = lambda v: 7
    teacher.response = response
    original = view(); copy = deepcopy(original)
    a = teacher.assess(original, policy_id="p", learning_step=0)
    assert a["status"] == "abstain" and a["target"] is None and original == copy
    # The policy accepts just this public tree, never the surrounding truth.
    for hidden in ({"winner": "self"}, {"winner": "opponent", "set": "different"}):
        envelope = {"public": deepcopy(original), "native_state": hidden}
        assert teacher.assess(envelope["public"], policy_id="p", learning_step=0) == a
    result = coverage([original], teacher, policy_id="p", learning_step=0)
    assert result["supported_targets"] == 0 and result["learning_allowed"] is False
    with pytest.raises(ValueError, match="duplicate"):
        coverage([original, original], teacher, policy_id="p", learning_step=0)


def test_off_and_abstention_do_not_encode_or_step():
    from scripts.train_showdown_autonomous import apply_public_teacher_decision
    def forbidden(*args, **kwargs): raise AssertionError("no work allowed")
    model = SimpleNamespace(num_timesteps=0, rollout_buffer=SimpleNamespace(pos=0))
    encoder = SimpleNamespace(encode=forbidden)
    provider = SimpleNamespace(assess=forbidden)
    off = apply_public_teacher_decision(model, encoder, view(), provider, policy_id="p",
        learning_step=0, enabled=False, ledger=None)
    assert off == {"status": "disabled", "optimizer_updates": 0}
    _, binding = public_teacher_binding(view(), policy_id="p", learning_step=0)
    provider.assess = lambda *a, **k: {"schema_version": PUBLIC_VERSION, "binding": binding,
        "status": "abstain", "target": None, "reason": "unsupported", "evidence_scope": "public_only_admission"}
    result = apply_public_teacher_decision(model, encoder, view(), provider, policy_id="p",
        learning_step=0, enabled=True, ledger=None)
    assert result["optimizer_updates"] == 0 and result["status"] == "abstain"
    model.rollout_buffer.pos = 1
    with pytest.raises(ValueError, match="empty_on_policy"):
        apply_public_teacher_decision(model, encoder, view(), provider, policy_id="p",
            learning_step=0, enabled=True, ledger=None)


def test_persistent_combined_budget_fails_before_mutation(tmp_path):
    ledger = MicroLedger(tmp_path / "ledger.jsonl")
    ledger.reserve("teacher_Adam", 1)
    ledger.reserve("PPO_Adam", 255)
    restored = MicroLedger(ledger.path)
    assert restored.counts["Adam"] == 256
    with pytest.raises(ValueError, match="exhausted"): restored.reserve("contract_test_Adam", 1)
    assert len(ledger.path.read_text().splitlines()) == 2
