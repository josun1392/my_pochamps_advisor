"""Focused bindings for the fixed-two-hit read-only runtime view."""
from __future__ import annotations

from copy import deepcopy

from llm.advisor_authenticated_predictive_runtime_view import (
    fixed_two_hit_second_hit_view_inputs,
    freeze_fixed_two_hit_second_hit_runtime_view,
)
from llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization import (
    _base,
    _hit_events,
    _single_hit_metadata,
    materialize_detached_fixed_two_hit_per_hit_predictive_leaves,
)
from tests.test_detached_fixed_two_hit_per_hit_predictive_materialization import _inputs


def _view_fixture():
    state, snapshot, d0, action, execution, _own, _foe = _inputs()
    base = _base(d0, action, execution)
    assert base is not None
    first = _hit_events(
        strategy_d0=d0, runtime_snapshot=snapshot, base=base,
        single_metadata=_single_hit_metadata(execution["move_metadata_authority"]["metadata"]),
        sturdy_survival_authority=None, capture_context=True,
    )
    assert not isinstance(first, dict)
    events, context = first
    source = {**events[0], "hit_index": 1}
    view = freeze_fixed_two_hit_second_hit_runtime_view(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action,
        attacker=base["attacker"], target=base["target"], first_hit=source,
        normal_formula_input=context["normal"], native_damage_context=context["native"],
        attacker_hp_before=base["own_current_hp"], attacker_hp_after=base["own_current_hp"],
        condition_before=base["attacker_condition"], condition_after=base["attacker_condition"],
        focus_sash_consumed=False,
    )
    return state, snapshot, d0, action, base, view


def test_fixed_two_hit_runtime_view_is_authenticated_sparse_and_does_not_mutate_source():
    state, snapshot, d0, action, base, view = _view_fixture()
    before = deepcopy(snapshot)
    assert view["status"] == "resolved", view.get("reason")
    inputs = fixed_two_hit_second_hit_view_inputs(
        view=view, strategy_d0=d0, action=action,
        attacker=base["attacker"], target=base["target"],
    )
    assert inputs["status"] == "resolved", inputs.get("reason")
    assert inputs["branch_state"]["active"][base["target"]["side"]]["current_hp"] == view["overlay"]["current_hp"]
    assert inputs["snapshot_damage_input"]["battle_context"]["current_state"]["direct_mechanics_context"]["defender"]["current_hp"] == view["overlay"]["current_hp"]
    assert snapshot == before and state["opponent_side"]["pokemon"][0]["current_hp"] == 100


def test_fixed_two_hit_runtime_view_rejects_forged_overlay_and_action_binding():
    _state, _snapshot, d0, action, base, view = _view_fixture()
    forged = deepcopy(view)
    forged["overlay"]["current_hp"] -= 1
    assert fixed_two_hit_second_hit_view_inputs(
        view=forged, strategy_d0=d0, action=action,
        attacker=base["attacker"], target=base["target"],
    )["status"] == "rejected"
    wrong_action = {**action, "action_id": "attack:foreign"}
    assert fixed_two_hit_second_hit_view_inputs(
        view=view, strategy_d0=d0, action=wrong_action,
        attacker=base["attacker"], target=base["target"],
    )["status"] == "rejected"


def test_supported_second_hit_uses_view_without_legacy_full_runtime_reconstruction(monkeypatch):
    import llm.advisor_detached_fixed_two_hit_per_hit_predictive_materialization as owner

    _state, snapshot, d0, action, execution, _own, _foe = _inputs()
    legacy_calls = 0

    def legacy_unavailable(**_kwargs):
        nonlocal legacy_calls
        legacy_calls += 1
        raise AssertionError("supported view path must not build a synthetic runtime state")

    monkeypatch.setattr(owner, "_detached_target_hp_view", legacy_unavailable)
    result = materialize_detached_fixed_two_hit_per_hit_predictive_leaves(
        strategy_d0=d0, runtime_snapshot=snapshot, action=action,
        execution_authority=execution,
    )
    assert result["status"] == "evaluable", result.get("reason")
    assert legacy_calls == 0
