"""Coordinator-only reuse of a SHA-bound native generated curriculum bank."""

from functools import lru_cache
import gzip
from hashlib import sha256
import json
from pathlib import Path
import random
from copy import deepcopy
from advisor.showdown_bridge import FORMAT_ID, SHOWDOWN_COMMIT

VERSION = "showdown-learning-curriculum-v6"
BANK = Path(__file__).resolve().parents[1] / "models/showdown_native_curriculum_v6"
FRESH_VERSION = "showdown-learning-curriculum-v6-fresh17"
FRESH_BANK = Path(__file__).resolve().parents[1] / "models/showdown_native_fresh17"


@lru_cache(maxsize=3)
def _load_bank(path, version):
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    compressed = (path / "teams.json.gz").read_bytes()
    if sha256(compressed).hexdigest() != manifest.get("bank_sha256"):
        raise ValueError("native_curriculum_hash_mismatch")
    bank = json.loads(gzip.decompress(compressed))
    if any(
        bank.get(key) != value
        for key, value in {
            "schema_version": "showdown-native-team-bank-v1",
            "curriculum_version": version,
            "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID,
        }.items()
    ):
        raise ValueError("native_curriculum_contract_mismatch")
    if any(
        len(bank["teams"][split]) != bank["counts"][split]
        for split in ("train", "validation", "test", "unseen")
    ):
        raise ValueError("native_curriculum_count_mismatch")
    return bank


def load_bank():
    return _load_bank(BANK, VERSION)


@lru_cache(maxsize=1)
def _full_bank():
    from advisor.learned_full_domain import BANK, CURRICULUM, DOMAIN, load_inventory

    bank = _load_bank(BANK, CURRICULUM)
    inventory = load_inventory()
    raw = gzip.decompress((DOMAIN / "inventory.json.gz").read_bytes())
    if bank.get("inventory_sha256") != sha256(raw).hexdigest():
        raise ValueError("curriculum_domain_identity_mismatch")
    pools = bank["partition_species"]
    if any(set(pools[a]) & set(pools[b]) for a in pools for b in pools if a != b):
        raise ValueError("full_domain_partition_overlap")
    for split, pool in pools.items():
        allowed = {
            e["start_species"]
            for e in inventory["species"].values()
            if e["base_species"] in pool
        }
        if any(
            p["species"] not in allowed for team in bank["teams"][split] for p in team
        ):
            raise ValueError("full_domain_team_outside_partition")
    return bank


def native_case(split, index, *, version=VERSION):
    if version == FRESH_VERSION and split != "unseen":
        raise ValueError("fresh_final_bank_cannot_be_used_for_training_or_selection")
    if version == "showdown-learning-curriculum-v7":
        bank = _full_bank()
    else:
        bank = (
            _load_bank(FRESH_BANK, version) if version == FRESH_VERSION else load_bank()
        )
    rng = random.Random(
        int.from_bytes(sha256(f"{version}:{split}:{index}".encode()).digest(), "big")
    )
    pool = bank["teams"][split]
    teams = {side: deepcopy(rng.choice(pool)) for side in ("self", "opponent")}
    # Team selection remains a coordinator fixture, not a perfect-information label.
    preview = {side: rng.sample(range(1, 7), 3) for side in teams}
    return {
        "scenario_id": f"{split}-{index}",
        "teams": teams,
        "preview": preview,
        "seed": [rng.randrange(65536) for _ in range(4)],
        "history": [],
        "assumptions": [
            "Native generated complete hypothetical teams, never observed truth."
        ],
    }
