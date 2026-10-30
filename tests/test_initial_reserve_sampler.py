"""Pure contract tests: no real simulator/model/optimizer is started here."""
from copy import deepcopy
from fractions import Fraction
import gzip
import json
import random
from types import SimpleNamespace

import numpy as np
import pytest

from advisor import learned_initial_reserves as s


def team(prefix):
    return [{"species": f"{prefix}{i}", "ability": "PublicFixture", "moves": ["Tackle"]} for i in range(6)]


def public_view(case, side):
    other = "opponent" if side == "self" else "self"
    owner = "p1" if side == "self" else "p2"
    opposite = "p2" if side == "self" else "p1"
    history = [f"|poke|{p}|{x['species']}, L50|" for who, p in (("self", "p1"), ("opponent", "p2"))
               for x in case["teams"][who]] + ["|turn|1"]
    mask = [int(i in (1, 2, 6)) for i in range(35)]
    return {"episode_id": "reference", "revision": 0, "side": side, "turn": 1,
            "request_state": "move", "terminated": False, "truncated": False,
            "events": history, "public_history": history,
            "own_request": {"side": {"id": owner, "pokemon": case["preview"][side]}},
            "action_mask": mask, "choices": [str(i) if m else None for i, m in enumerate(mask)],
            "state": {"opponent_side": {"active_identity": f"{opposite}a: slot-{case['preview'][other][0]-1}",
                                         "known_item": {"knowledge": "unknown"}}}}


def checkpoint(case):
    body = {"schema_version": "showdown-environment-checkpoint-v1", "engine_commit": s.SHOWDOWN_COMMIT,
            "format_id": s.FORMAT_ID, "decisions": 0, "max_decisions": 256, "consecutive_rejections": 0,
            "provenance": {"scenario_id": case["scenario_id"]},
            "native_state": {"turn": 1, "prng": case["seed"], "sides": [
                {"pokemon": [{"set": {"name": f"slot-{i-1}"}} for i in case["preview"][who]]}
                for who in ("self", "opponent")]}}
    return {**body, "digest": s.digest(body)}


@pytest.fixture
def harness(tmp_path, monkeypatch):
    data = SimpleNamespace(resets=0, views=[], change=None, save_hook=None)
    data.teams = [team("Own"), team("Foe")] + [team(f"Unused{j}-") for j in range(254)]
    data.case = {"scenario_id": "test-train-7", "teams": {"self": data.teams[0], "opponent": data.teams[1]},
                 "preview": {"self": [1, 2, 3], "opponent": [2, 3, 4]}, "seed": [1, 2, 3, 4]}
    subset_path = tmp_path / "subset.json"; subset_path.write_text("{}")
    checkout = tmp_path / "native"; checkout.mkdir(); (checkout / "stamp").write_text("native-fixture")
    runtime = tmp_path / "runtime.json"
    runtime.write_text(json.dumps({"root": str(checkout), "files": {"stamp": s.file_sha(checkout / "stamp")}}))

    class Subset:
        def __init__(self, *args):
            self.teams = deepcopy(data.teams)
            self.contract = {"schema_version": "showdown-native-training-subset-v3",
                             "selection_mode": "independent_random_ordered3", "team_indices": list(range(256))}
        def __call__(self, split, index):
            assert split == "train" and index == 7
            return deepcopy(data.case)
    monkeypatch.setattr("advisor.learned_training_subset.NativeTrainingSubset", Subset)
    monkeypatch.setattr(s, "source_identity", lambda: {"test-source": "one"})
    monkeypatch.setattr(s, "dependency_identity", lambda: {"test-dependency": "one"})
    monkeypatch.setattr(s, "_canonical_species", lambda *args: [])

    class Encoder:
        version, catalog_fingerprint = "test-public-encoder", "test-fingerprint"
        def encode(self, view):
            assert not s.FORBIDDEN & set(view)
            data.views.append(deepcopy(view))
            return np.array(view["own_request"]["side"]["pokemon"], dtype=np.float32)
    monkeypatch.setattr(s, "_encoder", lambda _: Encoder())

    class Native:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def reset(self, case):
            data.resets += 1; self.case = deepcopy(case)
            if data.change: data.change(self, case)
            return {"terminated": False, "truncated": False, "action_rejected": False}
        def observation(self, side, **kwargs):
            v = public_view(self.case, side); v["episode_id"] = str(data.resets)
            if hasattr(self, "bad_view"): v.update(self.bad_view)
            return v
        def save(self):
            if data.save_hook: data.save_hook(self)
            return checkpoint(self.case)
        def step(self, *args, **kwargs): raise AssertionError("native step is forbidden")
    monkeypatch.setattr(s, "_native", lambda _: Native())

    def plan(side="self", size=3, seed=123):
        pp = tmp_path / f"{side}.public.json"; pp.write_text(json.dumps(public_view(data.case, side)))
        cp = tmp_path / f"{side}.checkpoint.json.gz"; cp.write_bytes(gzip.compress(json.dumps(checkpoint(data.case)).encode()))
        return s.make_plan(subset_path=subset_path, subset_sha256=s.file_sha(subset_path), checkout=checkout,
            runtime_manifest_path=runtime, case_index=7, side=side, initial_seed=[1, 2, 3, 4],
            proposal_seed=seed, sample_size=size, public_path=pp, checkpoint_path=cp)
    data.plan, data.root, data.subset_path = plan, tmp_path, subset_path
    return data


