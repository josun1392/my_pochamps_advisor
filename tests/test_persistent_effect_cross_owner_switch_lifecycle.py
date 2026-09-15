"""Identity-scoped persistent-effect lifecycle through incoming materialization."""
from copy import deepcopy

from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_persistent_effect_authority import materialize_persistent_effect_authority
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_aqua_ring_detached_eot import _aqua
from tests.test_ingrain_detached_eot import _ingrain
from tests.test_leech_seed_detached_eot import _seed
from tests.test_leftovers_end_of_turn import _owner_id, _pre


_CONTEXT_KEYS = {
    "aqua_ring": "aqua_ring_persistent_effect_context",
    "ingrain": "ingrain_persistent_effect_context",
    "leech_seed": "leech_seed_persistent_effect_context",
}


def _switch(source, side):
    owner = {
        "session_id": "leftovers-eot", "side": side, "slot_index": 1,
        "pokemon_id": f"{side}-incoming",
    }
    incoming = {
        "provenance": "identity_bound_incoming_current_state_v1", "owner": owner,
        "hp_authority": {"status": "known", "current_hp": 50, "maximum_hp": 100},
        "fainted_authority": {"status": "known", "value": False},
        "current_state": deepcopy(source["current_state"]),
    }
    return materialize_incoming_active_branch(
        source_branch=source,
        source_branch_fingerprint=fingerprint_transition_preview_state(source),
        incoming_authority=incoming,
    ), incoming


def _row(state, family, owner):
    return next(row for row in state[_CONTEXT_KEYS[family]]["states"] if row["owner"] == owner)


def _bundle_row(state, family, owner):
    return next(row for row in state["branch_persistent_effect_authority"]["states"] if row["family"] == family and row["owner"] == owner)


def test_aqua_ring_survives_other_side_switch_but_retires_on_its_own_switch_without_transfer():
    source = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    _aqua(source, self_state="known_inactive", opponent_state="known_active")
    result, incoming = _switch(source, "self")
    assert result["status"] == "resolved"
    next_state = result["next_state"]
    assert _row(next_state, "aqua_ring", _owner_id(source, "opponent"))["state"] == "known_active"
    assert _row(next_state, "aqua_ring", incoming["owner"])["state"] == "known_inactive"

    source = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    _aqua(source, self_state="known_active", opponent_state="known_inactive")
    result, incoming = _switch(source, "self")
    assert result["status"] == "resolved"
    assert _row(result["next_state"], "aqua_ring", incoming["owner"])["state"] == "known_inactive"

    source = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    _aqua(source, self_state="known_active", opponent_state="known_inactive")
    result, incoming = _switch(source, "opponent")
    assert result["status"] == "resolved"
    assert _row(result["next_state"], "aqua_ring", _owner_id(source, "self"))["state"] == "known_active"
    assert _row(result["next_state"], "aqua_ring", incoming["owner"])["state"] == "known_inactive"


def test_ingrain_survives_other_side_switch_and_retires_only_its_own_owner_row():
    source = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    _ingrain(source, self_state="known_inactive", opponent_state="known_active")
    result, incoming = _switch(source, "self")
    assert result["status"] == "resolved"
    assert _row(result["next_state"], "ingrain", _owner_id(source, "opponent"))["state"] == "known_active"
    assert _row(result["next_state"], "ingrain", incoming["owner"])["state"] == "known_inactive"

    source = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    _ingrain(source, self_state="known_active", opponent_state="known_inactive")
    result, incoming = _switch(source, "self")
    assert result["status"] == "resolved"
    assert _row(result["next_state"], "ingrain", incoming["owner"])["state"] == "known_inactive"

    source = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    _ingrain(source, self_state="known_active", opponent_state="known_inactive")
    result, incoming = _switch(source, "opponent")
    assert result["status"] == "resolved"
    assert _row(result["next_state"], "ingrain", _owner_id(source, "self"))["state"] == "known_active"
    assert _row(result["next_state"], "ingrain", incoming["owner"])["state"] == "known_inactive"


