"""Experimental coordinator-only team candidates; no battle/evaluation adapter.

Legality belongs exclusively to the pinned native TeamValidator. Complete-team
novelty is independent of individual-set novelty and competitive usefulness.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import subprocess

from advisor.showdown_bridge import FORMAT_ID, SHOWDOWN_COMMIT, silent_process_options
from scripts.build_showdown_full_roster import set_identity

VERSION = "independent-train-development-team-source-v1"
VALIDATION_VERSION = "showdown-team-validation-only-v1"
ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_sha(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def token(value):
    if not isinstance(value, str):
        raise ValueError("team_identity_string_required")
    return re.sub("[^a-z0-9]", "", value.lower())


def set_key(member):
    """Reuse V8's set hash with public native spelling normalized for identity.

    Ignore nickname and move order, never rewrite the actual source roster.
    Missing defaults stay missing; joint-moveset exclusion additionally catches
    reused complete teams with alternate stat/default transport.
    """
    p = deepcopy(member)
    for field in ("species", "ability", "item", "nature", "gender"):
        if field in p:
            p[field] = token(p[field])
    if not token(p.get("species", "")) or not isinstance(p.get("moves"), list):
        raise ValueError("full_native_set_required")
    p["moves"] = [token(m) for m in p["moves"]]
    if not 1 <= len(p["moves"]) <= 4 or any(not m for m in p["moves"]):
        raise ValueError("full_native_move_slots_required")
    return set_identity(p)


def team_identity(team):
    if not isinstance(team, list) or len(team) != 6:
        raise ValueError("full_six_source_roster_required")
    sets = [set_key(p) for p in team]
    return {"ordered": digest(team), "semantic": digest(sorted(sets)),
            "joint_movesets": digest(sorted((token(p["species"]), sorted(map(token, p["moves"])))
                                             for p in team)),
            "roster": digest(sorted(token(p["species"]) for p in team))}


def admit(teams, excluded):
    """One deterministic pass. No redraws, team mutation or outcome selection."""
    used = {kind: set() for kind in ("semantic", "joint_movesets")}
    accepted, indices, records = [], [], []
    for i, team in enumerate(teams):
        keys = team_identity(team)
        reasons = ["excluded_" + k for k in used if keys[k] in excluded[k]]
        reasons += ["duplicate_" + k for k in used if keys[k] in used[k]]
        records.append({"generation_index": i, "identity": keys,
                        "accepted": not reasons, "reasons": reasons})
        if reasons:
            continue
        accepted.append(deepcopy(team)); indices.append(i)
        for kind in used:
            used[kind].add(keys[kind])
    return accepted, indices, records


def native_validate(checkout, teams):
    """Validation-only native command. No reset, Battle, step or policy call."""
    if not isinstance(teams, list) or not 1 <= len(teams) <= 256:
        raise ValueError("bounded_team_validation_required")
    request = {"schema_version": VALIDATION_VERSION, "teams": teams}
    result = subprocess.run(
        ["node", str(ROOT / "tools/showdown_bridge/validate-teams.cjs"), str(Path(checkout).resolve())],
        input=json.dumps(request, ensure_ascii=False), text=True, encoding="utf-8",
        capture_output=True, timeout=120, **silent_process_options())
    if result.returncode:
        raise ValueError("native_validation_command_failed")
    response = json.loads(result.stdout)
    if (response.get("schema_version") != VALIDATION_VERSION
            or response.get("engine_commit") != SHOWDOWN_COMMIT or response.get("format_id") != FORMAT_ID
            or response.get("input_SHA256") != digest(teams)
            or [r.get("index") for r in response.get("results", [])] != list(range(len(teams)))
            or any(type(r.get("valid")) is not bool or not isinstance(r.get("errors"), list)
                   for r in response["results"])):
        raise ValueError("native_validation_binding_mismatch")
    return response


def composition(teams):
    counters = {k: Counter() for k in ("species", "moves", "ability", "item", "nature", "stat_max", "move_count")}
    for team in teams:
        for p in team:
            for field in ("species", "ability", "item", "nature"):
                counters[field][token(p.get(field, "")) or "known_absence"] += 1
            counters["moves"].update(map(token, p["moves"]))
            counters["stat_max"][str(max(p.get("evs", {"unknown": -1}).values()))] += 1
            counters["move_count"][str(len(p["moves"]))] += 1
    return {k: dict(sorted(v.items())) for k, v in counters.items()}


def compare_distribution(new, reference):
    """Descriptive finite-source TV/Jensen-Shannon, not an equivalence test."""
    a, b = composition(new), composition(reference)
    out = {}
    for field in a:
        keys = set(a[field]) | set(b[field]); na = sum(a[field].values()); nb = sum(b[field].values())
        pa = {k: a[field].get(k, 0) / na for k in keys}
        pb = {k: b[field].get(k, 0) / nb for k in keys}
        js = 0.
        for k in keys:
            m = (pa[k] + pb[k]) / 2
            for p in (pa[k], pb[k]):
                if p:
                    js += .5 * p * math.log2(p / m)
        out[field] = {"TV": .5 * sum(abs(pa[k] - pb[k]) for k in keys),
                      "JS_bits": js, "new_support": len(a[field]), "V8_TRAIN_support": len(b[field])}
    return out


def set_reuse(teams, reference):
    old = {set_key(p) for t in reference for p in t}
    members = [set_key(p) for t in teams for p in t]; unique = set(members)
    return {"member_slots": len(members), "unique_sets": len(unique),
            "reused_slots": sum(s in old for s in members),
            "reused_slot_fraction": sum(s in old for s in members) / len(members),
            "reused_unique_sets": len(unique & old),
            "reused_unique_set_fraction": len(unique & old) / len(unique)}


def load_candidates(path, expected_sha256):
    """Validate a frozen candidate source; intentionally provides no scenarios."""
    path = Path(path).resolve()
    if file_sha(path) != expected_sha256:
        raise ValueError("candidate_manifest_hash_mismatch")
    m = json.loads(path.read_text(encoding="utf-8"))
    if (m.get("schema_version") != VERSION or m.get("engine_commit") != SHOWDOWN_COMMIT
            or m.get("format_id") != FORMAT_ID or m.get("evaluation_approved") is not False
            or m.get("battle_execution_approved") is not False):
        raise ValueError("candidate_source_authority_mismatch")
    assets = {}
    if set(m.get("assets", {})) != {"teams", "generation", "validation", "admissions", "audit", "statistics"}:
        raise ValueError("candidate_required_assets_missing")
    for name, binding in m["assets"].items():
        relative = Path(binding["path"]); target = (path.parent / relative).resolve()
        if relative.is_absolute() or ".." in relative.parts or not target.is_relative_to(path.parent):
            raise ValueError("candidate_asset_path_escape")
        if file_sha(target) != binding["sha256"]:
            raise ValueError("candidate_asset_hash_mismatch")
        assets[name] = json.loads(target.read_text(encoding="utf-8"))
    teams = assets["teams"]["teams"]; generation = assets["generation"]; validation = assets["validation"]
    indices = m["generation_indices"]
    if (type(m.get("minimum_teams")) is not int or m["minimum_teams"] < 128
            or len(teams) < m["minimum_teams"] or m["teams"] != len(teams)
            or indices != sorted(set(indices)) or len(indices) != len(teams)
            or any(type(i) is not int or not 0 <= i < len(generation["teams"]) for i in indices)
            or teams != [generation["teams"][i] for i in indices]
            or generation.get("seed") != m["generation_seed"]
            or generation.get("engine_commit") != SHOWDOWN_COMMIT or generation.get("format_id") != FORMAT_ID
            or generation.get("inventory_sha256") != m["inventory_SHA256"]
            or validation.get("schema_version") != VALIDATION_VERSION
            or validation.get("engine_commit") != SHOWDOWN_COMMIT or validation.get("format_id") != FORMAT_ID
            or validation.get("input_SHA256") != digest(generation["teams"])
            or [r.get("index") for r in validation.get("results", [])] != list(range(len(generation["teams"])))
            or any(r.get("valid") is not True or r.get("errors") for r in validation["results"])):
        raise ValueError("candidate_native_binding_mismatch")
    keys = [team_identity(t) for t in teams]
    if (keys != m["team_identities"] or any(len({k[f] for k in keys}) != len(teams)
                                           for f in ("semantic", "joint_movesets"))):
        raise ValueError("candidate_team_identity_mismatch")
    expected_pairs = [{"pair": i, "team_indices": [2*i, 2*i+1]} for i in range(len(teams)//2)]
    if m["pairs"] != expected_pairs or len(m["pairs"]) < 64:
        raise ValueError("candidate_pair_binding_mismatch")
    audit, admissions = assets["audit"], assets["admissions"]
    if (any(audit.get(k) != 0 for k in ("semantic_full_team_overlap", "joint_moveset_full_team_overlap", "duplicate_new_teams"))
            or audit.get("reproducible_batch_SHA256") != digest(generation)
            or audit.get("native_accepted") != len(generation["teams"])
            or len(admissions) != len(generation["teams"])
            or [a.get("generation_index") for a in admissions] != list(range(len(generation["teams"])))
            or [a["generation_index"] for a in admissions if a.get("accepted") is True] != indices
            or any(a["identity"] != team_identity(generation["teams"][i]) for i, a in enumerate(admissions))
            or any(bool(a.get("reasons")) == a["accepted"] for a in admissions)):
        raise ValueError("candidate_novelty_audit_mismatch")
    return deepcopy(m), deepcopy(teams)