def manifest(result):
    return json.loads(open(result["manifest_path"], encoding="utf-8").read())


def test_default_off_performs_no_io_or_native(monkeypatch):
    monkeypatch.setattr(s, "_validate_plan", lambda _: pytest.fail("disabled IO"))
    monkeypatch.setattr(s, "outside_git", lambda _: pytest.fail("disabled output"))
    assert s.sample_initial_reserves(None, None)["status"] == "disabled"
    for enabled in (1, "true", None):
        with pytest.raises(ValueError, match="boolean_enable"):
            s.sample_initial_reserves(None, None, enabled=enabled)


def test_cli_default_off_does_not_read_nonexistent_plan(capsys):
    from scripts.sample_foundation_initial_reserves import main
    main(["--plan", "nonexistent"])
    assert json.loads(capsys.readouterr().out)["status"] == "disabled"


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_both_seats_exact_h_private_snapshots_and_seed_reproduction(harness, side):
    p = harness.plan(side)
    rng_before = random.getstate()
    a = manifest(s.sample_initial_reserves(p, harness.root / "first", enabled=True))
    b = manifest(s.sample_initial_reserves(p, harness.root / "second", enabled=True))
    assert random.getstate() == rng_before
    assert [x["ordered3"] for x in a["candidates"]] == [x["ordered3"] for x in b["candidates"]]
    assert [x["snapshot"]["content_SHA256"] for x in a["candidates"]] == [x["snapshot"]["content_SHA256"] for x in b["candidates"]]
    assert len(a["unvalidated_not_sampled"]) == 17 and a["selected_verified"] == 3
    assert len(a["excluded_orders"]) == 100 and len(a["excluded_rosters"]) == 255
    assert all(x["side"] == side and not s.FORBIDDEN & set(x) for x in harness.views)
    assert a["native_steps"] == a["PPO"] == a["Adam"] == a["terminal_continuations"] == 0
    assert all(x["proposal_weight"] == "1/3" and x["actual_TRAIN_prior_mass"] is None for x in a["candidates"])


@pytest.mark.parametrize("n", [1, 3, 20])
def test_proposal_weights_never_claim_actual_prior_or_full_hidden_completeness(harness, n):
    m = manifest(s.sample_initial_reserves(harness.plan(size=n), harness.root / "run", enabled=True))
    q = m["probabilities"]
    assert sum(Fraction(x["proposal_weight"]) for x in m["candidates"]) == 1
    assert Fraction(q["untested_pre_admission_proposal_mass"]) == Fraction(20-n, 20)
    assert q["missing_TRAIN_mass"] is q["conditional_TRAIN_prior_mass"] is q["actual_TRAIN_prior_mass"] is None
    assert q["TRAIN_mass_status"] == "unknown" and not m["full_hidden_state_space_complete"]
    assert m["declared_support_fully_verified"] == (n == 20)
    if n == 20:
        assert m["native_starts"] == 20  # Original binding reused, not run twice.
        assert sum(c["snapshot_origin"] == "reused_authenticated_source_binding" for c in m["candidates"]) == 1


@pytest.mark.parametrize("field", ["revision", "events", "public_history", "own_request", "state", "action_mask", "choices"])
def test_uuid_only_tolerance_and_all_public_fields_strict(harness, field):
    view = public_view(harness.case, "self"); changed = deepcopy(view)
    changed["episode_id"] = "new"; s.require_same_public(view, changed)
    changed[field] = None
    with pytest.raises(ValueError, match="public_input_mismatch"): s.require_same_public(view, changed)


@pytest.mark.parametrize("field", sorted(s.FORBIDDEN))
def test_privileged_even_identical_payload_rejected(harness, field):
    v = public_view(harness.case, "self"); v[field] = "hidden"
    with pytest.raises(ValueError, match="privileged"): s.require_same_public(v, v)


