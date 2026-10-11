"""Offline executable M-C proof and benchmark, with no provider or server calls."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import statistics
import subprocess
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from advisor.showdown_bridge import FORMAT_ID, SHOWDOWN_COMMIT, ShowdownBridge
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_showdown_simulation import resume_detached_showdown, simulate_detached_showdown


def fixture_snapshot(*, hp: int = 155, opponent_hp: int = 147, session_id: str = "showdown-offline-proof") -> dict:
    state = create_unknown_bootstrap_battle_state(
        session_id, "charizard", "scizor", battle_format={"battle_format": "singles", "source": "user_confirmed_battle_format"},
    )["state"]
    for side, current, maximum in (("self", hp, 155), ("opponent", opponent_hp, 147)):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=current, max_hp=maximum, fainted=False)
    return snapshot_from_state(state)


def snapshot_from_state(state: dict) -> dict:
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"],
            "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def fixture_scenarios() -> list[dict]:
    fillers = [
        {"species": "Garchomp", "ability": "Rough Skin", "moves": ["Earthquake", "Protect"], "nature": "Jolly", "evs": {"atk": 32, "spe": 32, "hp": 2}},
        {"species": "Rotom-Wash", "ability": "Levitate", "moves": ["Thunderbolt", "Hydro Pump", "Protect"], "nature": "Modest", "evs": {"spa": 32, "spe": 32, "hp": 2}},
        {"species": "Tyranitar", "ability": "Sand Stream", "moves": ["Crunch", "Protect"], "nature": "Adamant", "evs": {"atk": 32, "hp": 32, "spd": 2}},
        {"species": "Dragonite", "ability": "Inner Focus", "moves": ["Dragon Claw", "Extreme Speed", "Protect"], "nature": "Adamant", "evs": {"atk": 32, "hp": 32, "spd": 2}},
        {"species": "Gengar", "ability": "Cursed Body", "moves": ["Shadow Ball", "Protect"], "nature": "Timid", "evs": {"spa": 32, "spe": 32, "hp": 2}},
    ]
    scenarios = []
    for scenario_id, item in (("none", ""), ("sash", "Focus Sash"), ("sitrus", "Sitrus Berry"), ("scarf", "Choice Scarf")):
        teams = {
            "self": [{"species": "Charizard", "ability": "Blaze", "moves": ["Flamethrower", "Air Slash", "Protect"], "nature": "Modest", "evs": {"spa": 32, "spe": 32, "hp": 2}}, *deepcopy(fillers)],
            "opponent": [{"species": "Scizor", "ability": "Technician", "item": item, "moves": ["Bullet Punch", "Swords Dance", "Protect"], "nature": "Adamant", "evs": {"atk": 32, "spe": 32, "hp": 2}}, *deepcopy(fillers)],
        }
        for team in teams.values():
            for pokemon in team:
                pokemon["level"] = 50
        scenarios.append({"scenario_id": scenario_id, "teams": teams, "seed": [1, 2, 3, 4],
                          "preview": {"self": [1, 2, 3], "opponent": [1, 2, 3]}, "history": [],
                          "choices": {"self": "move 1", "opponent": "move 1"},
                          "assumptions": ["All sets, unobserved HP, PP, counters and initial history are hypothetical.",
                                          f"Opponent initial held item: {item or 'none'}."]})
    return scenarios


def semantic_result(result: dict) -> dict:
    result = deepcopy(result)
    for row in result.get("scenarios", []):
        row.pop("elapsed_ms", None)
        # Native timestamps are nondeterministic metadata, not battle semantics.
        for key in ("checkpoint", "root_checkpoint"):
            if key in row:
                row[key].pop("checkpoint_fingerprint", None)
                row[key]["native_state"]["log"] = [line for line in row[key]["native_state"]["log"] if not line.startswith("|t:|")]
    return result


def verify(bridge: ShowdownBridge, *, iterations: int = 10) -> dict:
    snapshot, scenarios = fixture_snapshot(), fixture_scenarios()
    before = deepcopy((snapshot, scenarios))
    t0 = perf_counter()
    result = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=scenarios, bridge=bridge)
    cold_ms = (perf_counter() - t0) * 1000
    assert result["status"] == "simulated", result
    assert all(row["status"] == "simulated" for row in result["scenarios"]), result
    assert (snapshot, scenarios) == before
    rows = {row["scenario_id"]: row for row in result["scenarios"]}
    assert rows["none"]["after"]["sides"]["opponent"]["pokemon"][0]["hp"] == 0
    assert rows["sash"]["after"]["sides"]["opponent"]["pokemon"][0]["hp"] == 1
    assert rows["sash"]["after"]["sides"]["opponent"]["pokemon"][0]["item"] == ""
    restored = resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=rows["sash"]["root_checkpoint"],
                                       choices=scenarios[1]["choices"], bridge=bridge)
    assert restored["scenarios"][0]["after"] == rows["sash"]["after"]
    assert restored["scenarios"][0]["events"] == rows["sash"]["events"]
    # Observe a damaged mid-battle active pair and a known stage, independent of predictions.
    mid = fixture_snapshot(hp=100, opponent_hp=100)
    mid["state"]["opponent_side"]["pokemon"][0]["stat_stages"] = {"attack": 2}
    mid = snapshot_from_state(mid["state"])
    history = deepcopy(scenarios[1])
    history["history"] = [{"self": "move 3", "opponent": "move 2"}]
    reconstructed = simulate_detached_showdown(runtime_snapshot=mid, scenarios=[history], bridge=bridge)
    root = reconstructed["scenarios"][0]["before"]
    assert root["turn"] == 2
    assert [root["sides"][s]["pokemon"][0]["hp"] for s in ("self", "opponent")] == [100, 100]
    assert root["sides"]["opponent"]["pokemon"][0]["boosts"]["atk"] == 2
    # A KO requests a human-selected replacement. Explicitly resume that native boundary.
    switched = resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=rows["none"]["checkpoint"],
                                       choices={"self": "", "opponent": "switch 2"}, bridge=bridge)
    assert switched["scenarios"][0]["status"] == "simulated", switched
    assert switched["scenarios"][0]["after"]["sides"]["opponent"]["pokemon"][0]["species"] == "garchomp"
    timings = []
    for _ in range(iterations):
        started = perf_counter()
        again = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=scenarios, bridge=bridge)
        timings.append((perf_counter() - started) * 1000)
        assert semantic_result(again) == semantic_result(result)
    native_proof = subprocess.run(
        ["node", str(Path(__file__).resolve().parents[1] / "tools/showdown_bridge/proof.cjs"), str(bridge.checkout)],
        input=json.dumps(scenarios[1]), text=True, encoding="utf-8", capture_output=True,
        timeout=30, check=True,
    )
    return {"verdict": "CONDITIONAL GO", "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID,
            "checks": ["legal_six_pick_three", "native_priority_damage_sash", "seeded_reproduction",
                       "independent_items", "native_checkpoint_restore", "mid_battle_hp_stage_overlay",
                       "explicit_forced_switch_resume", "inputs_unchanged"],
            "scenario_hp": {name: [row["after"]["sides"][s]["pokemon"][0]["hp"] for s in ("self", "opponent")] for name, row in rows.items()},
            "performance_ms": {"four_scenario_first_call": cold_ms, "batches": iterations,
                               "four_scenario_p50": statistics.median(timings), "four_scenario_max": max(timings),
                               "native_scenario_ms": [row["elapsed_ms"] for row in result["scenarios"]]},
            "native_proof": json.loads(native_proof.stdout), "limitations": result["limitations"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--showdown-checkout", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=10)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("iterations must be positive")
    print(json.dumps(verify(ShowdownBridge(args.showdown_checkout), iterations=args.iterations), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
