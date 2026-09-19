from advisor.canonical_fling_lum_major_status_confusion_cure_berry import (
    COMMIT,
    resolve_canonical_fling_lum_major_status_confusion_cure_berry,
)
from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import _fixture


def test_lum_resolves_exact_family_and_pinned_source_contract():
    family = resolve_canonical_fling_lum_major_status_confusion_cure_berry("lum-berry")
    assert family["status"] == "resolved"
    assert family["item_id"] == "lum-berry"
    assert family["showdown_item_id"] == "lumberry"
    assert family["is_berry"] is True
    assert family["fling_base_power"] == 10
    assert family["removable_conditions"] == (
        "burn", "poison", "toxic", "paralysis", "sleep", "freeze",
    )
    assert family["intrinsic_on_eat"] == "cure_major_status_and_remove_confusion_volatile"
    assert family["source_provenance"]["commit_sha"] == COMMIT
    assert family["source_provenance"]["source_item_id"] == "lumberry"
    assert family["source_provenance"]["intrinsic_on_eat"] == "cure_status_and_remove_confusion_volatile"


def test_non_lum_berries_are_not_admitted_by_lum_owner():
    for item in (
        "persim-berry", "cheri-berry", "chesto-berry", "aspear-berry",
        "pecha-berry", "rawst-berry", "colbur-berry", "oran-berry",
        "sitrus-berry", "leppa-berry",
    ):
        assert resolve_canonical_fling_lum_major_status_confusion_cure_berry(item)["status"] == "not_applicable"


def test_lum_fling_execution_is_ready_at_exact_10_bp_with_mutually_exclusive_support():
    _state, _snapshot, _d0, _actor, _target, execution = _fixture(item="lum-berry")
    assert execution["status"] == "resolved"
    assert execution["outcome"] == "ready_throw"
    assert execution["resolved_base_power"] == 10
    assert (
        execution["fling_lum_major_status_confusion_cure_support"]
        == "fling_lum_major_status_confusion_cure_target_effect_v1"
    )
    assert execution["fling_lum_major_status_confusion_cure_berry_authority"]["item_id"] == "lum-berry"
    assert "fling_major_status_cure_berry_support" not in execution
    assert "fling_persim_confusion_cure_berry_support" not in execution
    assert "fling_type_resist_empty_intrinsic_berry_support" not in execution