@pytest.mark.parametrize("key,value", [("initial_seed", [9, 2, 3, 4]), ("side", "invalid"), ("sample_size", 21),
                                      ("case_index", -1), ("proposal_seed", True)])
def test_invalid_plan_or_seed_stops_before_native(harness, key, value):
    p = harness.plan(); p[key] = value
    with pytest.raises(ValueError): s.sample_initial_reserves(p, harness.root / "bad", enabled=True)
    assert harness.resets == 0


def test_public_unknown_is_not_established_absence(harness):
    v = public_view(harness.case, "self"); b = deepcopy(v)
    b["state"]["opponent_side"]["known_item"] = {"knowledge": "absent"}
    with pytest.raises(ValueError): s.require_same_public(v, b)


def test_scope_unique_roster_illusion_and_later_root(harness):
    p = harness.plan()
    harness.teams[2] = deepcopy(harness.teams[1])
    with pytest.raises(ValueError, match="nonunique"): s.sample_initial_reserves(p, harness.root / "duplicate-roster", enabled=True)
    assert harness.resets == 0
    harness.teams[2] = team("Unused-new")
    harness.teams[1][0]["ability"] = "Illusion"
    with pytest.raises(ValueError, match="Illusion"): s.sample_initial_reserves(p, harness.root / "illusion", enabled=True)
    assert harness.resets == 0
    harness.teams[1][0]["ability"] = "PublicFixture"
    path = p["reference_public"]["path"]; v = json.loads(open(path).read()); v["turn"] = 2
    open(path, "w").write(json.dumps(v)); p["reference_public"]["sha256"] = s.file_sha(path)
    with pytest.raises(ValueError, match="initial_root"): s.sample_initial_reserves(p, harness.root / "later", enabled=True)
    assert harness.resets == 0


def test_source_or_runtime_conflict_never_starts_native(harness, monkeypatch):
    p = harness.plan(); monkeypatch.setattr(s, "source_identity", lambda: {"changed": True})
    with pytest.raises(ValueError, match="source_or_dependency"): s.sample_initial_reserves(p, harness.root / "source", enabled=True)
    assert harness.resets == 0


def test_runtime_and_dependency_provenance_fail_before_native(harness, monkeypatch):
    p = harness.plan()
    (harness.root / "native/stamp").write_text("changed native file")
    with pytest.raises(ValueError, match="runtime_file_conflict"):
        s.sample_initial_reserves(p, harness.root / "runtime-conflict", enabled=True)
    assert harness.resets == 0
    (harness.root / "native/stamp").write_text("native-fixture")
    monkeypatch.setattr(s, "dependency_identity", lambda: {"test-dependency": "changed"})
    with pytest.raises(ValueError, match="dependency_conflict"):
        s.sample_initial_reserves(p, harness.root / "dependency-conflict", enabled=True)
    assert harness.resets == 0


def test_native_illegality_records_started_failed_and_no_replacement(harness):
    from advisor.showdown_environment import ShowdownEnvironmentError
    def reject(obj, case):
        if harness.resets > 1: raise ShowdownEnvironmentError("invalid_mc_team")
    harness.change = reject
    with pytest.raises(ShowdownEnvironmentError):
        s.sample_initial_reserves(harness.plan(size=20), harness.root / "illegal", enabled=True)
    rows = [json.loads(x) for x in (harness.root / "illegal/private/native_ledger.jsonl").read_text().splitlines()]
    assert [x["phase"] for x in rows][-2:] == ["started", "failed"]
    assert harness.resets == 2 and not (harness.root / "illegal/run.json").exists()


def test_encoder_mismatch_cannot_hide_behind_public_mapping_equality(harness, monkeypatch):
    class Encoder:
        version, catalog_fingerprint = "bad", "bad"
        def __init__(self): self.calls = 0
        def encode(self, view):
            self.calls += 1
            return np.array([self.calls], dtype=np.float32)
    monkeypatch.setattr(s, "_encoder", lambda _: Encoder())
    with pytest.raises(ValueError, match="source_feature_conflict"):
        s.sample_initial_reserves(harness.plan(), harness.root / "bad-encoder", enabled=True)
    assert harness.resets == 1


@pytest.mark.parametrize("change", ["dtype", "shape", "signed_zero"])
def test_feature_bytes_contract_is_stricter_than_numeric_array_equality(change):
    a = np.array([0., 1.], dtype=np.float32)
    if change == "dtype": b = a.astype(np.float64)
    elif change == "shape": b = a.reshape(1, 2)
    else: b = np.array([-0., 1.], dtype=np.float32)
    assert not s._same_feature_bytes(a, b)
    assert s._same_feature_bytes(a, a.copy())


