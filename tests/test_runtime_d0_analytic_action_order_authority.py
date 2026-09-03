from copy import deepcopy

from llm.advisor_runtime_d0_analytic_action_order_authority import (
    freeze_runtime_d0_analytic_action_order_authority,
    valid_runtime_d0_analytic_action_order_authority,
)


def _d0() -> dict:
    self_owner = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}
    opponent = {"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "b"}
    return {"status": "resolved", "session_id": "s", "source_runtime_fingerprint": "runtime", "strategy_preview_fingerprint": "branch", "decision_owner": self_owner, "active_owners": {"self": self_owner, "opponent": opponent}}


def _source(d0: dict, order: str = "opponent_first") -> dict:
    return {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": d0["decision_owner"], "own_action_id": "attack:water-gun", "opponent_action_id": "opponent:move", "own_actor": d0["active_owners"]["self"], "opponent_actor": d0["active_owners"]["opponent"], "order": order}


def test_analytic_authority_uses_exact_order_without_speed_derivation() -> None:
    d0 = _d0()
    value = freeze_runtime_d0_analytic_action_order_authority(
        strategy_d0=d0, attacker=d0["decision_owner"], target=d0["active_owners"]["opponent"],
        own_action_id="attack:water-gun", opponent_action_id="opponent:move", action_order="opponent_first",
        source_action_order_authority=_source(d0),
    )
    assert value["status"] == "resolved"
    assert value["outcome"] == "applicable"
    assert valid_runtime_d0_analytic_action_order_authority(value, strategy_d0=d0, attacker=d0["decision_owner"], target=d0["active_owners"]["opponent"], move_id="water-gun")


def test_analytic_authority_keeps_own_first_inactive_and_rejects_forged_bindings() -> None:
    d0 = _d0()
    value = freeze_runtime_d0_analytic_action_order_authority(
        strategy_d0=d0, attacker=d0["decision_owner"], target=d0["active_owners"]["opponent"],
        own_action_id="attack:water-gun", opponent_action_id="opponent:move", action_order="own_first",
        source_action_order_authority=_source(d0, "own_first"),
    )
    assert value["outcome"] == "not_applicable"
    forged = deepcopy(value); forged["target"] = d0["decision_owner"]
    assert not valid_runtime_d0_analytic_action_order_authority(forged, strategy_d0=d0, attacker=d0["decision_owner"], target=d0["active_owners"]["opponent"], move_id="water-gun")


def test_analytic_authority_accepts_switch_first_as_late_action() -> None:
    d0 = _d0()
    value = freeze_runtime_d0_analytic_action_order_authority(
        strategy_d0=d0, attacker=d0["decision_owner"], target=d0["active_owners"]["opponent"],
        own_action_id="attack:water-gun", opponent_action_id="switch:bench", action_order="opponent_switch_first",
    )
    assert value["status"] == "resolved"
    assert value["outcome"] == "applicable"


def test_analytic_authority_preserves_the_exact_equal_speed_branch() -> None:
    d0 = _d0()
    source = _source(d0, "unresolved_tie")
    value = freeze_runtime_d0_analytic_action_order_authority(
        strategy_d0=d0, attacker=d0["decision_owner"], target=d0["active_owners"]["opponent"],
        own_action_id="attack:water-gun", opponent_action_id="opponent:move", action_order="opponent_first",
        source_action_order_authority=source,
        action_order_branch={"order_branch_id": "equal_speed:opponent_first", "order": "opponent_first", "conditional_probability": {"numerator": 1, "denominator": 2}},
    )
    assert value["status"] == "resolved"
    assert value["action_order_branch"]["conditional_probability"] == {"numerator": 1, "denominator": 2}
