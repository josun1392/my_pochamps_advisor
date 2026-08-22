from copy import deepcopy

from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_observed_direct_damage import materialize_observed_direct_damage_result
from llm.advisor_observed_life_orb_consequence import materialize_observed_life_orb_post_hit
from llm.advisor_per_owner_eot import project_per_owner_end_of_turn
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_leftovers_end_of_turn import _pre


def _owner(state, side):
    return {key: state["active"][side][key] for key in ("session_id", "side", "slot_index", "pokemon_id")}


def _damage_observation(state, side="self", target="opponent", damage=20, **overrides):
    user, target_owner = _owner(state, side), _owner(state, target)
    value = {
        "schema_version": "observed-direct-damage-result-v1", "session_id": user["session_id"],
        "source_branch_fingerprint": fingerprint_transition_preview_state(state), "user": user,
        "target_owner": target_owner, "move_id": "water-gun", "damage_amount": damage,
        "damaging_hit_result": "applied", "provenance": "trusted_observed_direct_damage_result_v1",
    }
    value.update(overrides)
    return value


def _life_orb_observation(damage, category="special", qualifying="qualifying", **overrides):
    source = damage["observed_direct_damage_result"]
    value = {
        "schema_version": "observed-life-orb-post-hit-result-v1", "session_id": source["session_id"],
        "source_branch_fingerprint": damage["resulting_branch_fingerprint"], "user": source["user"],
        "target_owner": source["target_owner"], "move_id": "water-gun", "move_category": category,
        "qualifying_hit_result": qualifying, "provenance": "trusted_observed_life_orb_post_hit_v1",
    }
    value.update(overrides)
    return value


def _damage(state, **kwargs):
    return materialize_observed_direct_damage_result(
        branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state),
        observed_result=_damage_observation(state, **kwargs),
    )


def _life_orb(f1, damage, observation=None):
    return materialize_observed_life_orb_post_hit(
        branch_state=f1, source_branch_fingerprint=fingerprint_transition_preview_state(f1),
        observed_result=_life_orb_observation(damage) if observation is None else observation,
        preceding_damage_result=damage,
    )


def test_life_orb_f0_f1_f2_side_neutral_target_ko_and_attacker_ko():
    state = _pre(self_hp=50, self_item="life-orb", self_condition="none", opponent_condition="none")["next_state"]
    baseline = deepcopy(state); damage = _damage(state); result = _life_orb(damage["next_state"], damage)
    assert state == baseline and result["status"] == "resolved"
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 60
    assert result["next_state"]["active"]["self"]["current_hp"] == 40
    reverse_state = _pre(self_item=None, opponent_item="life-orb", self_condition="none", opponent_condition="none")["next_state"]
    reverse_damage = _damage(reverse_state, side="opponent", target="self")
    reverse = _life_orb(reverse_damage["next_state"], reverse_damage, _life_orb_observation(reverse_damage, category="physical"))
    assert reverse["status"] == "resolved" and reverse["next_state"]["active"]["opponent"]["current_hp"] == 70
    ko_state = _pre(self_hp=10, self_item="life-orb", self_condition="none", opponent_condition="none")["next_state"]
    ko_damage = _damage(ko_state, damage=80); ko = _life_orb(ko_damage["next_state"], ko_damage)
    assert ko["next_state"]["active"]["opponent"]["fainted"] and ko["next_state"]["active"]["self"]["fainted"]


def test_life_orb_magic_guard_known_non_trigger_and_unknown_are_distinct():
    magic = _pre(self_item="life-orb", self_ability="magic-guard", self_condition="none", opponent_condition="none")["next_state"]
    damage = _damage(magic); stopped = _life_orb(damage["next_state"], damage)
    assert stopped["status"] == "resolved" and stopped["life_orb"] == "not_triggered" and stopped["reason"] == "suppressed_by_magic_guard"
    non_holder = _pre(self_item="leftovers", self_condition="none", opponent_condition="none")["next_state"]
    damage = _damage(non_holder); stopped = _life_orb(damage["next_state"], damage)
    assert stopped["status"] == "resolved" and stopped["reason"] == "known_non_life_orb"
    unknown = _pre(self_item="life-orb", self_condition="none", opponent_condition="none")["next_state"]
    unknown["current_state"]["direct_mechanics_context"]["attacker"]["item"] = {"status": "unknown"}
    damage = _damage(unknown)
    assert _life_orb(damage["next_state"], damage) == {"status": "incomplete", "reason": "life_orb_current_item_unknown"}
    sheer_force = _pre(self_item="life-orb", self_ability="sheer-force", self_condition="none", opponent_condition="none")["next_state"]
    damage = _damage(sheer_force); normal = _life_orb(damage["next_state"], damage)
    assert normal["status"] == "resolved" and normal["life_orb_application"]["recoil"] == 10
    missing_target_ability = _pre(self_item="life-orb", self_ability="magic-guard", self_condition="none", opponent_condition="none")["next_state"]
    missing_target_ability["current_state"]["ability_context"]["current_abilities"] = missing_target_ability["current_state"]["ability_context"]["current_abilities"][:1]
    damage = _damage(missing_target_ability)
    assert _life_orb(damage["next_state"], damage) == {"status": "incomplete", "reason": "life_orb_target_ability_unknown"}


def test_life_orb_replay_handoff_and_fail_closed():
    state = _pre(self_hp=50, self_item="life-orb", self_condition="none", opponent_condition="none")["next_state"]
    damage = _damage(state); observation = _life_orb_observation(damage); result = _life_orb(damage["next_state"], damage, observation)
    assert _life_orb(result["next_state"], damage, observation)["status"] == "rejected"
    eot = project_per_owner_end_of_turn(pre_end_of_turn={"status": "resolved", "next_state": result["next_state"], "boundary": {"phase": "pre_end_of_turn"}}, owner=_owner(result["next_state"], "self"))
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)["next_state"]
    assert _life_orb(handoff, damage, observation)["status"] == "rejected"
    fresh_damage = _damage(handoff); assert _life_orb(fresh_damage["next_state"], fresh_damage)["status"] == "resolved"
    malformed = _pre(self_item="life-orb", self_condition="none", opponent_condition="none")["next_state"]
    malformed["active"]["self"]["max_hp"] = None
    broken_damage = _damage(malformed)
    assert _life_orb(broken_damage["next_state"], broken_damage)["status"] == "incomplete"
    foreign = _life_orb_observation(damage, user={**observation["user"], "pokemon_id": "foreign"})
    assert _life_orb(damage["next_state"], damage, foreign)["status"] == "rejected"
