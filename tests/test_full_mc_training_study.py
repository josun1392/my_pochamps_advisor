"""Full-roster experiment isolation, explicit conversion and telemetry integrity."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("sb3_contrib")
from advisor.learned_catalog_conversion import validate_extension, convert_checkpoint
from advisor.learned_full_roster import load_bank, VERSION, study_identity
from advisor.learned_full_domain import DOMAIN, load_inventory
from advisor.learned_gym import ShowdownLearningEnv
from advisor.learned_action_encoder import make_encoder
from advisor.learned_policy import LearnedPolicy
from advisor.learned_scenarios import scenario
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learned_baselines import VisibleBaseline
from scripts.build_showdown_full_roster import set_identity
from scripts.train_showdown_autonomous import (
    training_config_fingerprint,
    validate_config,
)

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "models/showdown_initial_v1/catalog.json"
NEW = DOMAIN / "catalog.json"


def test_catalog_extension_rejects_changed_or_removed_facts():
    old, new = json.loads(OLD.read_text()), json.loads(NEW.read_text())
    assert len(validate_extension(old, new)) == 68
    for section, key in (
        ("species", "pikachu"),
        ("moves", "tackle"),
        ("effectiveness", "Fire"),
    ):
        changed = deepcopy(new)
        del changed[section][key]
        with pytest.raises(ValueError, match="existing_feature_changed"):
            validate_extension(old, changed)


def test_bank_complete_roster_and_joint_moveset_partitions():
    bank = load_bank()
    assert len(bank["coverage"]["train"]["base_species"]) == 231
    assert set(bank["train_base_species"]) == set(load_inventory()["base_species"])
    assert len(bank["coverage"]["train"]["moves"]) == 510
    assert len(bank["rare_form_constraints"]) == 82
    seen_teams, seen_movesets = set(), set()
    for split, teams in bank["teams"].items():
        complete = {tuple(sorted(set_identity(p) for p in team)) for team in teams}
        move_combinations = {
            tuple(sorted((p["species"], tuple(sorted(p["moves"]))) for p in team))
            for team in teams
        }
        assert not seen_teams & complete
        assert not seen_movesets & move_combinations
        seen_teams.update(complete)
        seen_movesets.update(move_combinations)
    case = scenario("train", 16431, version=VERSION)
    assert case == scenario("train", 16431, version=VERSION)
    assert case != scenario("test", 16431, version=VERSION)
    assert "No species- or individual-set-unseen claim" in bank["partition_scope"]


def test_v8_config_fingerprints_bind_content():
    config = json.loads((ROOT / "config/learning/full_mc_roster_cpu.json").read_text())
    validate_config(config)
    fingerprint, identity = training_config_fingerprint(config)
    assert identity == study_identity(NEW)
    assert identity["curriculum_version"] == VERSION
    changed = deepcopy(config)
    changed["experiments"][0]["seed"] += 1
    assert training_config_fingerprint(changed)[0] != fingerprint


def test_conversion_keeps_native_known_feature_inference_and_zip(tmp_path):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("pinned engine required")
    source = ROOT / "models/showdown_strong_policy_experiment/learner_2477/model.zip"
    converted = convert_checkpoint(source, OLD, NEW, tmp_path / "converted")
    assert (
        sha256(Path(converted).read_bytes()).digest()
        == sha256(source.read_bytes()).digest()
    )
    old, new = LearnedPolicy(source, OLD), LearnedPolicy(converted, NEW)
    with pytest.raises(ValueError, match="contract_mismatch"):
        LearnedPolicy(source, NEW)
    with ShowdownEnvironment(checkout) as env:
        env.reset(
            scenario("validation", 17513, version="showdown-learning-curriculum-v3")
        )
        players = {
            side: VisibleBaseline("max_power", seed=17) for side in ("self", "opponent")
        }
        for _ in range(20):
            views = {
                side: env.observation(side, include_history=True) for side in players
            }
            for view in views.values():
                np.testing.assert_array_equal(
                    old.encoder.encode(view), new.encoder.encode(view)
                )
                np.testing.assert_array_equal(
                    old.infer(view)["action_probabilities"],
                    new.infer(view)["action_probabilities"],
                )
            result = env.step(
                {side: actor.act(views[side]) for side, actor in players.items()},
                revision=views["self"]["revision"],
            )
            if result["terminated"] or result["truncated"]:
                break


def test_coordinator_coverage_is_never_policy_input():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("pinned engine required")
    encoder = make_encoder(NEW, "showdown-learned-observation-v3")
    env = ShowdownLearningEnv(checkout, encoder, curriculum_version=VERSION)
    try:
        features, info = env.reset(seed=41917)
        before = deepcopy(env.current)
        coverage = env.drain_coverage()
        assert (
            sum(coverage["self_brought_species"].values()) == 6
        )  # construction + explicit reset
        assert env.current == before and not env.drain_coverage()
        assert set(info) == {
            "schema_version",
            "episode_id",
            "revision",
            "request_state",
        }
        np.testing.assert_array_equal(features, encoder.encode(before))
        leaked = deepcopy(before)
        leaked["teams"] = {}
        with pytest.raises(ValueError, match="privileged_truth"):
            encoder.encode(leaked)
    finally:
        env.close()
