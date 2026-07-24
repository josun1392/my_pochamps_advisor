from core.turn_state import BattleState, PokemonBattleSlot, TurnInput, TurnSnapshot
from llm.advisor_turn_snapshot import build_snapshot_deterministic_input


def test_deterministic_input_is_detached_from_frozen_snapshot_and_preserves_unknowns():
    snapshot = TurnSnapshot(battle_state=BattleState(active_player=PokemonBattleSlot(side="player", species_id="pikachu"), active_opponent=PokemonBattleSlot(side="opponent", species_id="eevee")), turn_input=TurnInput(selected_move_id="tackle", acting_side="player", target_side="opponent"), current_state={"condition_context": {"current_conditions": [{"side": "self", "condition_type": "unknown"}]}})
    value = build_snapshot_deterministic_input(snapshot)
    value["current_state"]["condition_context"]["current_conditions"][0]["condition_type"] = "burn"
    assert snapshot.to_dict()["current_state"]["condition_context"]["current_conditions"][0]["condition_type"] == "unknown"
    assert value["pokemon"]["active_player"]["species_id"] == "pikachu" and value["selected_move_id"] == "tackle"
