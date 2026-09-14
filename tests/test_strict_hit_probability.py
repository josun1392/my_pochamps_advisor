from copy import deepcopy

import pytest

from advisor.strict_hit_probability import (
    apply_accuracy_evasion_stages,
    apply_accuracy_modifier_q12,
    chain_accuracy_modifier_q12,
)
from llm.advisor_runtime_strategy_d0 import build_runtime_d0_strict_hit_probability_assessment
from tests.test_runtime_hit_modifier_authority import _d0, _hustle, _owner, _snapshot, _state


def _move(*, accuracy=100, category="physical", move_id="tackle"):
    return {"move_id": move_id, "category": category, "accuracy": accuracy}


def _assessment(state, move):
    snapshot, d0 = _d0(state)
    return build_runtime_d0_strict_hit_probability_assessment(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state),
        target=_owner(state, "opponent"), selected_move=move,
    )


def test_gen9_q12_primitives_lock_tie_and_stage_contract():
    assert chain_accuracy_modifier_q12(4095, 2048) == 2048
    assert apply_accuracy_modifier_q12(1, 2048) == 0
    assert apply_accuracy_evasion_stages(80, 1) == 106
    assert apply_accuracy_evasion_stages(80, -1) == 60
    with pytest.raises(ValueError):
        chain_accuracy_modifier_q12(0, 4096)


@pytest.mark.parametrize(
    "move,attacker_stage,target_stage,expected",
    [
        (_move(accuracy=100, category="special"), 0, 0, (4096, 100, 100, 100)),
        (_move(accuracy=80, category="special"), 0, 0, (4096, 80, 80, 80)),
        (_move(accuracy=95, category="special"), 0, 0, (4096, 95, 95, 95)),
        (_move(accuracy=100), 0, 0, (3277, 80, 80, 80)),
        (_move(accuracy=95), 0, 0, (3277, 76, 76, 76)),
        (_move(accuracy=100), 1, 0, (3277, 80, 106, 100)),
        (_move(accuracy=100), 0, 1, (3277, 80, 60, 60)),
        (_move(accuracy=1), -6, 0, (3277, 1, 0, 0)),
    ],
)
def test_strict_runtime_hustle_fixtures_are_exact(move, attacker_stage, target_stage, expected):
    state = _state()
    _hustle(state)
    state["self_side"]["pokemon"][0]["stat_stages"]["accuracy"] = attacker_stage
    state["opponent_side"]["pokemon"][0]["stat_stages"]["evasion"] = target_stage
    result = _assessment(state, move)
    modifier, modified_base, threshold, probability = expected
    assert result["status"] == "resolved"
    assert result["modifier_chain_q12"] == modifier
    assert result["modified_base_accuracy"] == modified_base
    assert result["raw_accuracy_threshold"] == threshold
    assert result["probability_percent"] == probability
    assert result["accuracy_check_only"] is True


def test_hustle_nonphysical_is_explicit_catalog_neutral_not_missing_neutral():
    state = _state()
    _hustle(state)
    result = _assessment(state, _move(accuracy=95, category="special", move_id="water-gun"))
    assert result["status"] == "resolved"
    assert result["modifier_chain_q12"] == 4096
    assert result["modified_base_accuracy"] == result["probability_percent"] == 95


def test_unknown_stage_modifier_and_unsupported_capability_fail_closed():
    state = _state()
    _hustle(state, "unknown")
    assert _assessment(state, _move())["status"] == "incomplete"

    state = _state()
    _hustle(state)
    del state["self_side"]["pokemon"][0]["stat_stages"]["accuracy"]
    stages = _assessment(state, _move())
    assert stages["status"] == "incomplete"
    assert stages["missing_authority"] == ["attacker_accuracy_stage"]

    state = _state()
    pokemon = state["self_side"]["pokemon"][0]
    pokemon.update(current_ability="compound-eyes", current_ability_provenance={"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1})
    unsupported = _assessment(state, _move())
    assert unsupported["status"] == "unsupported"


def test_always_hit_is_an_accuracy_only_bypass_without_stage_or_modifier_authority():
    state = _state()
    result = _assessment(state, {"move_id": "aerial-ace", "always_hit": True})
    assert result["status"] == "resolved"
    assert result["result"] == "always_hit"
    assert result["accuracy_check"] == "bypassed_by_move_metadata"
    assert "raw_accuracy_threshold" not in result


def test_stale_identity_and_detachment_are_rejected_without_runtime_mutation():
    state = _state()
    _hustle(state)
    original = deepcopy(state)
    snapshot, d0 = _d0(state)
    result = build_runtime_d0_strict_hit_probability_assessment(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state),
        target=_owner(state, "opponent"), selected_move=_move(),
    )
    assert result["status"] == "resolved" and state == original

    state["self_side"]["pokemon"][0]["current_ability"] = "changed"
    stale = build_runtime_d0_strict_hit_probability_assessment(
        strategy_d0=d0, runtime_snapshot=_snapshot(state), attacker=_owner(state),
        target=_owner(state, "opponent"), selected_move=_move(),
    )
    assert stale["status"] == "rejected"
    assert build_runtime_d0_strict_hit_probability_assessment(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "opponent"),
        target=_owner(state), selected_move=_move(),
    )["status"] == "rejected"


def _weather(state, value):
    state["field"]["weather"] = value
    state["field"]["weather_provenance"] = {"event_kind":"current_weather_observed","trust":"user_confirmed_observation","turn_number":1}


