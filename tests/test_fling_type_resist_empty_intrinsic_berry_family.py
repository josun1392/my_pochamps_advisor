import pytest

from advisor.canonical_fling_type_resist_empty_intrinsic_berry import (
    EXPECTED_ITEMS_SHA256,
    canonical_fling_type_resist_empty_intrinsic_berry_ids,
    resolve_canonical_fling_type_resist_empty_intrinsic_berry,
)
from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import _fixture


FAMILY = (
    "babiri-berry", "charti-berry", "chilan-berry", "chople-berry",
    "coba-berry", "colbur-berry", "haban-berry", "kasib-berry",
    "kebia-berry", "occa-berry", "passho-berry", "payapa-berry",
    "rindo-berry", "roseli-berry", "shuca-berry", "tanga-berry",
    "wacan-berry", "yache-berry",
)


def test_family_inventory_is_exactly_the_18_requested_berries():
    assert canonical_fling_type_resist_empty_intrinsic_berry_ids() == FAMILY
    assert len(set(FAMILY)) == 18


@pytest.mark.parametrize("item_id", FAMILY)
def test_each_family_member_binds_pinned_empty_on_eat_and_10_bp_execution(item_id):
    family = resolve_canonical_fling_type_resist_empty_intrinsic_berry(item_id)
    assert family["status"] == "resolved"
    assert family["item_id"] == item_id
    assert family["showdown_item_id"] == item_id.replace("-", "")
    assert family["effect_family"] == "type_resist_empty_intrinsic"
    assert family["fling_base_power"] == 10
    assert family["is_berry"] is True
    assert family["intrinsic_on_eat"] == "empty"
    assert family["held_resist_hook_present"] is True
    assert family["source_item_proof"] == {
        "upstream_item_id": item_id.replace("-", ""),
        "is_berry": True,
        "held_resist_hook_present": True,
        "intrinsic_on_eat": "empty",
    }
    source = family["source_provenance"]
    assert source["commit_sha"] == "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
    assert source["source_path"] == "data/items.ts"
    assert source["sha256"] == EXPECTED_ITEMS_SHA256
    metadata = family["fling_item_metadata"]
    assert metadata["base_power"] == 10
    assert metadata["effect"]["kind"] == "berry_effect"
    assert metadata["support_status"] == "unsupported_now"

    _state, _snapshot, _d0, _actor, _target, execution = _fixture(item=item_id)
    assert execution["status"] == "resolved"
    assert execution["outcome"] == "ready_throw"
    assert execution["resolved_base_power"] == 10
    assert execution["fling_type_resist_empty_intrinsic_berry_support"] == (
        "fling_type_resist_empty_intrinsic_berry_target_effect_v1"
    )
    assert execution["fling_type_resist_empty_intrinsic_berry_authority"] == family
    assert "fling_major_status_cure_berry_support" not in execution


@pytest.mark.parametrize(
    "item_id",
    ["cheri-berry", "persim-berry", "lum-berry", "oran-berry", "sitrus-berry", "leppa-berry"],
)
def test_non_family_berries_are_not_admitted_by_this_family_owner(item_id):
    assert resolve_canonical_fling_type_resist_empty_intrinsic_berry(item_id)["status"] == "not_applicable"


def test_still_unsupported_non_family_berry_does_not_become_ready_throw():
    _state, _snapshot, _d0, _actor, _target, execution = _fixture(item="persim-berry")
    assert execution["outcome"] == "unsupported_mandatory_item_effect"
    assert execution["status"] == "unsupported"
    assert "fling_type_resist_empty_intrinsic_berry_support" not in execution
