"""Synthetic structural fixtures only; real native protocol checks are opt-in outside tests."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import pytest
from advisor.learned_prospective_evaluation import (
    ProspectiveEvaluationSource, VERSION, READY_VERSION, OPPONENTS,
    SHOWDOWN_COMMIT, FORMAT_ID, file_sha, generate_team_batch,
)


def write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return file_sha(path)


@pytest.fixture
def source_fixture(tmp_path):
    # These are structural data, not a native legality attestation/test battle.
    teams = [[{"species": f"Example-{j}-{i}", "moves": ["tackle"]} for i in range(6)] for j in range(200)]
    asset = tmp_path / "teams.json"
    binding = {"path": asset.name, "sha256": write(asset, {"engine_commit": SHOWDOWN_COMMIT,
        "format_id": FORMAT_ID, "teams": teams})}
    cases = []
    for i in range(100):
        cases.append({"index": 161031000+i, "case_id": f"fixture-{i}",
            "partition": "protocol" if i < 4 else "sealed", "team_indices": {"a": 2*i, "b": 2*i+1},
            "ordered3": {"a": [6, 1, 3], "b": [2, 5, 4]}, "admitted": True,
            "native_seeds": {owner+":"+seat: [i, a, b, 0] for a,owner in enumerate(("a", "b"))
                             for b,seat in enumerate(("self", "opponent"))}})
    model = tmp_path / "frozen.zip"
    model.write_bytes(b"synthetic-frozen-policy-binding")
    frozen = {"kind": "frozen_model", "path": str(model), "sha256": file_sha(model)}
    manifest = {"schema_version": VERSION, "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID,
        "native_team_validated": True, "team_asset": binding, "cases": cases,
        "opponent_order": list(OPPONENTS), "opponents": {key: dict(frozen) for key in OPPONENTS},
        "reference_policy": dict(frozen),
        "measure": {"name": "Q_eval_source_v1", "cases": 96, "owners": ["a", "b"],
            "seats": ["self", "opponent"], "opponents": list(OPPONENTS), "points": 1152,
            "point_mass": "1/1152", "case_mass": "1/96", "renormalize": False,
            "historical_TRAIN_prior": False}}
    path = tmp_path / "manifest.json"
    digest = write(path, manifest)
    protocol = tmp_path / "protocol.json"; novelty = tmp_path / "novelty.json"
    ph = write(protocol, {"synthetic_structural_fixture": True, "status": "PASS", "manifest_sha256": digest,
        "native_starts": 6, "native_steps": 0, "terminal_games": 0, "model_forwards": 0})
    nh = write(novelty, {"synthetic_structural_fixture": True, "status": "PASS", "manifest_sha256": digest,
        "sealed_cases": 96, "all_cases_admitted": True, "old_semantic_team_overlap": 0,
        "old_base_roster_overlap": 0, "old_seed_overlap": 0, "old_case_id_overlap": 0})
    ready = tmp_path / "ready.json"
    rh = write(ready, {"schema_version": READY_VERSION, "status": "SEALED_EVAL_SOURCE_READY",
        "manifest_sha256": digest, "protocol_audit": {"path": protocol.name, "sha256": ph},
        "novelty_audit": {"path": novelty.name, "sha256": nh}})
    return path, digest, ready, rh, manifest


def load(fixture):
    path, digest, ready, rh, _ = fixture
    return ProspectiveEvaluationSource(path, digest, readiness=ready, readiness_sha256=rh)


def test_exact_finite_support_and_no_protocol_cases(source_fixture):
    points = list(load(source_fixture).points())
    assert len(points) == len({p["point_key"] for p in points}) == 1152
    assert len({p["case_id"] for p in points}) == 96
    assert sum((p["mass"] for p in points), Fraction()) == 1
    assert not {f"fixture-{i}" for i in range(4)} & {p["case_id"] for p in points}


@pytest.mark.parametrize("owner", ["a", "b"])
@pytest.mark.parametrize("seat", ["self", "opponent"])
def test_real_seat_and_ordered_three_bindings(source_fixture, owner, seat):
    source = load(source_fixture)
    p = next(p for p in source.points() if p["candidate_team"] == owner and p["seat"] == seat)
    other = "opponent" if seat == "self" else "self"
    expected = 8 if owner == "a" else 9
    assert p["scenario"]["teams"][seat][0]["species"] == f"Example-{expected}-0"
    assert p["scenario"]["preview"][seat] == ([6, 1, 3] if owner == "a" else [2, 5, 4])
    assert p["scenario"]["teams"][other][0]["species"] != p["scenario"]["teams"][seat][0]["species"]


def test_same_physical_seed_across_opponents_and_unique_result_keys(source_fixture):
    source = load(source_fixture); points = list(source.points())
    assert points[0]["scenario"] == points[1]["scenario"] == points[2]["scenario"]
    assert source.result_key(points[0], "a"*64) != source.result_key(points[0], "b"*64)
    assert source.result_key(points[0], "a"*64) != source.result_key(points[1], "a"*64)


def test_no_readiness_or_failed_admission_cannot_renormalize(source_fixture):
    path, digest, ready, rh, m = source_fixture
    with pytest.raises(ValueError, match="not_ready"):
        list(ProspectiveEvaluationSource(path, digest).points())
    m["cases"][5]["admitted"] = False
    newsha = write(path, m)
    with pytest.raises(ValueError, match="not_ready"):
        list(ProspectiveEvaluationSource(path, newsha).points())


@pytest.mark.parametrize("audit,key,value", [
    ("protocol_audit", "native_steps", 1), ("protocol_audit", "manifest_sha256", "x"*64),
    ("novelty_audit", "old_semantic_team_overlap", 1), ("novelty_audit", "status", "FAIL"),
])
def test_readiness_checks_bound_audit_results(source_fixture, audit, key, value):
    path, digest, ready, _, _ = source_fixture
    receipt = json.loads(ready.read_text()); target = path.parent / receipt[audit]["path"]
    result = json.loads(target.read_text()); result[key] = value
    receipt[audit]["sha256"] = write(target, result)
    with pytest.raises(ValueError, match="audit_failed"):
        ProspectiveEvaluationSource(path, digest, readiness=ready, readiness_sha256=write(ready, receipt))


def test_public_mutations_do_not_change_cached_source(source_fixture):
    source = load(source_fixture); original = next(source.points())
    view = source.manifest; view["cases"][4]["ordered3"]["a"] = [1, 2, 3]
    original["scenario"]["teams"]["self"][0]["species"] = "mutated"
    assert next(source.points())["scenario"]["teams"]["self"][0]["species"] == "Example-8-0"
    with pytest.raises(AttributeError): source.ready = True
    with pytest.raises(AttributeError): source.sha256 = "x"


@pytest.mark.parametrize("mutation", ["mass", "duplicate_seed", "preview", "case", "partition"])
def test_structural_contract_changes_fail_closed(source_fixture, mutation):
    path, _, _, _, m = source_fixture
    if mutation == "mass": m["measure"]["point_mass"] = "1/1000"
    if mutation == "duplicate_seed": m["cases"][1]["native_seeds"] = deepcopy(m["cases"][0]["native_seeds"])
    if mutation == "preview": m["cases"][0]["ordered3"]["a"] = [1, 1, 2]
    if mutation == "case": m["cases"][1]["case_id"] = m["cases"][0]["case_id"]
    if mutation == "partition": m["cases"][4]["partition"] = "protocol"
    with pytest.raises(ValueError): ProspectiveEvaluationSource(path, write(path, m))


def test_asset_mutation_and_path_escape_fail_closed(source_fixture):
    path, digest, _, _, m = source_fixture
    asset = path.parent / "teams.json"; asset.write_text("{}")
    with pytest.raises(ValueError, match="asset_hash"): ProspectiveEvaluationSource(path, digest)
    m["team_asset"]["path"] = "../escape.json"
    with pytest.raises(ValueError, match="asset_path"): ProspectiveEvaluationSource(path, write(path, m))


def test_policy_hash_change_fails_without_loading_a_model(source_fixture):
    source = load(source_fixture); source.verify_policy_bindings()
    Path(source.manifest["reference_policy"]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="opponent_changed"): source.verify_policy_bindings()


@pytest.mark.parametrize("seed,count", [([1, 2, 3], 200), ([1, 2, 3, 65536], 200), ([1, 2, 3, 4], 201)])
def test_generation_budget_rejected_without_native(seed, count):
    with pytest.raises(ValueError, match="bounded"): generate_team_batch("unused", seed=seed, count=count)
