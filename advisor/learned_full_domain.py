"""Versioned coordinator-only native legal-domain access; no battle mechanics."""

from functools import lru_cache
import gzip
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
from advisor.showdown_bridge import FORMAT_ID, SHOWDOWN_COMMIT

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = ROOT / "models/showdown_mc_domain_v1"
VERSION = "showdown-mc-legal-domain-v1"
CURRICULUM = "showdown-learning-curriculum-v7"
BANK = ROOT / "models/showdown_full_domain_v7"


def curriculum_identity(catalog=None):
    """Fresh content binding for V7 training/evaluation/restart (never an actor input)."""
    domain = json.loads((DOMAIN / "manifest.json").read_text(encoding="utf-8"))
    bank = json.loads((BANK / "manifest.json").read_text(encoding="utf-8"))
    packed = (BANK / "teams.json.gz").read_bytes()
    bank_hash = sha256(packed).hexdigest()
    raw_domain = gzip.decompress((DOMAIN / "inventory.json.gz").read_bytes())
    domain_hash = sha256(raw_domain).hexdigest()
    catalog_path = Path(catalog) if catalog is not None else DOMAIN / "catalog.json"
    catalog_hash = sha256(catalog_path.read_bytes()).hexdigest()
    if (
        bank_hash != bank["bank_sha256"]
        or sha256(gzip.decompress(packed)).hexdigest() != bank["content_sha256"]
        or domain_hash != domain["content_sha256"]
        or bank["inventory_sha256"] != domain_hash
        or catalog_hash != domain["catalog_sha256"]
    ):
        raise ValueError("full_domain_training_content_mismatch")
    for name, expected in domain["tool_source_sha256"].items():
        if (
            sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            != expected
        ):
            raise ValueError("full_domain_generator_source_mismatch")
    adapters = [
        "advisor/learned_full_domain.py",
        "advisor/learned_native_curriculum.py",
        "advisor/learned_scenarios.py",
        "advisor/showdown_observation.py",
        "advisor/showdown_environment.py",
        "tools/showdown_bridge/environment.cjs",
        "tools/showdown_bridge/legal-battle.cjs",
    ]
    return {
        "schema_version": "showdown-full-domain-training-binding-v1",
        "curriculum_version": CURRICULUM,
        "public_state_version": "showdown-policy-state-v2",
        "engine_commit": SHOWDOWN_COMMIT,
        "inventory_content_sha256": domain_hash,
        "bank_sha256": bank_hash,
        "catalog_sha256": catalog_hash,
        "generator_source_sha256": domain["tool_source_sha256"],
        "adapter_source_sha256": {
            name: sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in adapters
        },
    }


@lru_cache(maxsize=1)
def load_inventory():
    manifest = json.loads((DOMAIN / "manifest.json").read_text(encoding="utf-8"))
    packed = (DOMAIN / "inventory.json.gz").read_bytes()
    raw = gzip.decompress(packed)
    if (
        sha256(packed).hexdigest() != manifest["compressed_sha256"]
        or sha256(raw).hexdigest() != manifest["content_sha256"]
    ):
        raise ValueError("legal_domain_hash_mismatch")
    inventory = json.loads(raw)
    if any(
        inventory.get(k) != value
        for k, value in {
            "schema_version": VERSION,
            "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID,
        }.items()
    ):
        raise ValueError("legal_domain_contract_mismatch")
    return inventory


def generate_teams(
    checkout,
    *,
    seed,
    count=1,
    allowed_bases=None,
    constraints=None,
    max_runtime_seconds=60,
):
    """Bounded offline native generation. Returned full sets are privileged fixtures.

    Studies must explicitly choose a training partition; unrestricted generation
    is a coverage facility and must not be used to erase holdout reservations.
    """
    if (
        not isinstance(seed, (tuple, list))
        or len(seed) != 4
        or any(type(n) is not int or not 0 <= n <= 65535 for n in seed)
        or type(count) is not int
        or not 1 <= count <= 8192
        or not 1 <= max_runtime_seconds <= 300
    ):
        raise ValueError("bounded_generation_required")
    inventory = load_inventory()
    raw = gzip.decompress((DOMAIN / "inventory.json.gz").read_bytes())
    request = {
        "operation": "teams",
        "seed": list(seed),
        "count": count,
        "inventory_sha256": sha256(raw).hexdigest(),
    }
    if allowed_bases is not None:
        request["allowed_bases"] = list(allowed_bases)
    if constraints is not None:
        request["constraints"] = list(constraints)
    with tempfile.TemporaryDirectory(prefix="poke-mc-generation-") as directory:
        source = Path(directory) / "inventory.json"
        source.write_bytes(raw)
        request["inventory"] = str(source)
        response = subprocess.run(
            [
                "node",
                str(ROOT / "tools/showdown_bridge/full-domain.cjs"),
                str(Path(checkout).resolve()),
            ],
            input=json.dumps(request),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=max_runtime_seconds,
        )
    if response.returncode:
        raise ValueError(
            f"native_full_domain_generation_failed: {response.stderr[-1200:]}"
        )
    result = json.loads(response.stdout)
    if (
        result.get("engine_commit") != inventory["engine_commit"]
        or result.get("inventory_sha256") != request["inventory_sha256"]
    ):
        raise ValueError("generated_domain_identity_mismatch")
    return result
