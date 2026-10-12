"""Native prefixes, new teacher compatibility and policy-visible diagnostics."""

import json
import os
from copy import deepcopy
from pathlib import Path
import pytest
from poke_env.battle import Move
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_scenarios import scenario
from advisor.learned_tactical_curriculum import reset_learning_episode, VERSION, MOTIFS
from advisor.learned_tactical_diagnostics import TacticalDiagnostics, action_class
from advisor.learned_action_encoder import make_encoder
from advisor.showdown_environment import ShowdownEnvironment

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_initial_v1/catalog.json"


@pytest.fixture(scope="module")
def checkout():
    path = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not path:
        pytest.skip("external pinned engine required")
    return path


def test_upstream_target_enum_is_not_legacy_string():
    m = Move("swordsdance", gen=9)
    assert m.target != "self" and m.target.name.lower() == "self"


def test_v4_disjoint_namespaces_preserve_earlier_contracts():
    assert scenario("train", 17000, version=VERSION) != scenario(
        "validation", 17000, version=VERSION
    )
    assert scenario("validation", 17000, version=VERSION) == scenario(
        "validation", 17000, version=VERSION
    )
    assert "learning_start" not in scenario("unseen", 17000, version=VERSION)
    assert "learning_start" not in scenario(
        "train", 17000, version="showdown-learning-curriculum-v3"
    )


def test_native_prefixes_legality_reproducibility_and_isolation(checkout):
    encoder = make_encoder(CATALOG, "showdown-learned-observation-v3")
    motifs = set()
    with ShowdownEnvironment(checkout) as env:
        for index in range(17000, 17144):
            c = scenario("validation", index, version=VERSION)
            original = deepcopy(c)
            info = reset_learning_episode(env, c)
            assert c == original
            motifs.add(info["motif"])
            view = env.observation("self", include_history=True)
            assert any(view["action_mask"])
            assert not {"learning_start", "motif", "teams", "prefix", "seed"} & set(
                view
            )
            assert encoder.encode(view).shape == (7411,)
            old = deepcopy(view)
            teacher = VisibleBaseline("tactical_heuristic")
            a = teacher.act(view)
            assert view["action_mask"][a]
            assert TacticalDiagnostics().describe(view, a)["selected"] == action_class(
                view, a
            )
            assert view == old
            if index < 17024:
                reset_learning_episode(env, c)
                again = env.observation("self", include_history=True)
                assert view["public_history"] == again["public_history"]
        assert motifs == {"broad", *(m[0] for m in MOTIFS)}


def test_new_setup_teacher_and_old_baseline_remain_distinct(checkout):
    c = scenario("validation", 17004, version=VERSION)  # Clefable vs Garchomp.
    with ShowdownEnvironment(checkout) as env:
        reset_learning_episode(env, c)
        view = env.observation("self", include_history=True)
        old = VisibleBaseline("heuristic").act(view)
        new = VisibleBaseline("tactical_heuristic").act(view)
        assert action_class(view, new) == "setup"
        assert action_class(view, old) != "setup"


def test_tactical_start_complete_native_battles(checkout):
    with ShowdownEnvironment(checkout) as env:
        for i in range(17000, 17024, 2):
            reset_learning_episode(env, scenario("validation", i, version=VERSION))
            players = {
                s: VisibleBaseline("tactical_heuristic", i)
                for s in ("self", "opponent")
            }
            for _ in range(256):
                views = {s: env.observation(s, include_history=True) for s in players}
                r = env.step(
                    {s: p.act(views[s]) for s, p in players.items()},
                    revision=views["self"]["revision"],
                )
                if r["terminated"] or r["truncated"]:
                    break
            assert r["terminated"] and not r["truncated"]


