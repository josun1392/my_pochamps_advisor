"""Typed Aqua Ring authority and tier-six detached EOT coverage."""
from copy import deepcopy

from llm.advisor_aqua_ring_persistent_effect import apply_owner_aqua_ring_end_of_turn
from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_per_owner_eot import project_cross_owner_weather_end_of_turn, project_per_owner_end_of_turn
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_leftovers_end_of_turn import _owner_id, _pre, _projection


def _aqua(state, self_state="known_active", opponent_state="known_inactive"):
    owners = [_owner_id(state, side) for side in ("self", "opponent")]
    state["aqua_ring_persistent_effect_context"] = {"schema_version": "detached-aqua-ring-persistent-effect-v1", "session_id": owners[0]["session_id"], "source_branch_fingerprint": "trusted-pre-materialized-branch", "provenance": "trusted_aqua_ring_persistent_effect_state", "states": [{"owner": owners[0], "state": self_state}, {"owner": owners[1], "state": opponent_state}]}


def _weather_projection(pre):
    state=pre["next_state"]
    return {"schema_version":"detached-weather-event-target-order-v1","status":"known","session_id":"leftovers-eot","event_family":"Weather","source_branch_fingerprint":fingerprint_transition_preview_state(state),"ordered_active_owners":[_owner_id(state, side) for side in ("self","opponent")],"provenance":"trusted_canonical_showdown_weather_event_target_order"}


def _aqua_projection(state, sides=("self", "opponent")):
    return {"schema_version":"detached-aqua-ring-target-order-v1","status":"known","session_id":"leftovers-eot","event_family":"ResidualAquaRingTier6","source_branch_fingerprint":fingerprint_transition_preview_state(state),"ordered_active_owners":[_owner_id(state, side) for side in sides],"provenance":"trusted_canonical_showdown_aqua_ring_residual_target_order"}


def test_aqua_ring_recovers_then_poison_consumes_current_hp_and_handoff_persists_state():
    pre=_pre(self_hp=50,self_item="leftovers",self_condition="poison"); _aqua(pre["next_state"])
    result=project_per_owner_end_of_turn(pre_end_of_turn=pre,owner=_owner_id(pre["next_state"],"self"))
    assert result["status"] == "resolved", result
    assert [(r["tier"],r["effect"]) for r in result["eot_consequence_trace"]] == [(5,"leftovers_recovery"),(6,"aqua_ring_recovery"),(9,"poison_residual")]
    assert [r["post_hp"] for r in result["eot_consequence_trace"]] == [56,62,50]
    handoff=handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=result)
    assert handoff["status"] == "resolved" and handoff["next_state"]["aqua_ring_persistent_effect_context"]["states"][0]["state"] == "known_active" and handoff["next_state"]["aqua_ring_persistent_effect_context"]["source_branch_fingerprint"] == result["resulting_branch_fingerprint"]


def test_aqua_ring_full_unknown_foreign_and_fainted_boundaries():
    pre=_pre(self_hp=100,self_condition="none"); _aqua(pre["next_state"])
    result=project_per_owner_end_of_turn(pre_end_of_turn=pre,owner=_owner_id(pre["next_state"],"self"))
    assert result["eot_consequence_trace"][0]["outcome"] == "already_full_hp"
    unknown=_pre(self_condition="none"); _aqua(unknown["next_state"],self_state="unknown")
    assert project_per_owner_end_of_turn(pre_end_of_turn=unknown,owner=_owner_id(unknown["next_state"],"self")) == {"status":"incomplete","reason":"aqua_ring_persistent_effect_unknown"}
    stale=deepcopy(pre["next_state"]); owner=_owner_id(stale,"self")
    assert apply_owner_aqua_ring_end_of_turn(state=stale,side="self",owner={**owner,"pokemon_id":"foreign"},source_branch_fingerprint=fingerprint_transition_preview_state(stale)) == {"status":"rejected","reason":"stale_or_foreign_aqua_ring_owner"}
    fainted=_pre(self_hp=0,self_condition="none"); _aqua(fainted["next_state"])
    assert apply_owner_aqua_ring_end_of_turn(state=fainted["next_state"],side="self",owner=_owner_id(fainted["next_state"],"self"),source_branch_fingerprint=fingerprint_transition_preview_state(fainted["next_state"])) == {"status":"rejected","reason":"aqua_ring_fainted_owner"}


def test_cross_owner_aqua_ring_requires_trusted_order_and_manual_materialization_does_not_transfer():
    pre=_pre(self_item=None,opponent_item=None,self_condition="none",opponent_condition="none"); _aqua(pre["next_state"],opponent_state="known_active")
    result=project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre,weather_event_target_order=_weather_projection(pre),leftovers_event_target_order=_projection(pre),aqua_ring_target_order=_aqua_projection(pre["next_state"],("opponent","self")))
    assert result["status"] == "resolved", result
    rows=[r for r in result["eot_consequence_trace"] if r["effect"]=="aqua_ring_recovery"]
    assert [r["owner"]["side"] for r in rows] == ["opponent","self"] and rows[1]["branch_fingerprint_consumed"] != rows[0]["branch_fingerprint_consumed"]
    assert project_cross_owner_weather_end_of_turn(pre_end_of_turn=pre,weather_event_target_order=_weather_projection(pre),leftovers_event_target_order=_projection(pre),aqua_ring_target_order=None) == {"status":"incomplete","reason":"cross_owner_aqua_ring_order_unrepresented"}
    source=pre["next_state"]; incoming={"provenance":"identity_bound_incoming_current_state_v1","owner":{"session_id":"leftovers-eot","side":"self","slot_index":1,"pokemon_id":"incoming"},"hp_authority":{"status":"known","current_hp":50,"maximum_hp":100},"fainted_authority":{"status":"known","value":False},"current_state":deepcopy(source["current_state"])}
    switched=materialize_incoming_active_branch(source_branch=source,source_branch_fingerprint=fingerprint_transition_preview_state(source),incoming_authority=incoming)
    assert switched["status"] == "resolved" and "aqua_ring_persistent_effect_context" not in switched["next_state"]
