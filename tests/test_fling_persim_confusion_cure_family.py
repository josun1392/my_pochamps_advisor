from advisor.canonical_fling_persim_confusion_cure_berry import (
    EXPECTED_ITEMS_SHA256,
    resolve_canonical_fling_persim_confusion_cure_berry,
)
from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import _fixture


def test_persim_canonical_owner_binds_exact_pinned_confusion_cure():
    result = resolve_canonical_fling_persim_confusion_cure_berry("persim-berry")
    assert result["status"] == "resolved"
    assert result["item_id"] == "persim-berry"
    assert result["showdown_item_id"] == "persimberry"
    assert result["fling_base_power"] == 10
    assert result["effect_family"] == "persim_confusion_cure"
    assert result["intrinsic_on_eat"] == "remove_confusion_volatile"
    source = result["source_provenance"]
    assert source["commit_sha"] == "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
    assert source["sha256"] == EXPECTED_ITEMS_SHA256
    assert source["held_update_trigger"] == "confusion_present_then_eat_item"
    assert source["intrinsic_on_eat"] == "remove_confusion_volatile"


def test_non_persim_berries_do_not_resolve_through_persim_owner():
    for item in ("lum-berry", "cheri-berry", "colbur-berry", "oran-berry", "sitrus-berry", "leppa-berry"):
        assert resolve_canonical_fling_persim_confusion_cure_berry(item)["status"] == "not_applicable"


def test_exact_persim_is_admitted_as_10_bp_ready_throw_only_by_persim_support():
    _state, _snapshot, _d0, _actor, _target, execution = _fixture(item="persim-berry")
    assert execution["status"] == "resolved"
    assert execution["outcome"] == "ready_throw"
    assert execution["resolved_base_power"] == 10
    assert execution["fling_persim_confusion_cure_berry_support"] == "fling_persim_confusion_cure_target_effect_v1"
    assert execution["fling_persim_confusion_cure_berry_authority"]["item_id"] == "persim-berry"
    assert "fling_major_status_cure_berry_support" not in execution
    assert "fling_type_resist_empty_intrinsic_berry_support" not in execution


def test_remaining_bounded_berries_stay_unsupported():
    for item in ("leppa-berry",):
        _state, _snapshot, _d0, _actor, _target, execution = _fixture(item=item)
        assert execution["status"] == "unsupported"
        assert execution["outcome"] == "unsupported_mandatory_item_effect"