def test_trainer_accepts_versioned_tactical_curriculum():
    from scripts.train_showdown_autonomous import validate_config

    c = (
        json.loads((ROOT / "config/training_action_v2_example.json").read_text())
        if (ROOT / "config/training_action_v2_example.json").exists()
        else {
            "schema_version": "showdown-autonomous-training-v1",
            "max_runtime_seconds": 60,
            "envs": 1,
            "checkpoint_steps": 128,
            "experiments": [{"seed": 401, "steps": 128}],
        }
    )
    c["curriculum_version"] = VERSION
    c["experiments"][0]["teacher"] = "tactical_heuristic"
    c["experiments"][0]["opponents"] = ["tactical_heuristic"]
    assert validate_config(c) == c


def test_native_branch_restarts_have_reproducible_terminal_results(checkout):
    from scripts.evaluate_showdown_tactical_branches import evaluate_branches

    a = evaluate_branches(checkout, offset=18000, cycles=1)
    b = evaluate_branches(checkout, offset=18000, cycles=1)
    assert a == b
    assert all(not r["truncated"] for r in a["records"])
    assert {r["first_class"] for r in a["records"]} >= {
        "attack",
        "switch",
        "setup",
        "recovery",
    }


def test_native_teacher_updates_and_class_accounting(checkout):
    import numpy as np
    import torch
    from types import SimpleNamespace
    from stable_baselines3.common.vec_env import DummyVecEnv
    from advisor.learned_gym import ShowdownLearningEnv
    from advisor.learned_policy import LearnedPolicy
    from scripts.train_showdown_autonomous import warmstart

    torch.set_num_threads(1)
    policy = LearnedPolicy(
        ROOT / "models/showdown_generalization_v3/model.zip", CATALOG
    )
    env = ShowdownLearningEnv(
        checkout,
        policy.encoder,
        curriculum_version=VERSION,
        opponents=["tactical_heuristic"],
    )
    vector = DummyVecEnv([lambda: env])
    try:
        proof = warmstart(
            policy.model,
            vector,
            policy.encoder,
            128,
            1,
            501,
            SimpleNamespace(stopping=lambda: False),
            teacher_kind="tactical_heuristic",
        )
        assert (
            proof["decisions"]
            == sum(proof["retained_teacher_action_classes"].values())
            == 128
        )
        assert proof["parameter_l1_change"] > 0 and proof["optimizer_updates"] > 0
        assert np.isfinite(proof["last_loss"])
        correct = sum(
            proof["retained_teacher_action_classes"][k] * v
            for k, v in proof["teacher_action_accuracy_by_class"].items()
        )
        assert correct / 128 == pytest.approx(
            proof["teacher_demonstration_action_accuracy"]
        )
    finally:
        vector.close()


def test_published_tactical_artifacts_reload_with_masks_and_identity(checkout):
    import hashlib
    import numpy as np
    from advisor.learned_policy import LearnedPolicy
    from scripts.train_showdown_autonomous import optimizer_steps

    with ShowdownEnvironment(checkout) as env:
        reset_learning_episode(env, scenario("validation", 19100, version=VERSION))
        view = env.observation("self", include_history=True)
        before = env.save()
        for name in (
            "showdown_tactical_v4",
            "showdown_tactical_seed_811",
            "showdown_tactical_seed_919",
            "showdown_tactical_seed_1021",
        ):
            path = ROOT / "models" / name / "model.zip"
            m = json.loads(path.with_suffix(".json").read_text())
            assert hashlib.sha256(path.read_bytes()).hexdigest() == m["model_sha256"]
            p = LearnedPolicy(path, CATALOG, expected_model_id=m["model_sha256"])
            proof = p.infer(view)
            mask = np.asarray(view["action_mask"], dtype=bool)
            probabilities = np.asarray(proof["action_probabilities"])
            assert probabilities.sum() == pytest.approx(1)
            assert not probabilities[~mask].any()
            assert (
                proof["episode_id"] == view["episode_id"]
                and proof["revision"] == view["revision"]
            )
            assert (
                proof["evidence_class"] == "learned_policy_value"
                and mask[proof["action_index"]]
            )
            assert optimizer_steps(p.model) == m["optimizer_steps"] > 0
        assert env.save() == before