def test_candidate_dtype_change_fails_whole_batch(harness, monkeypatch):
    class Encoder:
        version, catalog_fingerprint = "bad-dtype", "bad-dtype"
        def __init__(self): self.calls = 0
        def encode(self, view):
            self.calls += 1
            return np.array([1.], dtype=np.float32 if self.calls <= 2 else np.float64)
    monkeypatch.setattr(s, "_encoder", lambda _: Encoder())
    with pytest.raises(ValueError, match="candidate_feature_conflict"):
        s.sample_initial_reserves(harness.plan(size=20), harness.root / "dtype", enabled=True)
    assert not (harness.root / "dtype/run.json").exists()


def test_native_selection_and_duplicate_world_binding(harness, monkeypatch):
    original_factory = s._native
    def factory(checkout):
        obj = original_factory(checkout)
        original_save = obj.save
        def save():
            cp = original_save()
            if harness.resets > 1:
                cp["native_state"]["sides"][1]["pokemon"] = checkpoint(harness.case)["native_state"]["sides"][1]["pokemon"]
            return cp
        obj.save = save
        return obj
    monkeypatch.setattr(s, "_native", factory)
    with pytest.raises(ValueError, match="native_selection_binding_conflict"):
        s.sample_initial_reserves(harness.plan(size=20), harness.root / "bad-selection", enabled=True)


def test_outputs_cannot_be_inside_any_git_worktree(harness):
    fake_repo = harness.root / "repo"; fake_repo.mkdir(); (fake_repo / ".git").write_text("gitdir: elsewhere")
    with pytest.raises(ValueError, match="non_git_directory"):
        s.sample_initial_reserves(harness.plan(), fake_repo / "samples", enabled=True)
    assert harness.resets == 0


def test_illegal_or_mismatched_candidate_poison_entire_batch(harness):
    p = harness.plan(size=20)
    harness.change = lambda obj, case: setattr(obj, "bad_view", {"events": ["new public event"]}) if harness.resets > 1 else None
    with pytest.raises(ValueError, match="public_input_mismatch"): s.sample_initial_reserves(p, harness.root / "bad", enabled=True)
    failure = json.loads((harness.root / "bad/private/failure.json").read_text())
    assert not failure["partial_samples_usable"] and not (harness.root / "bad/run.json").exists()
    before = harness.resets
    with pytest.raises(FileExistsError): s.sample_initial_reserves(p, harness.root / "bad", enabled=True)
    assert harness.resets == before


def test_source_checkpoint_and_selected_slot_must_bind(harness):
    p = harness.plan()
    path = p["reference_checkpoint"]["path"]
    cp = json.loads(gzip.decompress(open(path, "rb").read())); cp["native_state"]["prng"] = [9, 9, 9, 9]
    open(path, "wb").write(gzip.compress(json.dumps(cp).encode())); p["reference_checkpoint"]["sha256"] = s.file_sha(path)
    with pytest.raises(ValueError, match="native_source_checkpoint"): s.sample_initial_reserves(p, harness.root / "bad", enabled=True)
    assert harness.resets == 1


def test_source_drift_after_collection_aborts_no_reweight(harness):
    p = harness.plan()
    def change_after_save(obj):
        if harness.resets > 1: harness.subset_path.write_text("changed input")
    harness.save_hook = change_after_save
    with pytest.raises(ValueError, match="input_SHA_conflict"): s.sample_initial_reserves(p, harness.root / "bad", enabled=True)
    assert not (harness.root / "bad/private/manifest.json").exists()


def test_STOP_storage_and_native_caps(harness, monkeypatch):
    p = harness.plan()
    with pytest.raises(TimeoutError): s.sample_initial_reserves(p, harness.root / "stop", enabled=True, stopping=lambda: True)
    assert harness.resets == 0
    monkeypatch.setattr(s, "MAX_BYTES", 1)
    with pytest.raises(ValueError, match="storage_cap"): s.sample_initial_reserves(p, harness.root / "storage", enabled=True)
    monkeypatch.setattr(s, "MAX_BYTES", 4*1024*1024); monkeypatch.setattr(s, "MAX_STARTS", 1)
    with pytest.raises(ValueError, match="start_cap"): s.sample_initial_reserves(p, harness.root / "starts", enabled=True)


def test_duplicate_proposal_cannot_be_silently_deduplicated(monkeypatch):
    monkeypatch.setattr(s.random, "Random", lambda _: SimpleNamespace(sample=lambda pool, n: [pool[0]] * n))
    with pytest.raises(ValueError, match="duplicate_proposal"): s.candidate_orders(1, 1, 2)
