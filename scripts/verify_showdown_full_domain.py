"""Bounded native coverage, public observation and battle execution audit."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from collections import Counter
from copy import deepcopy
import gzip
from hashlib import sha256
import json
import logging
from time import perf_counter
import numpy as np
import torch
from advisor.learned_full_domain import (
    DOMAIN,
    CURRICULUM,
    load_inventory,
    generate_teams,
)
from advisor.learned_action_encoder import make_encoder
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_native_curriculum import _full_bank
from advisor.learned_policy import LearnedPolicy
from advisor.learned_scenarios import scenario
from advisor.learned_encoder import identifier
from advisor.learning_resources import (
    WindowsJob,
    RuntimeLimit,
    atomic_json,
    enforce_local_network_only,
)
from advisor.showdown_environment import ShowdownEnvironment
from scripts.build_showdown_full_domain import native

ROOT = Path(__file__).resolve().parents[1]
CATALOG = DOMAIN / "catalog.json"


def witness_case(inventory, target, move=None):
    entry = inventory["species"][target]
    own = deepcopy(entry["witness"])
    if move:
        own["moves"] = [move]
    # Shared audit filler construction, with a harmless native-legal opponent.
    fillers, used = [own], {entry["base_species"]}
    for p in inventory["species"].values():
        if (
            p["kind"] == "selectable"
            and not p["required_item"]
            and p["base_species"] not in used
        ):
            fillers.append(deepcopy(p["witness"]))
            used.add(p["base_species"])
            if len(fillers) == 6:
                break
    opponent = deepcopy(fillers)
    opponent[0] = deepcopy(inventory["species"]["blastoise"]["witness"])
    opponent[0]["moves"] = ["Protect", "Surf"]
    # Blastoise may already occupy a filler slot. Select unique bases again.
    opponent = [opponent[0]]
    used = {"Blastoise"}
    for p in inventory["species"].values():
        if (
            p["kind"] == "selectable"
            and not p["required_item"]
            and p["base_species"] not in used
        ):
            opponent.append(deepcopy(p["witness"]))
            used.add(p["base_species"])
            if len(opponent) == 6:
                break
    return {
        "scenario_id": f"domain-native-{target}",
        "teams": {"self": fillers, "opponent": opponent},
        "preview": {"self": [1, 2, 3], "opponent": [1, 2, 3]},
        "seed": [381, 491, 631, 773],
        "history": [],
    }


def run(checkout, output, sample_teams, max_runtime):
    output.mkdir(parents=True, exist_ok=False)
    job = WindowsJob(memory_mib=4096, cpu_percent=12.5)
    budget = RuntimeLimit(output, max_runtime)
    # Import poke-env before installing the socket guard (Windows loopback pipe).
    import poke_env  # noqa: F401

    network = enforce_local_network_only()
    torch.set_num_threads(1)
    started = perf_counter()
    inventory = load_inventory()
    summary = {
        "schema_version": "showdown-full-domain-verification-v1",
        "public_state_version": "showdown-policy-state-v2",
        "engine_commit": inventory["engine_commit"],
        "format_id": inventory["format_id"],
        "inventory_content_sha256": sha256(
            gzip.decompress((DOMAIN / "inventory.json.gz").read_bytes())
        ).hexdigest(),
    }
    repeated = native(checkout, {"operation": "audit"}, max_runtime)
    assert repeated == inventory, "inventory not reproducible"
    print("Native inventory reproduced", flush=True)
    if budget.stopping():
        raise RuntimeError("verification_runtime_exhausted")
    generation_start = perf_counter()
    sampled = generate_teams(
        checkout,
        seed=[123, 457, 811, 1597],
        count=sample_teams,
        max_runtime_seconds=max_runtime,
    )
    replayed = generate_teams(
        checkout,
        seed=[123, 457, 811, 1597],
        count=sample_teams,
        max_runtime_seconds=max_runtime,
    )
    assert sampled == replayed, "generation not reproducible"
    constraints = [
        {"form": id}
        for id, p in inventory["species"].items()
        if p["kind"] != "ability_transformation"
    ]
    for move in inventory["moves"]:
        id, p = next(
            (id, p) for id, p in inventory["species"].items() if move in p["moves"]
        )
        ability = next(a for a, ms in p["moves_by_ability"].items() if move in ms)
        constraints.append({"form": id, "ability": ability, "move": move})
    for ability in inventory["abilities"]:
        id = next(
            id for id, p in inventory["species"].items() if ability in p["abilities"]
        )
        constraints.append({"form": id, "ability": ability})
    for item in inventory["items"].values():
        witness = item["witness"]
        id = next(
            id
            for id, p in inventory["species"].items()
            if p["kind"] == "selectable" and p["start_species"] == witness["species"]
        )
        constraints.append({"form": id, "item": item["name"]})
    fixtures = generate_teams(
        checkout,
        seed=[1601, 2203, 2801, 3301],
        count=len(constraints),
        constraints=constraints,
        max_runtime_seconds=max_runtime,
    )
    coverage = {k: set() for k in ("species", "moves", "abilities", "items")}
    for team in sampled["teams"] + fixtures["teams"]:
        for p in team:
            coverage["species"].add(p["species"])
            coverage["moves"].update(p["moves"])
            coverage["abilities"].add(p["ability"])
            coverage["items"].add(p["item"])
    assert set(inventory["moves"]) <= coverage["moves"]
    assert set(inventory["abilities"]) <= coverage["abilities"]
    assert {i["name"] for i in inventory["items"].values()} <= coverage["items"]
    fixture_bytes = json.dumps(
        {"constraints": constraints, **fixtures}, sort_keys=True, separators=(",", ":")
    ).encode()
    (output / "coverage_fixtures.json.gz").write_bytes(
        gzip.compress(fixture_bytes, mtime=0)
    )
    summary["generation"] = {
        "sample_teams": sample_teams,
        "fixture_teams": len(constraints),
        "repeat_sample_equal": True,
        "inventory_reproduced": True,
        "coverage": {k: len(v) for k, v in coverage.items()},
        "attempts": sampled["attempts"],
        "rejections": sampled["rejections"],
        "modes": sampled["modes"],
        "fixtures_sha256": sha256(fixture_bytes).hexdigest(),
        "seconds": perf_counter() - generation_start,
    }
    print("Native legality and full set-attribute coverage verified", flush=True)
    encoders = [
        make_encoder(CATALOG, f"showdown-learned-observation-v{i}") for i in range(1, 5)
    ]
    events, incomplete, disabled = Counter(), Counter(), []
    public_effect_warnings = Counter()

    class Warnings(logging.Filter):
        def filter(self, record):
            message = record.getMessage()
            if "Unexpected effect" in message:
                public_effect_warnings[message] += 1
                return False
            return True

    logging.getLogger("poke-env").addFilter(Warnings())
    policy_paths = [
        "showdown_initial_v1",
        "showdown_action_v2",
        "showdown_generalization_v3",
        "showdown_tactical_v4",
    ]
    legacy_catalog = ROOT / "models/showdown_initial_v1/catalog.json"
    models = [
        LearnedPolicy(ROOT / "models" / p / "model.zip", legacy_catalog)
        for p in policy_paths
    ]
    activated_megas = set()
    decision_start = perf_counter()
    baseline = VisibleBaseline("tactical_heuristic", 7993)
    with ShowdownEnvironment(checkout, max_decisions=256) as env:
        for index, (constraint, team) in enumerate(zip(constraints, fixtures["teams"])):
            if budget.stopping():
                raise RuntimeError("verification_runtime_exhausted")
            case = witness_case(inventory, constraint["form"])
            case["teams"]["self"] = team
            env.reset(case)
            observation = env.observation("self", include_history=True)
            for encoder in encoders:
                assert not encoder.coverage(observation)["missing_species"]
                features = encoder.encode(observation)
                assert np.isfinite(features).all()
            assert observation["action_mask"][baseline.act(observation)]
            assert (
                not {"seed", "teams", "checkpoint", "queue", "native_state"}
                & observation.keys()
            )
            if index < 12:
                for model in models:
                    action = model.act(observation)
                    assert observation["action_mask"][action]
            entry = inventory["species"][constraint["form"]]
            choices = [i for i, m in enumerate(observation["action_mask"]) if m]
            mega = [i for i in choices if i in range(10, 14) or i in range(27, 35)]
            selected = (
                mega[0]
                if entry["kind"] == "mega"
                else next((i for i in choices if 6 <= i <= 9), choices[0])
            )
            if constraint.get("move") and not observation["action_mask"][6]:
                disabled.append(constraint["move"])
            result = env.step(
                {"self": selected, "opponent": 6}, revision=observation["revision"]
            )
            assert not result["action_rejected"]
            after = env.observation("self", include_history=True)
            for encoder in encoders:
                assert not encoder.coverage(after)["missing_species"]
                assert np.isfinite(encoder.encode(after)).all()
            if not result["terminated"]:
                assert after["action_mask"][baseline.act(after)]
            for line in after["events"]:
                events[line.split("|")[1]] += 1
            incomplete.update(
                after["projection_coverage"]["preserved_unmodeled_state_events"]
            )
            if entry["kind"] == "mega":
                native_forms = [
                    identifier(p["details"])
                    for p in after["own_request"].get("side", {}).get("pokemon", [])
                ]
                assert constraint["form"] in native_forms, (
                    f"mega not activated: {constraint['form']}"
                )
                activated_megas.add(constraint["form"])
            if index % 100 == 0:
                saved = env.save()
                with env.fork() as fork:
                    assert fork.save()["digest"] == saved["digest"]
                    if not result["terminated"]:
                        actions = {
                            side: next(
                                i
                                for i, m in enumerate(
                                    env.observation(side)["action_mask"]
                                )
                                if m
                            )
                            for side in ("self", "opponent")
                        }
                        env.step(actions, revision=after["revision"])
                        fork.step(
                            actions, revision=fork.observation("self")["revision"]
                        )
                        assert env.save()["digest"] == fork.save()["digest"]
        summary["execution"] = {
            "initial_and_post_action_encoder_checks": len(constraints) * 8,
            "native_fixture_progressions": len(constraints),
            "activated_mega_forms": len(activated_megas),
            "native_initial_action_gates": sorted(set(disabled)),
            "public_event_counts": dict(events),
            "preserved_unmodeled_public_event_counts": dict(incomplete),
            "seconds": perf_counter() - decision_start,
        }
        transforms = {
            "castformsunny": "Sunny Day",
            "castformrainy": "Rain Dance",
            "castformsnowy": "Snowscape",
            "aegislashblade": "Iron Head",
            "mimikyubusted": "Swords Dance",
            "morpekohangry": "Protect",
            "palafinhero": None,
        }
        reached = []
        for target, move in transforms.items():
            env.reset(witness_case(inventory, target, move))
            own = env.observation("self")
            if target == "palafinhero":
                env.step({"self": 1, "opponent": 6}, revision=own["revision"])
                own = env.observation("self")
                slot = next(
                    i
                    for i, p in enumerate(own["own_request"]["side"]["pokemon"])
                    if p["details"].startswith("Palafin")
                )
                action = slot
            else:
                action = 6
            env.step(
                {"self": action, "opponent": 7 if target == "mimikyubusted" else 6},
                revision=own["revision"],
            )
            after = env.observation("self", include_history=True)
            observed = [
                identifier(p["details"])
                for p in after["state"]["self_side"]["pokemon"].values()
            ]
            assert target in observed, (
                f"native transformation not observed: {target}, {observed}"
            )
            reached.append(target)
        summary["ability_transformations"] = reached
        battles = []
        for index in range(32):
            if budget.stopping():
                raise RuntimeError("verification_runtime_exhausted")
            env.reset(scenario("train", 720000 + index, version=CURRICULUM))
            actors = {
                "self": VisibleBaseline("max_power", index),
                "opponent": VisibleBaseline("tactical_heuristic", index + 39),
            }
            while True:
                own = env.observation("self", include_history=True)
                result = env.step(
                    {
                        side: actors[side].act(
                            env.observation(side, include_history=True)
                        )
                        for side in actors
                    },
                    revision=own["revision"],
                )
                if result["terminated"] or result["truncated"]:
                    break
            battles.append(result)
        summary["battles"] = {
            "count": len(battles),
            "terminal": sum(r["terminated"] for r in battles),
            "truncated": sum(r["truncated"] for r in battles),
            "outcomes": dict(
                Counter(r["winner"] or "draw_or_truncated" for r in battles)
            ),
        }
        summary["native_resources"] = env.resources
    bank = _full_bank()
    summary["partitions"] = {
        split: len(pool) for split, pool in bank["partition_species"].items()
    }
    summary["legacy_catalog_missing_species"] = sorted(
        set(inventory["species"])
        - set(json.loads(legacy_catalog.read_text())["species"])
    )
    summary["model_identity_preserved"] = {
        p: model.model_id for p, model in zip(policy_paths, models)
    }
    summary["unsupported_poke_env_effect_warnings"] = dict(public_effect_warnings)
    summary["wall_seconds"] = perf_counter() - started
    summary["resources"] = job.usage()
    summary["network"] = network
    atomic_json(output / "summary.json", summary)
    budget.finished.set()
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "generation",
                    "execution",
                    "battles",
                    "wall_seconds",
                    "resources",
                )
            }
        ),
        flush=True,
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-teams", type=int, default=4096)
    parser.add_argument("--max-runtime-seconds", type=int, default=300)
    args = parser.parse_args()
    if not 64 <= args.sample_teams <= 8192 or not 60 <= args.max_runtime_seconds <= 600:
        parser.error("bounded sample/runtime required")
    run(args.checkout, args.output, args.sample_teams, args.max_runtime_seconds)


if __name__ == "__main__":
    main()
