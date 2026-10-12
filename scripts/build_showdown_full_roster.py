"""Build a separate all-231-species bank using the already validated generator."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from collections import Counter
import gzip
from hashlib import sha256
import json
from time import perf_counter

from advisor.learned_full_domain import DOMAIN, generate_teams, load_inventory
from advisor.learned_full_roster import VERSION, BANK
from advisor.learning_resources import WindowsJob, atomic_json


def set_identity(p):
    # Moves and nickname/team order cannot make a reused complete set 'new'.
    value = {k: v for k, v in p.items() if k != "name"}
    value["moves"] = sorted(value["moves"])
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build(checkout, output=BANK):
    output = Path(output)
    if output.exists():
        raise ValueError("new_full_roster_bank_required")
    job = WindowsJob(memory_mib=2048, cpu_percent=12.5)
    started = perf_counter()
    inventory = load_inventory()
    raw = gzip.decompress((DOMAIN / "inventory.json.gz").read_bytes())
    teams, coverage, generation, set_pools, team_pools = {}, {}, {}, {}, {}
    seen_sets, seen_teams, seen_movesets = set(), set(), set()
    rare_forms = sorted(
        k for k, v in inventory["species"].items() if v["kind"] == "mega"
    )
    for number, (split, count) in enumerate(
        (("train", 4096), ("validation", 512), ("test", 512), ("unseen", 512))
    ):
        seed = [9413 + number, 22129, 31723, 51031]
        candidate_count = count + 32
        constraints = (
            [{"form": rare_forms[i % len(rare_forms)]} for i in range(candidate_count)]
            if split == "unseen" and rare_forms
            else None
        )
        generated = generate_teams(
            checkout,
            seed=seed,
            count=candidate_count,
            constraints=constraints,
            max_runtime_seconds=120,
        )
        accepted, set_hashes, team_hashes, moveset_hashes = [], set(), set(), set()
        rejections = 0
        for team in generated["teams"]:
            sets = {set_identity(p) for p in team}
            key = sha256("".join(sorted(sets)).encode()).hexdigest()
            moveset_key = sha256(
                json.dumps(
                    sorted((p["species"], sorted(p["moves"])) for p in team),
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            if key in seen_teams or moveset_key in seen_movesets:
                rejections += 1
                continue
            accepted.append(team)
            set_hashes.update(sets)
            team_hashes.add(key)
            moveset_hashes.add(moveset_key)
            if len(accepted) == count:
                break
        if len(accepted) != count:
            raise ValueError(
                f"bounded_partition_generation_exhausted:{split}:{len(accepted)}:{rejections}"
            )
        shared_sets = len(set_hashes & seen_sets)
        seen_sets.update(set_hashes)
        seen_teams.update(team_hashes)
        seen_movesets.update(moveset_hashes)
        teams[split] = accepted
        set_pools[split], team_pools[split] = sorted(set_hashes), sorted(team_hashes)
        fields = {
            name: Counter()
            for name in ("base_species", "species", "moves", "abilities", "items")
        }
        by_start = {
            v["start_species"]: v["base_species"] for v in inventory["species"].values()
        }
        for team in accepted:
            for p in team:
                fields["base_species"][by_start[p["species"]]] += 1
                for field, values in (
                    ("species", [p["species"]]),
                    ("moves", p["moves"]),
                    ("abilities", [p["ability"]]),
                    ("items", [p["item"] or "known_absence"]),
                ):
                    fields[field].update(values)
        coverage[split] = {k: dict(v) for k, v in fields.items()}
        generation[split] = {
            "seed": seed,
            "attempts": generated["attempts"],
            "rejections": generated["rejections"],
            "partition_rejections": rejections,
            "individual_sets_shared_with_earlier_splits": shared_sets,
            "team_moveset_partition_sha256": sha256(
                "".join(sorted(moveset_hashes)).encode()
            ).hexdigest(),
            "modes": generated["modes"],
        }
    if len(coverage["train"]["base_species"]) != 231:
        raise ValueError("full_roster_train_coverage_incomplete")
    bank = {
        "schema_version": "showdown-native-team-bank-v1",
        "curriculum_version": VERSION,
        "engine_commit": inventory["engine_commit"],
        "format_id": inventory["format_id"],
        "inventory_sha256": sha256(raw).hexdigest(),
        "counts": {k: len(v) for k, v in teams.items()},
        "train_base_species": inventory["base_species"],
        "teams": teams,
        "coverage": coverage,
        "generation": generation,
        "partition_scope": "All 231 base species eligible in each split; unordered complete teams and joint species/moveset combinations disjoint across train/validation/test/rare-form assessment; deterministic independent generation seeds. Individual upstream sets may recur (overlap measured), preserving the native generator distribution. No species- or individual-set-unseen claim.",
        "rare_form_constraints": rare_forms,
        "historical_holdout_exposure": "Training exposes V7 validation/test/reserved and historical fresh17 species. Their old identities/results are preserved; only V7-trained policies retain species-disjoint claims.",
        "team_selection_scope": "Coordinator random legal ordered pick-3, not learned preview.",
    }
    encoded = json.dumps(bank, sort_keys=True, separators=(",", ":")).encode()
    packed = gzip.compress(encoded, mtime=0)
    output.mkdir(parents=True)
    (output / "teams.json.gz").write_bytes(packed)
    manifest = {k: v for k, v in bank.items() if k != "teams"}
    manifest.update(
        bank_sha256=sha256(packed).hexdigest(),
        content_sha256=sha256(encoded).hexdigest(),
        wall_seconds=perf_counter() - started,
        resources=job.usage(),
        set_partition_sha256={
            k: sha256("".join(v).encode()).hexdigest() for k, v in set_pools.items()
        },
        team_partition_sha256={
            k: sha256("".join(v).encode()).hexdigest() for k, v in team_pools.items()
        },
    )
    atomic_json(output / "manifest.json", manifest)
    print(
        json.dumps(
            {
                "counts": bank["counts"],
                "coverage": {
                    s: {k: len(v) for k, v in c.items()} for s, c in coverage.items()
                },
                "rare_forms": len(rare_forms),
                "wall_seconds": manifest["wall_seconds"],
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=BANK)
    args = parser.parse_args()
    build(args.checkout, args.output)