def test_leech_seed_is_target_owned_and_source_switch_preserves_target_and_source_slot():
    source = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    _seed(source, target="self", source="opponent")
    seeded_owner = _owner_id(source, "self")
    original = _row(source, "leech_seed", seeded_owner)["source_slot"]
    result, incoming = _switch(source, "opponent")
    assert result["status"] == "resolved"
    retained = _row(result["next_state"], "leech_seed", seeded_owner)
    assert retained["state"] == "known_active" and retained["source_slot"] == original
    assert _row(result["next_state"], "leech_seed", incoming["owner"])["state"] == "known_inactive"

    result, incoming = _switch(source, "self")
    assert result["status"] == "resolved"
    retired = _row(result["next_state"], "leech_seed", incoming["owner"])
    assert retired["state"] == "known_inactive" and "source_slot" not in retired

    source = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    _seed(source, target="opponent", source="self")
    seeded_owner = _owner_id(source, "opponent")
    result, incoming = _switch(source, "self")
    assert result["status"] == "resolved"
    retained = _row(result["next_state"], "leech_seed", seeded_owner)
    assert retained["state"] == "known_active" and retained["source_slot"]["side"] == "self"
    assert _row(result["next_state"], "leech_seed", incoming["owner"])["state"] == "known_inactive"


def test_cross_effect_rows_keep_unrelated_owners_and_branch_authority_in_sync():
    source = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    _aqua(source, self_state="known_active", opponent_state="known_inactive")
    _ingrain(source, self_state="known_active", opponent_state="known_inactive")
    _seed(source, target="opponent", source="self")
    owners = {side: _owner_id(source, side) for side in ("self", "opponent")}
    states = {
        "self": {
            "aqua_ring": {"state": "known_active"}, "ingrain": {"state": "known_active"},
            "leech_seed": {"state": "known_inactive"},
        },
        "opponent": {
            "aqua_ring": {"state": "known_inactive"}, "ingrain": {"state": "known_inactive"},
            "leech_seed": {"state": "known_active", "source_slot": {"session_id": "leftovers-eot", "side": "self", "slot_index": 0}},
        },
    }
    source["branch_persistent_effect_authority"] = materialize_persistent_effect_authority(
        owners=owners, source_branch_fingerprint="trusted-cross-owner", states=states,
    )
    result, incoming = _switch(source, "self")
    assert result["status"] == "resolved"
    next_state = result["next_state"]
    opponent = owners["opponent"]
    assert _row(next_state, "aqua_ring", opponent)["state"] == "known_inactive"
    assert _row(next_state, "ingrain", opponent)["state"] == "known_inactive"
    assert _row(next_state, "leech_seed", opponent)["state"] == "known_active"
    assert _bundle_row(next_state, "leech_seed", opponent)["source_slot"] == states["opponent"]["leech_seed"]["source_slot"]
    assert all(_bundle_row(next_state, family, incoming["owner"])["state"] == "known_inactive" for family in _CONTEXT_KEYS)


def test_malformed_persistent_ownership_rejects_without_mutating_source_and_replay_is_deterministic():
    source = _pre(self_item=None, opponent_item=None, self_condition="none", opponent_condition="none")["next_state"]
    _aqua(source, self_state="known_inactive", opponent_state="known_active")
    before = deepcopy(source)
    first, _ = _switch(source, "self")
    second, _ = _switch(source, "self")
    assert first == second and source == before

    malformed = deepcopy(source)
    malformed["aqua_ring_persistent_effect_context"]["states"].append(deepcopy(malformed["aqua_ring_persistent_effect_context"]["states"][1]))
    result, _ = _switch(malformed, "self")
    assert result == {"status": "rejected", "reason": "invalid_aqua_ring_persistent_effect_context_on_switch"}
