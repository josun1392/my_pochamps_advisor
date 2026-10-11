"""Real native observations, trained artifact, masks, updates and replay continuity."""

from copy import deepcopy
import json
import os
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("sb3_contrib")
from advisor.learned_gym import ShowdownLearningEnv
from advisor.learned_policy import LearnedPolicy
from advisor.learned_scenarios import scenario, TRAIN, UNSEEN
from advisor.showdown_environment import ShowdownEnvironment
from advisor.showdown_worker import ShowdownWorker
from scripts.verify_showdown_integration import fixture_scenarios

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_initial_v1/catalog.json"
MODEL = ROOT / "models/showdown_initial_v1/model.zip"


@pytest.fixture(scope="module")
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker:
        yield worker


@pytest.fixture(scope="module")
def learned():
    return LearnedPolicy(MODEL, CATALOG)


def test_hidden_sets_rng_and_episode_identity_never_enter_features(worker, learned):
    with ShowdownEnvironment(worker=worker) as env:
        original = fixture_scenarios()[0]
        for team in original["teams"].values():
            for p in team:
                p["gender"] = "N" if p["species"] == "Rotom-Wash" else "M"
        env.reset(original)
        before = env.observation("self")
        changed = deepcopy(original)
        changed["teams"]["opponent"][0].update(
            item="Choice Scarf",
            moves=["U-turn", "Iron Head"],
            evs={"hp": 32, "atk": 32, "spd": 2},
        )
        env.reset(changed, seed=[901, 802, 703, 604])
        after = env.observation("self")
        assert before["episode_id"] != after["episode_id"]
        np.testing.assert_array_equal(
            learned.encoder.encode(before), learned.encoder.encode(after)
        )
        a, b = learned.infer(before), learned.infer(after)
        assert a["action_probabilities"] == b["action_probabilities"]
        assert a["discounted_return_estimate"] == b["discounted_return_estimate"]


@pytest.mark.parametrize(
    "key", ["seed", "checkpoint", "native_state", "teams", "queue", "scenario"]
)
def test_privileged_input_fails_closed(worker, learned, key):
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(scenario("test", 2))
        obs = env.observation("self")
        obs[key] = {}
        with pytest.raises(ValueError, match="privileged_truth"):
            learned.infer(obs)


@pytest.mark.parametrize("key", ["known_item", "current_ability", "condition"])
def test_unknown_is_different_from_confirmed_absence(worker, learned, key):
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(scenario("test", 3))
        obs = env.observation("self")
        side = obs["state"]["opponent_side"]
        row = side["pokemon"][side["active_identity"]]
        row[key] = {"knowledge": "unknown"}
        unknown = learned.encoder.encode(obs)
        row[key] = None
        absent = learned.encoder.encode(obs)
        assert not np.array_equal(unknown, absent)


@pytest.mark.parametrize("key", ["weather", "terrain"])
def test_unknown_field_preserved(worker, learned, key):
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(scenario("test", 4))
        obs = env.observation("self")
        obs["state"]["field"][key] = {"knowledge": "unknown"}
        a = learned.encoder.encode(obs)
        obs["state"]["field"][key] = None
        assert not np.array_equal(a, learned.encoder.encode(obs))


def test_checkpoint_and_forced_replacement_native_masks(worker, learned):
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(fixture_scenarios()[0])
        saved = env.save()
        obs = env.observation("self")
        a = learned.infer(obs)
        assert env.save() == saved
        with env.fork() as fork:
            b = learned.infer(fork.observation("self"))
            assert (
                a["action_probabilities"] == b["action_probabilities"]
                and a["discounted_return_estimate"] == b["discounted_return_estimate"]
            )
        env.step({"self": 6, "opponent": 6}, revision=0)
        waiting = learned.infer(env.observation("self"))
        assert (
            waiting["action_index"] == 26 and waiting["action_probabilities"][26] == 1
        )
        other = env.observation("opponent")
        proof = learned.infer(other)
        assert proof["action_index"] in (1, 2) and proof["native_choice"].startswith(
            "switch "
        )
        assert all(
            p == 0
            for p, m in zip(proof["action_probabilities"], other["action_mask"])
            if not m
        )


def test_manifest_rejected_before_pickle_loading(tmp_path, monkeypatch, learned):
    model = tmp_path / "invalid.zip"
    model.write_bytes(MODEL.read_bytes())
    manifest = deepcopy(learned.metadata)
    manifest["model_sha256"] = "0" * 64
    model.with_suffix(".json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(
        "advisor.learned_policy.MaskablePPO.load",
        lambda *a, **k: pytest.fail("loaded incompatible artifact"),
    )
    with pytest.raises(ValueError, match="manifest"):
        LearnedPolicy(model, CATALOG)


def test_model_terminal_and_illegal_action_refusal(worker, learned):
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(scenario("test", 5))
        obs = env.observation("self")
        obs["action_mask"] = [0] * 35
        with pytest.raises(ValueError, match="no_native_policy_action"):
            learned.infer(obs)


def test_expected_model_identity_checked_before_pickle(monkeypatch):
    monkeypatch.setattr(
        "advisor.learned_policy.MaskablePPO.load",
        lambda *a, **k: pytest.fail("unexpected model loaded"),
    )
    with pytest.raises(ValueError, match="unexpected_learned_model_version"):
        LearnedPolicy(MODEL, CATALOG, expected_model_id="0" * 64)


