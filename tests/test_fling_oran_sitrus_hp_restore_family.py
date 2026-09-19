from advisor.canonical_fling_hp_restore_berry import (
    nominal_fling_hp_restore_amount,
    resolve_canonical_fling_hp_restore_berry,
)


def test_oran_and_sitrus_resolve_and_leppa_does_not():
    oran = resolve_canonical_fling_hp_restore_berry("oran-berry")
    sitrus = resolve_canonical_fling_hp_restore_berry("sitrus-berry")
    leppa = resolve_canonical_fling_hp_restore_berry("leppa-berry")
    assert oran["status"] == sitrus["status"] == "resolved"
    assert leppa["status"] == "not_applicable"
    assert oran["fling_base_power"] == sitrus["fling_base_power"] == 10
    assert oran["heal_family"] == "fixed_hp"
    assert sitrus["heal_family"] == "quarter_base_max_hp"


def test_pinned_source_and_battle_heal_contract():
    oran = resolve_canonical_fling_hp_restore_berry("oran-berry")
    sitrus = resolve_canonical_fling_hp_restore_berry("sitrus-berry")
    assert oran["source_provenance"] == sitrus["source_provenance"]
    source = oran["source_provenance"]
    assert source["items_sha256"] == "b8ec6ef48590402e83502902f5205a798c02a72f35d710d35cd30902e08c3f4e"
    assert source["battle_sha256"] == "1d413692d0ed518e992593c0644a5456ab5497cbf3baf2542e65d9fba8d054b1"
    assert source["held_update_threshold"] == "hp_le_half_then_eat_item"
    assert source["battle_heal_order"] == "positive_min_one_then_trunc_then_try_heal_then_cap"
    assert oran["ordinary_held_threshold_applies_to_fling_target_eat"] is False
    assert sitrus["ordinary_held_threshold_applies_to_fling_target_eat"] is False


def test_exact_nominal_heal_math():
    oran = resolve_canonical_fling_hp_restore_berry("oran-berry")
    sitrus = resolve_canonical_fling_hp_restore_berry("sitrus-berry")
    assert nominal_fling_hp_restore_amount(family=oran, maximum_hp=100) == 10
    assert nominal_fling_hp_restore_amount(family=oran, maximum_hp=3) == 10
    assert nominal_fling_hp_restore_amount(family=sitrus, maximum_hp=100) == 25
    assert nominal_fling_hp_restore_amount(family=sitrus, maximum_hp=101) == 25
    assert nominal_fling_hp_restore_amount(family=sitrus, maximum_hp=3) == 1


def test_fling_execution_admits_oran_sitrus_exclusively_and_leppa_remains_unsupported():
    from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import _fixture

    for item in ("oran-berry", "sitrus-berry"):
        _state, _snapshot, _d0, _actor, _target, execution = _fixture(item=item)
        assert execution["status"] == "resolved"
        assert execution["outcome"] == "ready_throw"
        assert execution["resolved_base_power"] == 10
        assert execution["fling_hp_restore_berry_support"] == "fling_hp_restore_berry_target_effect_v1"
        assert execution["fling_hp_restore_berry_authority"]["item_id"] == item
        assert all(
            execution.get(key) is None
            for key in (
                "fling_major_status_cure_berry_support",
                "fling_type_resist_empty_intrinsic_berry_support",
                "fling_persim_confusion_cure_berry_support",
                "fling_lum_major_status_confusion_cure_support",
            )
        )
    _state, _snapshot, _d0, _actor, _target, leppa = _fixture(item="leppa-berry")
    assert leppa["status"] == "unsupported"
    assert leppa["outcome"] == "unsupported_mandatory_item_effect"


def test_source_klutz_and_magic_room_still_fail_before_oran_sitrus_target_eat():
    from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import _fixture, _leaf
    from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
        freeze_runtime_d0_fling_berry_eat_item_interaction_authority,
    )

    for item in ("oran-berry", "sitrus-berry"):
        cases = (
            (_fixture(item=item, source_ability="klutz"), "failed_klutz"),
            (_fixture(item=item, magic_room="active"), "failed_item_suppressed"),
        )
        for fixture, expected in cases:
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
