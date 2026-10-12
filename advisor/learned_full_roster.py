"""Full-roster study: disjoint teams/joint movesets, no species-unseen claims."""

from functools import lru_cache
import gzip
from hashlib import sha256
import json
from pathlib import Path

from advisor.learned_full_domain import DOMAIN, load_inventory, curriculum_identity
from advisor.learned_native_curriculum import _load_bank

ROOT = Path(__file__).resolve().parents[1]
VERSION = "showdown-learning-curriculum-v8"
BANK = ROOT / "models/showdown_full_roster_v8"


@lru_cache(maxsize=1)
def load_bank():
    bank = _load_bank(BANK, VERSION)
    inventory = load_inventory()
    digest = sha256(
        gzip.decompress((DOMAIN / "inventory.json.gz").read_bytes())
    ).hexdigest()
    if bank.get("inventory_sha256") != digest or sorted(
        bank["train_base_species"]
    ) != sorted(inventory["base_species"]):
        raise ValueError("full_roster_inventory_binding_mismatch")
    return bank


def study_identity(catalog=None):
    authority = curriculum_identity(catalog)
    manifest = json.loads((BANK / "manifest.json").read_text(encoding="utf-8"))
    packed = (BANK / "teams.json.gz").read_bytes()
    if (
        sha256(packed).hexdigest() != manifest["bank_sha256"]
        or sha256(gzip.decompress(packed)).hexdigest() != manifest["content_sha256"]
    ):
        raise ValueError("full_roster_bank_hash_mismatch")
    return {
        **authority,
        "curriculum_version": VERSION,
        "bank_sha256": manifest["bank_sha256"],
        "partition_scope": manifest["partition_scope"],
        "additional_sources": {
            name: sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in (
                "advisor/learned_full_roster.py",
                "scripts/build_showdown_full_roster.py",
            )
        },
    }