@pytest.mark.parametrize("split", ["train", "validation", "test", "unseen"])
def test_curriculum_native_legality_and_observation_space(worker, learned, split):
    assert not {p[0] for p in TRAIN} & {p[0] for p in UNSEEN}
    with ShowdownEnvironment(worker=worker) as env:
        for index in range(6):
            env.reset(scenario(split, index))
            obs = env.observation("self")
            assert learned.encoder.encode(obs).shape == (787,)
            assert learned.infer(obs)["action_index"] in np.flatnonzero(
                obs["action_mask"]
            )


def test_gym_reset_truncation_mask_and_sparse_reward(learned):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned engine required")
    with ShowdownLearningEnv(checkout, learned.encoder, max_decisions=1) as env:
        obs, _ = env.reset(seed=71, options={"opponent": "max_power"})
        assert env.observation_space.contains(obs)
        first = obs.copy()
        action = int(np.flatnonzero(env.action_masks())[0])
        obs, reward, ended, truncated, info = env.step(action)
        assert truncated and not ended and reward == 0
        assert set(info["native_outcome"]) == {
            "revision",
            "decisions",
            "terminated",
            "truncated",
            "winner",
            "action_rejected",
            "rewards",
        }
        obs, _ = env.reset(seed=71, options={"opponent": "max_power"})
        np.testing.assert_array_equal(first, obs)
        for invalid in (-1, 35, 1.5):
            with pytest.raises(ValueError, match="masked_learning_action"):
                env.step(invalid)


def test_real_optimizer_updates_save_reload(tmp_path):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned engine required")
    from scripts.train_showdown_policy import train

    report = train(checkout, CATALOG, tmp_path / "trained", steps=256, envs=1, seed=3)
    assert report["steps_this_run"] == 256 and report["optimizer_steps_this_run"] > 0
    assert report["parameter_l1_change"] > 0 and report["reload_inference_equal"]
    assert report["completed_episodes"] > 0 and report["truncated"] == 0
    LearnedPolicy(tmp_path / "trained.zip", CATALOG)
    repeat = train(checkout, CATALOG, tmp_path / "repeat", steps=256, envs=1, seed=3)
    import torch

    a, b = (
        LearnedPolicy(tmp_path / "trained.zip", CATALOG),
        LearnedPolicy(tmp_path / "repeat.zip", CATALOG),
    )
    assert report["completed_episodes"] == repeat["completed_episodes"]
    assert all(
        torch.equal(p, q)
        for p, q in zip(a.model.policy.parameters(), b.model.policy.parameters())
    )


def test_gym_native_pivot_keeps_queued_choice_and_switch_mask(learned, monkeypatch):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned engine required")
    case = fixture_scenarios()[1]
    case["teams"]["self"][0] = {
        **deepcopy(case["teams"]["opponent"][0]),
        "moves": ["U-turn", "Protect"],
        "nature": "Jolly",
        "evs": {"atk": 32, "spe": 32, "hp": 2},
    }
    case["teams"]["opponent"][0]["evs"] = {"atk": 32, "hp": 32, "spd": 2}
    monkeypatch.setattr("advisor.learned_gym.scenario", lambda *_: deepcopy(case))
    monkeypatch.setattr(
        "advisor.learned_baselines.VisibleBaseline.act",
        lambda self, o: 7
        if o["action_mask"][7]
        else int(np.flatnonzero(o["action_mask"])[0]),
    )
    with ShowdownLearningEnv(checkout, learned.encoder) as env:
        _, reward, ended, truncated, _ = env.step(6)
        assert not ended and not truncated and reward == 0
        assert env.current["request_state"] == "switch" and not env.action_masks()[26]
        assert env.native.save()["native_state"]["queue"]
        assert any(env.action_masks()[:6]) and not any(env.action_masks()[6:])
        assert learned.act(env.current) in np.flatnonzero(env.action_masks())


def test_native_public_mega_form_updates_types(worker, learned):
    selected = None
    for index in range(100):
        case = scenario("train", index)
        if case["teams"]["self"][case["preview"]["self"][0] - 1]["item"].endswith(
            "ite X"
        ):
            selected = case
            break
    assert selected
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(selected)
        obs = env.observation("self")
        action = next(i for i in range(10, 14) if obs["action_mask"][i])
        other = env.observation("opponent")
        rival = int(np.flatnonzero(other["action_mask"])[0])
        env.step({"self": action, "opponent": rival}, revision=0)
        own = env.observation("self")["state"]["self_side"]
        assert "Mega-X" in own["pokemon"][own["active_identity"]]["details"]
        public = env.observation("opponent")["state"]["opponent_side"]
        assert "Mega-X" in public["pokemon"][public["active_identity"]]["details"]


def test_missing_private_item_is_unknown_not_known_absence(worker):
    from advisor.showdown_observation import project_policy_observation

    with ShowdownEnvironment(worker=worker) as env:
        env.reset(scenario("train", 1))
        obs = env.observation("self", include_history=True)
        native = {
            k: v
            for k, v in obs.items()
            if k not in {"state", "interpretation", "public_history"}
        }
        pokemon = native["own_request"]["side"]["pokemon"][1]
        for key in ("item", "ability", "baseAbility"):
            pokemon.pop(key, None)
        value = project_policy_observation(native, obs["public_history"])
        row = next(
            r
            for key, r in value["state"]["self_side"]["pokemon"].items()
            if key.split(": ", 1)[1] == pokemon["ident"].split(": ", 1)[1]
        )
        assert row["known_item"] == row["current_ability"] == {"knowledge": "unknown"}
        pokemon["item"] = ""
        value = project_policy_observation(native, obs["public_history"])
        row = next(
            r
            for key, r in value["state"]["self_side"]["pokemon"].items()
            if key.split(": ", 1)[1] == pokemon["ident"].split(": ", 1)[1]
        )
        assert row["known_item"] is None
