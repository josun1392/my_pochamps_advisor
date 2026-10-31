"""Immutable prospective evaluation inputs. Coordinator only, no policy runner.

Team generation reuses the maintained native legal-domain CLI. This module
does not authorize terminal battles, model loading, training or promotion.
"""
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

from advisor.learned_encoder import fingerprint
from advisor.learned_full_domain import DOMAIN, load_inventory
from advisor.learned_response_predictor import team_signature
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID, silent_process_options

VERSION = "showdown-prospective-policy-evaluation-source-v1"
READY_VERSION = "showdown-prospective-policy-evaluation-readiness-v1"
ROOT = Path(__file__).resolve().parents[1]
OWNERS = ("a", "b")
SEATS = ("self", "opponent")
OPPONENTS = ("champions_heuristic", "tactical_heuristic", "frozen_v4_reference")


def file_sha(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def generate_team_batch(checkout, *, seed, count=200):
    """Native TeamValidator generation only; never creates a battle.

    Retains the maintained generator's bounded retry semantics. The caller
    must freeze seed/count first and must not redraw duplicates or failures.
    """
    if (not isinstance(seed, list) or len(seed) != 4
            or any(type(n) is not int or not 0 <= n <= 65535 for n in seed)
            or type(count) is not int or not 1 <= count <= 200):
        raise ValueError("bounded_prospective_generation_required")
    inventory = load_inventory()
    import gzip
    raw = gzip.decompress((DOMAIN / "inventory.json.gz").read_bytes())
    with tempfile.TemporaryDirectory(prefix="poke-prospective-inventory-") as folder:
        path = Path(folder) / "inventory.json"
        path.write_bytes(raw)
        request = {"operation": "teams", "inventory": str(path),
                   "inventory_sha256": sha256(raw).hexdigest(), "seed": seed, "count": count}
        response = subprocess.run(
            ["node", str(ROOT / "tools/showdown_bridge/full-domain.cjs"), str(Path(checkout).resolve())],
            input=json.dumps(request), text=True, encoding="utf-8", capture_output=True,
            timeout=120, **silent_process_options(),
        )
    if response.returncode:
        raise ValueError("prospective_native_generation_failed:" + response.stderr[-1200:])
    result = json.loads(response.stdout)
    if (result.get("schema_version") != "showdown-full-domain-generated-teams-v1"
            or result.get("engine_commit") != SHOWDOWN_COMMIT
            or result.get("format_id") != FORMAT_ID
            or result.get("inventory_sha256") != sha256(raw).hexdigest()
            or result.get("seed") != seed or len(result.get("teams", [])) != count
            or inventory["engine_commit"] != SHOWDOWN_COMMIT):
        raise ValueError("prospective_generation_identity_mismatch")
    return result


def _seed(value):
    return (isinstance(value, list) and len(value) == 4
            and all(type(n) is int and 0 <= n <= 65535 for n in value))


class ProspectiveEvaluationSource:
    """Frozen 96-case finite source, not the historical TRAIN distribution.

    Private teams/scenarios are coordinator inputs, never actor features.
    A readiness receipt is mandatory to enumerate evaluation points. It
    attests protocol-only tests; it is not an authorization to run battles.
    """

    def __init__(self, path, expected_sha256, *, readiness=None, readiness_sha256=None):
        self.path = Path(path).resolve()
        if file_sha(self.path) != expected_sha256:
            raise ValueError("prospective_manifest_hash_mismatch")
        manifest = json.loads(self.path.read_text(encoding="utf-8"))
        if (manifest.get("schema_version") != VERSION
                or manifest.get("engine_commit") != SHOWDOWN_COMMIT
                or manifest.get("format_id") != FORMAT_ID
                or manifest.get("native_team_validated") is not True):
            raise ValueError("prospective_authority_mismatch")
        asset = self._asset(manifest["team_asset"])
        batch = json.loads(asset.read_text(encoding="utf-8"))
        teams = batch.get("teams", [])
        if (len(teams) != 200 or any(not isinstance(t, list) or len(t) != 6 for t in teams)
                or batch.get("engine_commit") != SHOWDOWN_COMMIT
                or batch.get("format_id") != FORMAT_ID):
            raise ValueError("prospective_team_asset_mismatch")
        if len({team_signature(t) for t in teams}) != 200:
            raise ValueError("prospective_duplicate_team_identity")
        cases = manifest.get("cases", [])
        if (len(cases) != 100 or any(not isinstance(c.get("case_id"), str) or not c["case_id"] for c in cases)
                or len({c["case_id"] for c in cases}) != 100
                or any(type(c.get("index")) is not int for c in cases)
                or [c["index"] for c in cases] != list(range(161031000, 161031100))
                or any(c.get("partition") != ("protocol" if i < 4 else "sealed")
                       for i, c in enumerate(cases))):
            raise ValueError("prospective_fixed_case_support_mismatch")
        all_seeds = []
        for i, case in enumerate(cases):
            if (case.get("team_indices") != {"a": 2 * i, "b": 2 * i + 1}
                    or not isinstance(case.get("admitted"), bool)):
                raise ValueError("prospective_team_pair_binding_mismatch")
            for owner in OWNERS:
                order = case["ordered3"][owner]
                if (not isinstance(order, list) or len(order) != 3 or len(set(order)) != 3
                        or any(type(n) is not int or not 1 <= n <= 6 for n in order)):
                    raise ValueError("prospective_ordered_three_mismatch")
                for seat in SEATS:
                    vector = case["native_seeds"][owner + ":" + seat]
                    if not _seed(vector):
                        raise ValueError("prospective_seed_mismatch")
                    all_seeds.append(tuple(vector))
        if len(set(all_seeds)) != 400:
            raise ValueError("prospective_duplicate_seed")
        if (tuple(manifest.get("opponent_order", [])) != OPPONENTS
                or set(manifest.get("opponents", {})) != set(OPPONENTS)):
            raise ValueError("prospective_opponent_support_mismatch")
        measure = manifest.get("measure", {})
        if measure != {"name": "Q_eval_source_v1", "cases": 96, "owners": list(OWNERS),
                       "seats": list(SEATS), "opponents": list(OPPONENTS),
                       "points": 1152, "point_mass": "1/1152", "case_mass": "1/96",
                       "renormalize": False, "historical_TRAIN_prior": False}:
            raise ValueError("prospective_probability_contract_mismatch")
        self._manifest, self._teams = deepcopy(manifest), deepcopy(teams)
        self._sha256 = expected_sha256
        self._ready = False
        if readiness is not None:
            rp = Path(readiness).resolve()
            if readiness_sha256 is None or file_sha(rp) != readiness_sha256:
                raise ValueError("prospective_readiness_hash_mismatch")
            receipt = json.loads(rp.read_text(encoding="utf-8"))
            if (receipt.get("schema_version") != READY_VERSION
                    or receipt.get("status") != "SEALED_EVAL_SOURCE_READY"
                    or receipt.get("manifest_sha256") != expected_sha256):
                raise ValueError("prospective_readiness_not_established")
            protocol = json.loads(self._asset(receipt["protocol_audit"]).read_text(encoding="utf-8"))
            novelty = json.loads(self._asset(receipt["novelty_audit"]).read_text(encoding="utf-8"))
            if (any(a.get("status") != "PASS" or a.get("manifest_sha256") != expected_sha256
                    for a in (protocol, novelty))
                    or any(protocol.get(k) != v for k, v in {
                        "native_starts": 6, "native_steps": 0, "terminal_games": 0, "model_forwards": 0}.items())
                    or any(novelty.get(k) != v for k, v in {
                        "sealed_cases": 96, "all_cases_admitted": True,
                        "old_semantic_team_overlap": 0, "old_base_roster_overlap": 0,
                        "old_seed_overlap": 0, "old_case_id_overlap": 0}.items())):
                raise ValueError("prospective_readiness_audit_failed")
            self._ready = True

    @property
    def manifest(self):
        return deepcopy(self._manifest)

    @property
    def sha256(self):
        return self._sha256

    @property
    def ready(self):
        return self._ready

    def _asset(self, binding):
        relative = Path(binding["path"])
        path = (self.path.parent / relative).resolve()
        if (relative.is_absolute() or ".." in relative.parts
                or not path.is_relative_to(self.path.parent)
                or path.is_relative_to(ROOT)):
            raise ValueError("prospective_private_asset_path_mismatch")
        if file_sha(path) != binding["sha256"]:
            raise ValueError("prospective_asset_hash_mismatch")
        return path

    def _scenario(self, case, owner, seat):
        opposite_owner = "b" if owner == "a" else "a"
        opposite_seat = "opponent" if seat == "self" else "self"
        return {"scenario_id": case["case_id"] + ":" + owner + ":" + seat,
                "teams": {seat: deepcopy(self._teams[case["team_indices"][owner]]),
                          opposite_seat: deepcopy(self._teams[case["team_indices"][opposite_owner]])},
                "preview": {seat: list(case["ordered3"][owner]),
                            opposite_seat: list(case["ordered3"][opposite_owner])},
                "seed": list(case["native_seeds"][owner + ":" + seat]), "history": [],
                "assumptions": ["Prospective coordinator-only native-legal fixture, not public hidden-set knowledge."]}

    def protocol_scenarios(self):
        """Two fixed nonterminal fixtures; not evaluation support."""
        for i, owner, seat in [(0, "a", "self"), (1, "b", "opponent")]:
            case = self._manifest["cases"][i]
            yield {"case_id": case["case_id"], "owner": owner, "seat": seat,
                   "scenario": self._scenario(case, owner, seat)}

    def points(self):
        if not self._ready or any(not c["admitted"] for c in self._manifest["cases"]):
            raise ValueError("prospective_source_not_ready_no_reweight_or_replacement")
        for case in self._manifest["cases"][4:]:
            for owner in OWNERS:
                for seat in SEATS:
                    for opponent in OPPONENTS:
                        identity = {"manifest_sha256": self.sha256, "case_id": case["case_id"],
                                    "candidate_team": owner, "seat": seat, "opponent": opponent}
                        yield {**identity, "point_key": fingerprint(identity),
                               "mass": Fraction(1, 1152), "scenario": self._scenario(case, owner, seat)}

    def verify_policy_bindings(self):
        """Hash-only checks; never load a policy or inspect its outputs."""
        for opponent in self._manifest["opponents"].values():
            if opponent["kind"] == "frozen_model":
                if file_sha(opponent["path"]) != opponent["sha256"]:
                    raise ValueError("prospective_frozen_opponent_changed")
            elif opponent["kind"] == "heuristic":
                for relative, expected in opponent["source_sha256"].items():
                    path = (ROOT / relative).resolve()
                    if not path.is_relative_to(ROOT) or file_sha(path) != expected:
                        raise ValueError("prospective_heuristic_source_changed")
            else:
                raise ValueError("prospective_unknown_opponent_kind")
        parent = self._manifest["reference_policy"]
        if file_sha(parent["path"]) != parent["sha256"]:
            raise ValueError("prospective_reference_policy_changed")

    @staticmethod
    def result_key(point, candidate_zip_sha256):
        if (not isinstance(candidate_zip_sha256, str) or len(candidate_zip_sha256) != 64
                or any(c not in "0123456789abcdef" for c in candidate_zip_sha256)):
            raise ValueError("prospective_candidate_identity_required")
        return fingerprint({"point_key": point["point_key"], "candidate_sha256": candidate_zip_sha256})
