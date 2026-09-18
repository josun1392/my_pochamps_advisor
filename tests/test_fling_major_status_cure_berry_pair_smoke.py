from tests.test_runtime_d0_fling_item_execution_authority import _production_fling_pair


def _assert_cured_pair(*, item: str, condition: str) -> None:
    pair, ledger = _production_fling_pair(item=item, target_condition=condition)
    assert pair["status"] == "evaluable", pair.get("reason")
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert pair["schema_version"] == "immediate-move-vs-move-action-pair-v1"
    assert {branch["second_action"]["state"] for branch in pair["terminal_branches"]} == {"executed"}
    assert all(
        branch["first_action_leaf"]["consequences"][
            "fling_major_status_cure_berry_target_effect"
        ]["condition_after"] == "none"
        for branch in pair["terminal_branches"]
    )


def test_cheri_pair_smoke():
    _assert_cured_pair(item="cheri-berry", condition="paralysis")


def test_chesto_pair_smoke():
    _assert_cured_pair(item="chesto-berry", condition="sleep")
