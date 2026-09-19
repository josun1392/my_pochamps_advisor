from advisor.canonical_fling_leppa_pp_restore_berry import (
    resolve_canonical_fling_leppa_pp_restore_berry,
)
from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import _fixture, _leaf
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    freeze_runtime_d0_fling_berry_eat_item_interaction_authority,
)


def test_only_leppa_resolves_with_exact_pinned_contract():
    leppa = resolve_canonical_fling_leppa_pp_restore_berry("leppa-berry")
    assert leppa["status"] == "resolved"
    assert leppa["showdown_item_id"] == "leppaberry"
    assert leppa["fling_base_power"] == 10
    assert leppa["ordinary_restore_amount"] == 10
    assert leppa["ripen_restore_amount"] == 20
    assert leppa["selection_priority"] == ("first_zero_pp", "first_missing_pp")
    assert leppa["ordinary_held_zero_pp_trigger_applies_to_fling_target_eat"] is False
    assert leppa["external_staleness"] == {
        "value": True,
        "source": "fling_leppa_successful_target_eat",
        "timing": "after_target_eat_item_dispatch",
    }
    source = leppa["source_provenance"]
    assert source["items_sha256"] == "b8ec6ef48590402e83502902f5205a798c02a72f35d710d35cd30902e08c3f4e"
    assert source["moves_sha256"] == "1ded02b7fda2e4cfcc28ad753190f83c3db3ac5947d2825c2663e66d8ce83d6b"
    for other in ("oran-berry", "sitrus-berry", "lum-berry", "persim-berry", "liechi-berry"):
        assert resolve_canonical_fling_leppa_pp_restore_berry(other)["status"] == "not_applicable"


def test_leppa_is_exact_10_bp_ready_throw_with_one_family_marker():
    _state, _snapshot, _d0, _actor, _target, execution = _fixture(item="leppa-berry")
    assert execution["status"] == "resolved"
    assert execution["outcome"] == "ready_throw"
    assert execution["resolved_base_power"] == 10
    assert execution["fling_leppa_pp_restore_support"] == "fling_leppa_pp_restore_target_effect_v1"
    assert execution["fling_leppa_pp_restore_berry_authority"]["item_id"] == "leppa-berry"
    assert all(
        execution.get(key) is None
        for key in (
            "fling_major_status_cure_berry_support",
            "fling_type_resist_empty_intrinsic_berry_support",
            "fling_persim_confusion_cure_berry_support",
            "fling_lum_major_status_confusion_cure_support",
            "fling_hp_restore_berry_support",
        )
    )


def test_source_klutz_and_magic_room_fail_before_leppa_target_eat():
    for fixture, expected in (
        (_fixture(item="leppa-berry", source_ability="klutz"), "failed_klutz"),
        (_fixture(item="leppa-berry", magic_room="active"), "failed_item_suppressed"),
    ):
        _state, snapshot, d0, actor, target, execution = fixture
        assert execution["status"] == "resolved"
        assert execution["outcome"] == expected
        leaf = _leaf(d0, actor, target, execution)
        interaction = freeze_runtime_d0_fling_berry_eat_item_interaction_authority(
            strategy_d0=d0,
            runtime_snapshot=snapshot,
            fling_execution_authority=execution,
            actor=actor,
            target=target,
            phase="post_hit_target_berry_interaction",
            source_leaf=leaf,
        )
        assert interaction["status"] == "resolved"
        assert interaction["target_eat_occurred"] is False
        assert interaction["target_eat_item_dispatched"] is False