def _magic_room(state, value):
    state["field"]["magic_room_status"] = value
    state["field"]["magic_room_status_provenance"] = {"event_kind":"magic_room_field_observed","trust":"user_confirmed_observation","turn_number":1,"source_observation_id":"magic-room-1","source_sequence":1}


@pytest.mark.parametrize("move_id,weather,expected", (
    ("thunder", "rain", 100), ("hurricane", "rain", 100), ("blizzard", "snow", 100),
    ("thunder", "sun", 50), ("hurricane", "sun", 50),
))
def test_weather_accuracy_overrides_are_exact(move_id, weather, expected):
    state=_state(); _hustle(state); _weather(state, weather)
    result=_assessment(state, _move(accuracy=70, category="special", move_id=move_id))
    assert result["status"]=="resolved" and result["effective_base_accuracy"]==result["probability_percent"]==expected


def test_weather_accuracy_nontrigger_is_exact_neutral():
    state=_state(); _hustle(state); _weather(state, "none")
    result=_assessment(state, _move(accuracy=70, category="special", move_id="thunder"))
    assert result["status"] == "resolved" and result["probability_percent"] == 70


def test_target_bright_powder_and_ability_accuracy_modifiers_are_exact():
    state=_state(); _hustle(state)
    target=state["opponent_side"]["pokemon"][0]; target["known_item"]="bright-powder"; target["known_item_provenance"]={"event_kind":"current_item_observed","trust":"user_confirmed_observation","turn_number":1,"status":"known"}; _magic_room(state,"inactive")
    bright=_assessment(state, _move(accuracy=100, category="special"))
    assert bright["status"]=="resolved" and bright["probability_percent"]==90
    _magic_room(state,"active")
    assert _assessment(state, _move(accuracy=100, category="special"))["probability_percent"] == 100
    for ability, weather, confusion, expected in (("sand-veil","sandstorm","none",80),("snow-cloak","snow","none",80),("tangled-feet","none","confused",50)):
        state=_state(); _hustle(state); _weather(state,weather); target=state["opponent_side"]["pokemon"][0]
        target.update(
            current_ability=ability,
            current_ability_provenance={"event_kind":"current_ability_observed","trust":"user_confirmed_observation","turn_number":1},
            current_confusion=confusion,
            confusion_provenance={"event_kind":"current_confusion_observed","trust":"user_confirmed_observation","turn_number":1,"state":confusion},
        )
        state["ability_applicability_context"]={"schema_version":"ability-applicability-context-v1","session_id":state["session_id"],"source":{"side":"opponent","slot_index":0,"pokemon_id":target["pokemon_id"]},"ability_id":ability,"status":"applicable"}
        result=_assessment(state,_move(accuracy=100,category="special"))
        assert result["status"]=="resolved" and result["probability_percent"]==expected
    for ability, weather, confusion in (("sand-veil", "none", "none"), ("snow-cloak", "none", "none"), ("tangled-feet", "none", "none")):
        state=_state(); _hustle(state); _weather(state, weather); target=state["opponent_side"]["pokemon"][0]
        target.update(current_ability=ability, current_ability_provenance={"event_kind":"current_ability_observed","trust":"user_confirmed_observation","turn_number":1}, current_confusion=confusion, confusion_provenance={"event_kind":"current_confusion_observed","trust":"user_confirmed_observation","turn_number":1,"state":confusion})
        state["ability_applicability_context"]={"schema_version":"ability-applicability-context-v1","session_id":state["session_id"],"source":{"side":"opponent","slot_index":0,"pokemon_id":target["pokemon_id"]},"ability_id":ability,"status":"applicable"}
        assert _assessment(state,_move(accuracy=100,category="special"))["probability_percent"] == 100


def test_material_unknowns_and_known_unsupported_modifiers_fail_closed():
    state=_state(); _hustle(state); del state["field"]["weather_provenance"]
    assert _assessment(state,_move(accuracy=70,category="special",move_id="thunder"))["status"]=="incomplete"
    state=_state(); _hustle(state); target=state["opponent_side"]["pokemon"][0]; target["known_item"]="leftovers"; target["known_item_provenance"]={"event_kind":"current_item_observed","trust":"user_confirmed_observation","turn_number":1,"status":"known"}
    assert _assessment(state,_move(accuracy=100,category="special"))["status"]=="unsupported"
    state=_state(); _hustle(state); target=state["opponent_side"]["pokemon"][0]; target["known_item"]={"knowledge":"unknown"}; target["known_item_provenance"]=None
    assert _assessment(state,_move(accuracy=100,category="special"))["status"]=="incomplete"
    state=_state(); _hustle(state); state["opponent_side"]["pokemon"][0]["known_item_provenance"]={}
    assert _assessment(state,_move(accuracy=100,category="special"))["status"]=="rejected"
    state=_state(); _hustle(state); target=state["opponent_side"]["pokemon"][0]
    target.update(current_ability="tangled-feet", current_ability_provenance={"event_kind":"current_ability_observed","trust":"user_confirmed_observation","turn_number":1})
    state["ability_applicability_context"]={"schema_version":"ability-applicability-context-v1","session_id":state["session_id"],"source":{"side":"opponent","slot_index":0,"pokemon_id":target["pokemon_id"]},"ability_id":"tangled-feet","status":"applicable"}
    assert _assessment(state,_move(accuracy=100,category="special"))["status"]=="incomplete"
