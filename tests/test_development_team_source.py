"""Source-only structural tests; synthetic teams do not attest native legality."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest

from advisor.learned_development_team_source import (
    VERSION, VALIDATION_VERSION, SHOWDOWN_COMMIT, FORMAT_ID, admit, team_identity,
    digest, file_sha, native_validate, load_candidates, set_reuse, compare_distribution,
)
from scripts.build_independent_development_teams import invalid_fixtures, load_exclusions


def team(i):
    return [{"species": f"Example-{i}-{j}", "moves": ["Tackle", "Protect"], "item": "",
             "ability": "Example", "nature": "Hardy", "evs": {"hp": 11, "atk": 11, "def": 11,
             "spa": 11, "spd": 11, "spe": 11}} for j in range(6)]


def test_identity_ignores_nickname_team_order_and_move_slots_without_mutation():
    a = team(1); original = deepcopy(a); b = deepcopy(a[::-1])
    for p in b:
        p["name"] = "nickname"; p["moves"].reverse(); p["species"] = p["species"].upper()
    ka, kb = team_identity(a), team_identity(b)
    assert ka["ordered"] != kb["ordered"]
    assert all(ka[k] == kb[k] for k in ("semantic", "joint_movesets", "roster"))
    assert a == original


def test_complete_team_exclusion_and_stricter_joint_movesets():
    a = team(1); b = deepcopy(a); b[0]["evs"]["hp"] = 12
    assert team_identity(a)["semantic"] != team_identity(b)["semantic"]
    excluded = {k: {team_identity(a)[k]} for k in ("semantic", "joint_movesets")}
    accepted, indices, rows = admit([a, b, team(2), team(2)[::-1]], excluded)
    assert accepted == [team(2)] and indices == [2]
    assert rows[1]["reasons"] == ["excluded_joint_movesets"]
    assert "duplicate_semantic" in rows[3]["reasons"]


def test_individual_sets_may_recur_without_complete_team_reuse():
    a = team(1); b = team(2); b[0] = deepcopy(a[0])
    excluded = {k: {team_identity(a)[k]} for k in ("semantic", "joint_movesets")}
    assert admit([b], excluded)[0] == [b]
    r = set_reuse([b], [a]); assert r["reused_slots"] == r["reused_unique_sets"] == 1
    assert r["reused_slot_fraction"] == 1/6


@pytest.mark.parametrize("bad", [[], team(1)[:5], [dict(team(1)[0], moves=[])] * 6,
                                      [dict(team(1)[0], species=123)] * 6])
def test_malformed_identity_rejected(bad):
    with pytest.raises(ValueError): team_identity(bad)


def test_distribution_comparison_is_bounded_and_identical_reference_is_zero():
    same = compare_distribution([team(1)], [team(1)])
    assert all(x["TV"] == 0 and x["JS_bits"] == 0 for x in same.values())
    different = compare_distribution([team(2)], [team(1)])
    assert different["species"]["TV"] == different["species"]["JS_bits"] == 1
    assert all(0 <= x["TV"] <= 1 and 0 <= x["JS_bits"] <= 1 for x in different.values())


def write(p, value):
    p.write_text(json.dumps(value), encoding="utf-8"); return file_sha(p)


@pytest.fixture
def source(tmp_path):
    teams = [team(i) for i in range(128)]
    generation = {"teams": teams, "seed": [1,2,3,4], "inventory_sha256": "fixture-inventory",
                  "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID}
    validation = {"schema_version": VALIDATION_VERSION, "engine_commit": SHOWDOWN_COMMIT,
                  "format_id": FORMAT_ID, "input_SHA256": digest(teams),
                  "results": [{"index": i, "valid": True, "errors": []} for i in range(128)]}
    admissions = [{"generation_index": i, "identity": team_identity(t), "accepted": True, "reasons": []}
                  for i, t in enumerate(teams)]
    values = {"teams": {"teams": teams}, "generation": generation, "validation": validation,
              "admissions": admissions, "statistics": {},
              "audit": {"semantic_full_team_overlap": 0, "joint_moveset_full_team_overlap": 0,
                        "duplicate_new_teams": 0, "reproducible_batch_SHA256": digest(generation), "native_accepted": 128}}
    assets = {k: {"path": k+".json", "sha256": write(tmp_path/(k+".json"), v)} for k, v in values.items()}
    m = {"schema_version": VERSION, "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID,
         "evaluation_approved": False, "battle_execution_approved": False,
         "assets": assets, "generation_seed": [1,2,3,4], "inventory_SHA256": "fixture-inventory",
         "generation_indices": list(range(128)), "teams": 128, "minimum_teams": 128,
         "team_identities": [team_identity(t) for t in teams],
         "pairs": [{"pair": i, "team_indices": [2*i, 2*i+1]} for i in range(64)]}
    p = tmp_path/"manifest.json"; return p, write(p,m), m


def test_candidate_manifest_roundtrip_has_no_evaluation_authorization(source):
    p, h, _ = source; m, teams = load_candidates(p, h)
    assert len(m["pairs"]) == 64 and len(teams) == 128
    assert not m["evaluation_approved"] and not m["battle_execution_approved"]
    teams[0][0]["species"] = "changed"
    assert load_candidates(p,h)[1][0][0]["species"] != "changed"


@pytest.mark.parametrize("mutation", ["authorization", "seed", "pair", "index", "identity", "authority", "minimum"])
def test_contract_mutations_fail_closed(source, mutation):
    p, _, m = source
    if mutation == "authorization": m["battle_execution_approved"] = True
    if mutation == "seed": m["generation_seed"][0] = 9
    if mutation == "pair": m["pairs"][0]["team_indices"].reverse()
    if mutation == "index": m["generation_indices"][0] = -1
    if mutation == "identity": m["team_identities"][0]["semantic"] = "changed"
    if mutation == "authority": m["engine_commit"] = "changed"
    if mutation == "minimum": m["minimum_teams"] = 1
    with pytest.raises(ValueError): load_candidates(p,write(p,m))


def test_asset_mutation_path_escape_and_manifest_sha_fail_closed(source):
    p, h, m = source
    with pytest.raises(ValueError, match="manifest_hash"): load_candidates(p,"bad")
    m["assets"]["teams"]["path"] = "../escape.json"
    with pytest.raises(ValueError, match="path_escape"): load_candidates(p,write(p,m))


@pytest.mark.parametrize("asset", ["validation", "audit", "admissions"])
def test_forged_attestations_fail_even_with_updated_asset_hash(source, asset):
    p, _, m = source; q = p.parent/m["assets"][asset]["path"]; v = json.loads(q.read_text())
    if asset == "validation": v["results"][0]["valid"] = False
    if asset == "audit": v["semantic_full_team_overlap"] = 1
    if asset == "admissions": v[0]["accepted"] = False
    m["assets"][asset]["sha256"] = write(q,v)
    with pytest.raises(ValueError): load_candidates(p,write(p,m))


@pytest.mark.parametrize("bad", [[], [team(1)] * 257, None])
def test_validator_budget_rejection_never_launches_native(monkeypatch, bad):
    monkeypatch.setattr("subprocess.run", lambda *a, **k: pytest.fail("unexpected native process"))
    with pytest.raises(ValueError): native_validate("unused",bad)


def test_native_response_input_binding_is_checked(monkeypatch):
    monkeypatch.setattr("subprocess.run", lambda *a, **k: SimpleNamespace(returncode=0,stdout="{}"))
    with pytest.raises(ValueError, match="binding"): native_validate("unused",[team(1)])


def test_exclusion_sources_fail_hash_check_before_loading(tmp_path):
    p = tmp_path/"source.json"; p.write_text("{}")
    with pytest.raises(ValueError, match="hash_changed"):
        load_exclusions([{"kind":"pilot_plan", "path":str(p), "sha256":"bad"}])


def test_invalid_fixture_names_are_explicit_and_do_not_mutate_source():
    a=team(1); old=deepcopy(a); fixtures=invalid_fixtures(a)
    assert len(fixtures)==5 and a==old and len(fixtures["not_full_six"])==5
