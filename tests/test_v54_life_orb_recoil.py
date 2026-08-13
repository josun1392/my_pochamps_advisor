"""Bounded trusted-event Life Orb recoil regressions."""

from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    CURRENT_ABILITY_SOURCE,
    HP_TRANSITION_SOURCE,
    SAME_TURN_EVENT_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection


def _manager(*, hp=80, maximum=100, item="life-orb", fainted=False):
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    state["self_side"]["pokemon"][0].update(current_hp=hp, max_hp=maximum, known_item=item, fainted=fainted)
    state["opponent_side"]["pokemon"][0].update(current_hp=80, max_hp=100, known_item=None, fainted=False)
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _boundary():
    return LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})


def _apply(manager, confirmation):
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def _ability(boundary, side, pokemon_id, ability, turn=4):
    return boundary.confirm(event_kind="current_ability_observed", payload={"ability": ability}, session_id="s", source=CURRENT_ABILITY_SOURCE, trust=USER_TRUST, confirmed=True, side=side, slot_index=0, pokemon_id=pokemon_id, turn_number=turn)


def _qualifying_hit(boundary, *, occurred=True, target=("opponent", "eevee"), turn=4):
    return boundary.confirm(event_kind="same_turn_event_observed", payload={"predicate": "qualifying_direct_damage_dealt", "occurred": occurred, "target_side": target[0], "target_slot_index": 0, "target_pokemon_id": target[1]}, session_id="s", source=SAME_TURN_EVENT_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=turn)


def _hp(boundary, before, after, turn=4):
    return boundary.confirm(event_kind="exact_hp_transition_observed", payload={"hp_before": before, "hp_after": after}, session_id="s", source=HP_TRANSITION_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=turn)


def _known_abilities(manager, boundary, *, self_ability="pressure", opponent_ability="pressure"):
    _apply(manager, _ability(boundary, "self", "pikachu", self_ability))
    _apply(manager, _ability(boundary, "opponent", "eevee", opponent_ability))


def _result(manager):
    return manager.read_state()["state"]["life_orb_recoil_context"][-1]


def test_qualifying_damage_event_applies_one_canonical_life_orb_recoil_and_detaches_projection():
    manager, boundary = _manager(), _boundary()
    _known_abilities(manager, boundary)
    _apply(manager, _qualifying_hit(boundary))
    result = _result(manager)
    assert result["outcome"] == "recoiled" and result["recoil"] == 10 and result["post_hp"] == 70
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 70
    projection = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    frozen = deepcopy(projection)
    _apply(manager, _hp(boundary, 70, 60))
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 60
    assert frozen["self"]["active_pokemon"]["current_hp"] == {"status": "known", "value": 70}


def test_life_orb_recoil_can_reduce_authoritative_hp_to_zero_without_inventing_faint_observation():
    manager, boundary = _manager(hp=9), _boundary()
    _known_abilities(manager, boundary)
    _apply(manager, _qualifying_hit(boundary))
    result = _result(manager)
    pokemon = manager.read_state()["state"]["self_side"]["pokemon"][0]
    assert result["guaranteed_faint"] is True and pokemon["current_hp"] == 0 and pokemon["fainted"] is False


def test_false_or_unknown_qualifying_event_never_assumes_life_orb_recoil():
    false_manager, boundary = _manager(), _boundary()
    _apply(false_manager, _qualifying_hit(boundary, occurred=False))
    assert _result(false_manager)["outcome"] == "not_triggered"
    assert false_manager.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 80

    unknown_manager = _manager()
    assert unknown_manager.read_state()["state"].get("life_orb_recoil_context", []) == []
    assert unknown_manager.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 80


def test_life_orb_requires_matching_identity_turn_and_relevant_suppression_authority():
    manager, boundary = _manager(), _boundary()
    wrong_target = _qualifying_hit(boundary, target=("self", "pikachu"))
    assert wrong_target["status"] == "invalid_provenance" and wrong_target["excluded_reason"] == "target_must_differ_from_subject"
    _apply(manager, _qualifying_hit(boundary, turn=4))
    assert _result(manager)["status"] == "incomplete" and _result(manager)["reason"] == "current_ability_unknown"

    magic_guard, boundary = _manager(), _boundary()
    _known_abilities(magic_guard, boundary, self_ability="magic-guard")
    _apply(magic_guard, _qualifying_hit(boundary))
    assert _result(magic_guard)["outcome"] == "prevented_by_magic_guard"

    sheer_force, boundary = _manager(), _boundary()
    _known_abilities(sheer_force, boundary, self_ability="sheer-force")
    _apply(sheer_force, _qualifying_hit(boundary))
    assert _result(sheer_force)["reason"] == "sheer_force_move_applicability_unknown"


def test_life_orb_event_expires_from_current_turn_projection_and_non_holder_is_unchanged():
    manager, boundary = _manager(item="leftovers"), _boundary()
    _known_abilities(manager, boundary)
    _apply(manager, _qualifying_hit(boundary))
    state = manager.read_state()["state"]
    assert state.get("life_orb_recoil_context", []) == []
    assert state["self_side"]["pokemon"][0]["current_hp"] == 80
    projection = build_runtime_advice_state_projection(state)["runtime_advice_state"]
    assert projection["field"]["same_turn_events"][0]["turn_number"] == 4
