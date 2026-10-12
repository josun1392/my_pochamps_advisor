"""Public action representation, trusted checkpoints and bounded trainer contracts."""

from copy import deepcopy
import json
import os
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
pytest.importorskip("sb3_contrib")
from sb3_contrib import MaskablePPO
from advisor.learned_action_encoder import (
    ActionObservationEncoder,
    CONTEXT,
    ACTION,
    VERSION,
)
from advisor.learned_action_policy import ActionConditionedPolicy
from advisor.learned_gym import ShowdownLearningEnv
from advisor.learned_policy import LearnedPolicy
from advisor.learned_scenarios import scenario
from advisor.showdown_environment import ShowdownEnvironment
from scripts.train_showdown_autonomous import (
    validate_config,
    save_checkpoint,
    optimizer_steps,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_initial_v1/catalog.json"


@pytest.fixture(scope="module")
def checkout():
    value = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not value:
        pytest.skip("external pinned native engine required")
    return value


@pytest.fixture(scope="module")
def view(checkout):
    with ShowdownEnvironment(checkout) as env:
        env.reset(
            scenario("validation", 7131, version="showdown-learning-curriculum-v2")
        )
        yield env.observation("self", include_history=True)


def test_hash_namespaced_curriculum_preserves_old_contract():
    # The old additive schedule really collided; never reinterpret those old seeds.
    assert scenario("train", 100000)["teams"] == scenario("validation", 0)["teams"]
    v2 = "showdown-learning-curriculum-v2"
    assert scenario("train", 100000, version=v2) != scenario(
        "validation", 0, version=v2
    )
    assert scenario("train", 100000, version=v2) == scenario(
        "train", 100000, version=v2
    )
    with pytest.raises(ValueError):
        scenario("train", 0, version="future")


def test_historical_opponent_binding_survives_best_model_change_and_resume():
    from scripts.train_showdown_autonomous import freeze_historical_reference

    state = {"best": "original.zip"}
    assert (
        freeze_historical_reference(
            state, 0, "previous.zip", resumed=False, required=True
        )
        == "original.zip"
    )
    state["best"] = "new-self-best.zip"
    assert (
        freeze_historical_reference(
            state, 0, "previous.zip", resumed=True, required=True
        )
        == "original.zip"
    )
    assert (
        freeze_historical_reference(
            state, 1, "previous.zip", resumed=False, required=True
        )
        == "new-self-best.zip"
    )
    with pytest.raises(ValueError, match="missing_frozen_opponent"):
        freeze_historical_reference(
            {"best": "unknown-history.zip"},
            0,
            "previous.zip",
            resumed=True,
            required=True,
        )


def test_explicit_historical_opponent_keeps_seed_experiments_independent():
    from scripts.train_showdown_autonomous import freeze_historical_reference

    state = {"best": "prior-seed-best.zip"}
    assert (
        freeze_historical_reference(
            state,
            0,
            "fallback.zip",
            resumed=False,
            required=True,
            fixed_path="frozen-reference.zip",
        )
        == "frozen-reference.zip"
    )
    state["best"] = "new-league-best.zip"
    assert (
        freeze_historical_reference(
            state,
            0,
            "fallback.zip",
            resumed=True,
            required=True,
            fixed_path="frozen-reference.zip",
        )
        == "frozen-reference.zip"
    )
    assert (
        freeze_historical_reference(
            state,
            1,
            "fallback.zip",
            resumed=False,
            required=True,
            fixed_path="frozen-reference.zip",
        )
        == "frozen-reference.zip"
    )


def test_action_features_public_history_masks_and_unknown(view):
    encoder = ActionObservationEncoder(CATALOG)
    original = deepcopy(view)
    x = encoder.encode(view)
    assert x.shape == (5221,) and np.isfinite(x).all()
    assert view == original
    missing_history = deepcopy(view)
    missing_history.pop("public_history")
    with pytest.raises(ValueError, match="public_history_required"):
        encoder.encode(missing_history)
    for key in ("seed", "native_state", "teams", "queue", "checkpoint"):
        bad = deepcopy(view)
        bad[key] = {}
        with pytest.raises(ValueError, match="privileged"):
            encoder.encode(bad)
    changed = deepcopy(view)
    changed.update(episode_id="other", revision=999)
    np.testing.assert_array_equal(x, encoder.encode(changed))
    side = changed["state"]["opponent_side"]
    row = side["pokemon"][side["active_identity"]]
    row["known_item"] = None
    assert not np.array_equal(x, encoder.encode(changed))


def test_unrevealed_opponent_set_and_future_seed_never_change_action_features(checkout):
    from scripts.verify_showdown_integration import fixture_scenarios

    encoder = ActionObservationEncoder(CATALOG)
    case = fixture_scenarios()[0]
    for team in case["teams"].values():
        for pokemon in team:
            pokemon["gender"] = "N" if pokemon["species"] == "Rotom-Wash" else "M"
    changed = deepcopy(case)
    changed["teams"]["opponent"][0].update(
        item="Choice Scarf",
        moves=["U-turn", "Iron Head"],
        evs={"hp": 32, "atk": 32, "spd": 2},
    )
    with ShowdownEnvironment(checkout) as env:
        env.reset(case)
        before = encoder.encode(env.observation("self", include_history=True))
        env.reset(changed, seed=[901, 802, 703, 604])
        after = encoder.encode(env.observation("self", include_history=True))
        np.testing.assert_array_equal(before, after)


def test_move_and_bench_permutations_preserve_context_and_action_scores(view):
    torch.set_num_threads(1)
    encoder = ActionObservationEncoder(CATALOG)
    x = encoder.encode(view)
    changed = deepcopy(view)
    changed["own_request"]["active"][0]["moves"][0:2] = reversed(
        changed["own_request"]["active"][0]["moves"][0:2]
    )
    roster = changed["own_request"]["side"]["pokemon"]
    roster[1], roster[2] = roster[2], roster[1]
    pairs = [(1, 2), (6, 7), (10, 11), (27, 28), (31, 32)]
    for a, b in pairs:
        changed["action_mask"][a], changed["action_mask"][b] = (
            changed["action_mask"][b],
            changed["action_mask"][a],
        )
    y = encoder.encode(changed)
    np.testing.assert_allclose(x[:CONTEXT], y[:CONTEXT], rtol=0, atol=1e-7)
    xr, yr = x[CONTEXT:].reshape(35, ACTION), y[CONTEXT:].reshape(35, ACTION)
    order = list(range(35))
    for a, b in pairs:
        order[a], order[b] = order[b], order[a]
    np.testing.assert_allclose(xr[order], yr, rtol=0, atol=1e-7)
    network = __import__(
        "advisor.learned_action_policy", fromlist=["ActionExtractor"]
    ).ActionExtractor()
    with torch.no_grad():
        first = network.forward_actor(torch.tensor(x)[None])[0]
        second = network.forward_actor(torch.tensor(y)[None])[0]
        torch.testing.assert_close(first[order], second)
        torch.testing.assert_close(
            network.forward_critic(torch.tensor(x)[None]),
            network.forward_critic(torch.tensor(y)[None]),
        )


def test_actual_learning_optimizer_reload_and_continuation(tmp_path, checkout):
    torch.set_num_threads(1)
    encoder = ActionObservationEncoder(CATALOG)
    with ShowdownLearningEnv(
        checkout, encoder, curriculum_version="showdown-learning-curriculum-v2"
    ) as env:
        model = MaskablePPO(
            ActionConditionedPolicy,
            env,
            n_steps=128,
            batch_size=128,
            n_epochs=2,
            seed=23,
            device="cpu",
        )
        before = torch.cat(
            [p.detach().flatten() for p in model.policy.parameters()]
        ).clone()
        model.learn(256)
        assert optimizer_steps(model) > 0
        assert (
            torch.cat([p.detach().flatten() for p in model.policy.parameters()])
            - before
        ).abs().sum() > 0
        path = save_checkpoint(model, encoder, tmp_path / "one", {"test": True})
        restored = LearnedPolicy(path, CATALOG)
        assert (
            restored.encoder.version == VERSION and restored.model.num_timesteps == 256
        )
        assert restored.act(env.current) == int(
            model.predict(
                encoder.encode(env.current),
                action_masks=env.action_masks(),
                deterministic=True,
            )[0]
        )
        assert optimizer_steps(restored.model) == optimizer_steps(model)
        restored.model.set_env(env)
        restored.model.learn(128, reset_num_timesteps=False)
        assert restored.model.num_timesteps == 384 and optimizer_steps(
            restored.model
        ) > optimizer_steps(model)


def test_v2_existing_strategy_ui_truth_and_ranking_are_unchanged(tmp_path, checkout):
    from tests.test_showdown_strategy_evaluation import configuration
    from tests.test_showdown_shadow_ui import run
    from advisor.showdown_worker import ShowdownWorker
    from llm.advisor_learned_strategy import valid_learned_evidence
    from ui.strategy_explanation_presentation import (
        present_strategy_explanation,
        render_strategy_explanation,
    )

    encoder = ActionObservationEncoder(CATALOG)
    with ShowdownLearningEnv(
        checkout, encoder, curriculum_version="showdown-learning-curriculum-v2"
    ) as env:
        model = MaskablePPO(
            ActionConditionedPolicy,
            env,
            n_steps=128,
            batch_size=128,
            seed=23,
            device="cpu",
        )
        path = save_checkpoint(model, encoder, tmp_path / "v2-ui", {})
    manifest = json.loads(Path(path).with_suffix(".json").read_text())
    snapshot, builder, context = configuration(horizon=1)
    context["learned_policy"] = {
        "schema_version": "showdown-learned-config-v1",
        "enabled": True,
        "model_path": path,
        "catalog_path": str(CATALOG),
        "expected_model_id": manifest["model_sha256"],
    }
    original = deepcopy((snapshot, context))
    with ShowdownWorker(checkout) as bridge:
        baseline = run(snapshot, builder)
        result = run(
            snapshot, builder, showdown_context=context, showdown_bridge=bridge
        )
    assert original == (snapshot, context)
    assert baseline["exact_outcome_ledgers"] == result["exact_outcome_ledgers"]
    assert (
        baseline["explanation"]["preferred_frontier"]
        == result["explanation"]["preferred_frontier"]
    )
    evidence = result["explanation"]["sampled_simulation"]
    for row in evidence["scenarios"]:
        assert row["learned_policy"]["status"] == "evaluated"
        assert valid_learned_evidence(row["learned_policy"], evidence, row)
        assert row["learned_policy"]["inference"]["encoder_version"] == VERSION
    text = render_strategy_explanation(
        presentation=present_strategy_explanation(explanation=result["explanation"])
    )
    assert "승률 아님" in text and "기본 추천에 미적용" in text


def test_independent_teacher_rate_updates_then_restores_ppo_rate(checkout):
    from stable_baselines3.common.vec_env import DummyVecEnv
    from types import SimpleNamespace
    from scripts.train_showdown_autonomous import warmstart

    encoder = ActionObservationEncoder(CATALOG)
    env = ShowdownLearningEnv(
        checkout, encoder, curriculum_version="showdown-learning-curriculum-v2"
    )
    vector = DummyVecEnv([lambda: env])
    try:
        model = MaskablePPO(
            ActionConditionedPolicy,
            vector,
            n_steps=128,
            batch_size=128,
            learning_rate=5e-5,
            seed=31,
            device="cpu",
        )
        report = warmstart(
            model,
            vector,
            encoder,
            128,
            2,
            31,
            SimpleNamespace(stopping=lambda: False),
            learning_rate=3e-4,
        )
        assert report["optimizer_updates"] == 2 and report["parameter_l1_change"] > 0
        assert (
            report["learning_rate"] == 3e-4
            and 0 <= report["teacher_demonstration_action_accuracy"] <= 1
        )
        assert all(group["lr"] == 5e-5 for group in model.policy.optimizer.param_groups)
    finally:
        vector.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_runtime_seconds", 0),
        ("envs", 16),
        ("memory_mib", 99999),
        ("cpu_percent", 100),
    ],
)
def test_trainer_rejects_unbounded_configuration(field, value):
    config = {
        "schema_version": "showdown-autonomous-training-v1",
        "max_runtime_seconds": 60,
        "envs": 1,
        "checkpoint_steps": 256,
        "experiments": [{"seed": 11, "steps": 512}],
    }
    validate_config(config)
    config[field] = value
    with pytest.raises(ValueError):
        validate_config(config)


