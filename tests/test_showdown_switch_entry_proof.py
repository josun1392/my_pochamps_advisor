"""Entry effects remain native, phase-bound and separate from selected moves."""
from copy import deepcopy
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_showdown_simulation import (
    simulate_detached_showdown, prove_deterministic_native_switch_entry, progress_native_showdown,
)
from llm.advisor_switch_hazard_authority import build_switch_hazard_context
from llm.advisor_switch_entry_hazards import evaluate_entry_hazards
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios, snapshot_from_state


@pytest.fixture(scope="module")
def worker():
    if not os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT"):
        pytest.skip("external pinned engine required")
    with ShowdownWorker(os.environ["POKEADVICE_SHOWDOWN_CHECKOUT"]) as bridge:
        yield bridge


def setup(worker, *, spikes=0, balloon=False, bench_hp=185, effects=False):
    state, scenario = fixture_snapshot()["state"], fixture_scenarios()[1]
    state["self_side"]["pokemon"][1] = {"pokemon_id": "garchomp", "current_hp": bench_hp, "max_hp": 185, "fainted": False}
    state["switch_hazard_context"] = build_switch_hazard_context(session_id=state["session_id"], affected_side="self",
        stealth_rock="present", spikes_layers=spikes, toxic_spikes_layers=2 if effects else 0, sticky_web="present" if effects else "absent")
    scenario["conditioning"] = [{"target": "self", "effect": "side", "id": "stealthrock"}]
    if spikes:
        scenario["conditioning"].append({"target": "self", "effect": "side", "id": "spikes", "layers": spikes})
    if effects:
        scenario["conditioning"] += [{"target": "self", "effect": "side", "id": "toxicspikes", "layers": 2},
                                      {"target": "self", "effect": "side", "id": "stickyweb"}]
    if balloon:
        scenario["teams"]["self"][1]["item"] = "Air Balloon"
    scenario["choices"] = {"self": "switch slot:1", "opponent": "move 2"}
    snapshot = snapshot_from_state(state)
    full = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)["scenarios"][0]
    assert full["status"] == "simulated", full
    return snapshot, scenario, full


@pytest.mark.parametrize("spikes", [0, 1, 2, 3])
@pytest.mark.parametrize("balloon", [False, True])
def test_native_switch_entry_parity_and_residual_exclusion(worker, spikes, balloon):
    snapshot, scenario, full = setup(worker, spikes=spikes, balloon=balloon)
    original = deepcopy(snapshot)
    result = prove_deterministic_native_switch_entry(runtime_snapshot=snapshot, checkpoint=full["root_checkpoint"],
        bridge=worker, choices=scenario["choices"])
    row = result["scenarios"][0]
    assert row["status"] == "simulated", row
    assert result["outcome_schema_version"] == "showdown-native-switch-entry-evidence-v1"
    assert row["probability_scope"]["scope"] == "native_switch_entry_batch_before_moves"
    assert row["probability_mass"] == {"numerator": 1, "denominator": 1}
    incoming = next(p for p in row["after"]["sides"]["self"]["pokemon"] if p["slot_index"] == 1)
    old = evaluate_entry_hazards(hazards=snapshot["state"]["switch_hazard_context"], target={"side": "self",
        "hp_authority": {"status": "known", "current_hp": 185, "maximum_hp": 185}, "item_authority": {"status": "known", "value": "air-balloon" if balloon else None},
        "ability_authority": {"status": "known", "value": "rough-skin"}, "current_type_authority": {"status": "known", "value": ["dragon", "ground"]},
        "prospective_groundedness_authority": {"status": "ungrounded" if balloon else "grounded"}})
    assert incoming["hp"] == old["post_hazard_hp"]
    assert not any(line.startswith("|move|") for line in row["events"])
    assert row["native_progression"]["completed_entries"] == [{"side": "self", "slot_index": 1, "fainted": False}]
    drained = progress_native_showdown(runtime_snapshot=snapshot, checkpoint=row["checkpoint"], bridge=worker, stop_after_move=False)["scenarios"][0]
    assert drained["after"] == full["after"]
    assert snapshot == original


def test_native_toxic_spikes_web_and_faint_entry_are_not_deferred_to_attack(worker):
    snapshot, scenario, full = setup(worker, spikes=3, effects=True)
    row = prove_deterministic_native_switch_entry(runtime_snapshot=snapshot, checkpoint=full["root_checkpoint"], bridge=worker, choices=scenario["choices"])["scenarios"][0]
    incoming = next(p for p in row["after"]["sides"]["self"]["pokemon"] if p["slot_index"] == 1)
    assert incoming["hp"] == 128 and incoming["status"] == "tox" and incoming["boosts"]["spe"] == -1
    assert full["after"]["sides"]["self"]["pokemon"][0]["hp"] == 117  # Later residual is outside the proof.
    snapshot, scenario, full = setup(worker, bench_hp=1)
    row = prove_deterministic_native_switch_entry(runtime_snapshot=snapshot, checkpoint=full["root_checkpoint"], bridge=worker, choices=scenario["choices"])["scenarios"][0]
    assert row["status"] == "simulated", row
    assert row["native_progression"]["completed_entries"][0]["fainted"] is True
    assert row["after"]["sides"]["self"]["pokemon"][0]["hp"] == 0
    assert not any(line.startswith("|move|") for line in row["events"])


def test_move_choices_and_stale_source_cannot_claim_switch_entry_mass(worker):
    snapshot, scenario, full = setup(worker)
    result = prove_deterministic_native_switch_entry(runtime_snapshot=snapshot, checkpoint=full["root_checkpoint"], bridge=worker,
        choices={"self": "move 1", "opponent": "move 2"})
    row = result["scenarios"][0]
    assert row["status"] == "rejected" and row["reason"] == "native_switch_entry_before_move_required"
    assert "probability_mass" not in row
    snapshot["state"]["self_side"]["pokemon"][0]["current_hp"] -= 1
    snapshot = snapshot_from_state(snapshot["state"])
    result = prove_deterministic_native_switch_entry(runtime_snapshot=snapshot, checkpoint=full["root_checkpoint"], bridge=worker, choices=scenario["choices"])
    assert result["status"] == "rejected" and "scenarios" not in result
