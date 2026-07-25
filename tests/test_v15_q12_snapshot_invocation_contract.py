import llm.advisor_q12_snapshot_adapter as q12_adapter
from llm.advisor_q12_snapshot_adapter import invoke_existing_q12_from_snapshot
from llm.advisor_turn_snapshot import (
    BASE_STAT_KEYS, build_request_start_recommendation_snapshot,
    build_snapshot_damage_input, build_snapshot_stat_provenance,
)


class Repo:
    def get(self, key):
        return {"en": key, "types_en": ["electric"] if key == "pikachu" else ["normal"], "base_stats": {stat: 80 for stat in BASE_STAT_KEYS}}


def _entry(side, stat, value, pokemon, slot):
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known", "provenance": {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": "s", "source": "user_confirmed_final_battle_stat", "trust": "user_confirmed_current"}}


def _snapshot():
    final = []
    for side, pokemon, slot in (("self", "pikachu", 0), ("opponent", "eevee", 1)):
        final += [_entry(side, stat, 100 + index, pokemon, slot) for index, stat in enumerate(BASE_STAT_KEYS)]
    return build_request_start_recommendation_snapshot({"current_state_session_id": "s", "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]}, "final_stat_context": {"current_final_stats": final}}, selectable_moves=("tackle",))


def _invoke(category="physical", level=50):
    snapshot = _snapshot()
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="tackle", selectable_moves=("tackle",), move_metadata={"category": category, "power": 40, "type": "normal"})
    provenance = build_snapshot_stat_provenance(snapshot, species_repository=Repo())
    return invoke_existing_q12_from_snapshot(damage, stat_provenance=provenance, trusted_level=level)


def test_physical_and_special_snapshot_invocation_use_existing_q12_boundary(monkeypatch):
    original = q12_adapter.calc_damage_rolls
    contexts = []

    def tracking_rolls(context):
        contexts.append(context)
        return original(context)

    monkeypatch.setattr(q12_adapter, "calc_damage_rolls", tracking_rolls)
    physical = _invoke("physical")
    special = _invoke("special")
    assert physical["status"] == special["status"] == "resolved"
    assert len(physical["damage_rolls"]) == len(special["damage_rolls"]) == 16
    assert physical["candidate_move_id"] == "tackle"
    assert len(contexts) == 2
    assert (contexts[0].attack_stat, contexts[0].defense_stat) == (101, 102)
    assert (contexts[1].attack_stat, contexts[1].defense_stat) == (103, 104)


def test_status_or_missing_level_never_invokes_q12(monkeypatch):
    monkeypatch.setattr(q12_adapter, "calc_damage_rolls", lambda _context: (_ for _ in ()).throw(AssertionError("must not invoke")))
    assert _invoke("status")["limitations"] == ["status_move_not_damaging"]
    assert _invoke("physical", level=None)["limitations"] == ["trusted_level_unavailable"]


def test_tampered_candidate_owner_is_rejected_before_q12(monkeypatch):
    snapshot = _snapshot()
    damage = build_snapshot_damage_input(
        snapshot, candidate_slot_index=0, candidate_move_id="tackle",
        selectable_moves=("tackle",),
        move_metadata={"category": "physical", "power": 40, "type": "normal"},
    )
    damage["move"]["owner_species_id"] = "eevee"
    monkeypatch.setattr(q12_adapter, "calc_damage_rolls", lambda _context: (_ for _ in ()).throw(AssertionError("must not invoke")))
    result = invoke_existing_q12_from_snapshot(
        damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=Repo()), trusted_level=50,
    )
    assert result["limitations"] == ["invalid_snapshot_identity"]