@pytest.mark.skipif(os.name != "nt", reason="hard job limits require Windows")
def test_standalone_lifecycle_and_new_budget_from_optimizer_checkpoint(
    tmp_path, checkout
):
    import subprocess
    import sys
    from advisor.learning_resources import process_alive

    script = ROOT / "scripts/train_showdown_autonomous.py"
    config = {
        "schema_version": "showdown-autonomous-training-v1",
        "checkout": checkout,
        "catalog": str(CATALOG),
        "max_runtime_seconds": 60,
        "envs": 1,
        "checkpoint_steps": 256,
        "validation_cases": 1,
        "plateau_patience": 4,
        "experiments": [{"seed": 11, "steps": 512}],
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    output = tmp_path / "run"
    command = [
        sys.executable,
        str(script),
        "--config",
        str(config_file),
        "--output",
        str(output),
    ]
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=90, cwd=ROOT
    )
    assert result.returncode == 0, result.stderr
    state = json.loads((output / "state.json").read_text())
    assert state["status"] == "complete" and state["transitions"] == 512
    assert (
        state["trained_rollout_transitions"] == 512 and state["completed_battles"] > 0
    )
    control = json.loads((output / "control.json").read_text())
    assert sum(state["episode_outcomes"].values()) == state["completed_battles"]
    assert state["episode_count_scope"] == "ended_including_time_limit_truncations"
    assert not process_alive(control["pid"]) and not (output / "run.lock").exists()
    checkpoint = state["evaluations"][-1]["checkpoint"]
    saved = LearnedPolicy(checkpoint, CATALOG)
    updates = optimizer_steps(saved.model)
    result = subprocess.run(
        command + ["--resume"], capture_output=True, text=True, timeout=90, cwd=ROOT
    )
    assert result.returncode == 0, result.stderr
    assert json.loads((output / "state.json").read_text())["transitions"] == 512
    config["experiments"][0].update(steps=256, initial_model=checkpoint, seed=29)
    config_file = tmp_path / "continuation.json"
    config_file.write_text(json.dumps(config))
    second = tmp_path / "continued"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--config",
            str(config_file),
            "--output",
            str(second),
        ],
        capture_output=True,
        text=True,
        timeout=90,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    state = json.loads((second / "state.json").read_text())
    resumed = LearnedPolicy(state["evaluations"][-1]["checkpoint"], CATALOG)
    assert state["transitions"] == 256 and resumed.model.num_timesteps == 768
    assert resumed.model.seed == 29
    assert optimizer_steps(resumed.model) > updates
