"""Compare representative M-C native conditional rolls with legacy mechanics."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from advisor.showdown_bridge import SHOWDOWN_COMMIT
from advisor.showdown_worker import ShowdownWorker
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.abilities import get_ability
from advisor.damage.items import get_item
from advisor.damage.field import Field, SideField
from llm.advisor_showdown_simulation import simulate_detached_showdown, evaluate_native_damage_rolls
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios

CASES = [
    ("flamethrower", "self", "Flamethrower", None, None, None, False),
    ("air-slash", "self", "Air Slash", None, None, None, False),
    ("technician-bullet-punch", "opponent", "Bullet Punch", None, None, None, False),
    ("burned-technician", "opponent", "Bullet Punch", None, None, "burn", False),
    ("sun-fire", "self", "Flamethrower", "sun", None, None, False),
    ("rain-fire", "self", "Flamethrower", "rain", None, None, False),
    ("life-orb", "self", "Flamethrower", None, "Life Orb", None, False),
    ("sharp-beak", "self", "Air Slash", None, "Sharp Beak", None, False),
    ("metal-coat", "opponent", "Bullet Punch", None, "Metal Coat", None, False),
    ("light-screen", "self", "Air Slash", None, None, "screen", False),
    ("critical-screen-bypass", "self", "Flamethrower", None, None, "screen", True),
    ("blaze-low-hp", "self", "Flamethrower", None, None, "blaze", False),
]


def compare(checkout):
    native = []
    with ShowdownWorker(checkout) as bridge:
        for cid, side, move, weather, item, condition, critical in CASES:
            snapshot = fixture_snapshot(hp=50 if condition == "blaze" else 155)
            scenario = fixture_scenarios()[0]
            if item: scenario["teams"][side][0]["item"] = item
            scenario["choices"] = {"self": "move 3", "opponent": "move 3"}
            scenario["conditioning"] = []
            if weather: scenario["conditioning"].append({"target": "field", "effect": "weather", "id": "sunnyday" if weather == "sun" else "raindance"})
            if condition == "burn": scenario["conditioning"].append({"target": side, "effect": "status", "id": "brn"})
            if condition == "screen": scenario["conditioning"].append({"target": "opponent", "effect": "side", "id": "lightscreen"})
            result = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=bridge)
            assert result["status"] == "simulated", (cid, result.get("scenarios", [{}])[0].get("reason"))
            queried = evaluate_native_damage_rolls(runtime_snapshot=snapshot, checkpoint=result["scenarios"][0]["root_checkpoint"],
                side=side, move=move, critical=critical, bridge=bridge)
            row = queried["scenarios"][0]
            assert row["status"] == "simulated", (cid, row)
            native.append(row["damage_rolls"])
    comparisons = []
    conditions = {"": "none", "brn": "burn"}
    for case, row in zip(CASES, native, strict=True):
        cid, side, move, weather, item, condition, critical = case
        c = row["context"]; a, d = c["attacker"], c["defender"]
        ctx = DamageContext(attacker_level=c["level"], move_power=c["move_power"],
            attack_stat=a["stats"]["atk" if c["is_physical"] else "spa"], defense_stat=d["stats"]["def" if c["is_physical"] else "spd"],
            move_type=c["move_type"], attacker_types=tuple(a["types"]), defender_types=tuple(d["types"]),
            is_physical=c["is_physical"], is_critical=critical, is_spread=False, move_id=move.lower().replace(" ", "-"),
            field=Field(weather=weather or "none", is_doubles=False, defender_side=SideField(light_screen=condition == "screen")),
            attacker_species=a["species"], defender_species=d["species"], attacker_ability=get_ability(a["ability"]), defender_ability=get_ability(d["ability"]),
            attacker_item=get_item(a["item"]), defender_item=get_item(d["item"]),
            attacker_hp_current=a["hp"], attacker_hp_max=a["max_hp"], attacker_condition=conditions[a["status"]],
            burn_mod_q12=2048 if a["status"] == "brn" and c["is_physical"] else 4096,
            defender_hp_current=d["hp"], defender_hp_max=d["max_hp"])
        legacy = calc_damage_rolls(ctx)
        comparisons.append({"case_id": cid, "matched": legacy == row["rolls"], "native_rolls": row["rolls"], "legacy_rolls": legacy})
    return {"engine_commit": SHOWDOWN_COMMIT, "cases": comparisons, "all_matched": all(c["matched"] for c in comparisons),
        "scope": "conditional_single_hit_damage_fixed_crit_not_full_battle_parity"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    report = compare(parser.parse_args().checkout)
    print(json.dumps(report, separators=(",", ":")))
    raise SystemExit(0 if report["all_matched"] else 1)
