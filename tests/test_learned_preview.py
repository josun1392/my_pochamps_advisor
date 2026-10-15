"""Native ordered preview, information isolation, learning and persistence."""
from copy import deepcopy
from hashlib import sha256
import os
from pathlib import Path
import numpy as np
import pytest
import torch
import gymnasium as gym
from sb3_contrib import MaskablePPO
from advisor.learned_preview import ACTIONS, ACTION_VERSION, PreviewEncoder, public_preview, selection, DIMENSION, ROW, NUMERIC
from advisor.learned_preview_policy import PreviewPolicy, LearnedPreviewPolicy
from advisor.learned_preview_env import PreviewLearningEnv, execute_preview_battle
from advisor.learned_encoder import fingerprint
from advisor.showdown_environment import ShowdownEnvironment
from advisor.showdown_bridge import ShowdownBridgeError
from advisor.learned_baselines import VisibleBaseline
from scripts.verify_showdown_integration import fixture_scenarios
from scripts.train_showdown_preview import save_preview_checkpoint, optimizer_identity, tensor_identity

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_mc_domain_v1/catalog.json"


@pytest.fixture(scope="module")
def native():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("pinned external native checkout required")
    with ShowdownEnvironment(checkout, max_decisions=512) as env:
        yield env


def test_all_120_unique_ordered_actions_and_strict_validation():
    assert len(ACTIONS) == len(set(ACTIONS)) == 120
    assert ACTIONS[0] == (1, 2, 3) and ACTIONS[-1] == (6, 5, 4)
    assert {frozenset(p) for p in ACTIONS}.__len__() == 20
    for action in (-1, 120, True, 1.1, "123"):
        with pytest.raises(ValueError): selection(action)


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_native_all_120_slot_lead_reserve_and_unselected_enforcement(native, side):
    case = fixture_scenarios()[0]
    for action in range(120):
        case["preview"][side] = selection(action)
        native.reset(case)
        request = native.observation(side)["own_request"]["side"]["pokemon"]
        assert len(request) == 3
        slots = [int(row["ident"].split("slot-")[1]) + 1 for row in request]
        assert slots == selection(action)
        assert [row["active"] for row in request] == [True, False, False]
        assert all(row["details"].split(",")[0] == case["teams"][side][slot-1]["species"] for row, slot in zip(request, slots))
        assert native.observation(side)["action_mask"][3:6] == [0, 0, 0]


def test_preview_native_phase_no_execution_or_opposing_request(native):
    case = fixture_scenarios()[0]
    v = native.preview(case, "self")
    assert set(v) == {"schema_version", "side", "own_request", "events"}
    assert v["own_request"]["teamPreview"] and len(v["own_request"]["side"]["pokemon"]) == 6
    assert not any(x.startswith(("|switch|", "|turn|", "|move|")) for x in v["events"])
    assert native.resources["episodes"] <= 1  # inspection itself owns no episode
    invalid = deepcopy(case); invalid["teams"]["self"] = invalid["teams"]["self"][:3]
    with pytest.raises(ShowdownBridgeError): native.preview(invalid, "self")
    invalid = deepcopy(case); invalid["teams"]["self"][1] = deepcopy(invalid["teams"]["self"][0])
    with pytest.raises(ShowdownBridgeError): native.preview(invalid, "self")


def test_native_original_roster_slots_are_not_nickname_ordinals(native):
    case = deepcopy(fixture_scenarios()[0])
    case["slot_mapping"] = {"self": [9, 3, 20, 1, 5, 11]}
    view = public_preview(native.preview(case, "self"))
    assert [p["slot"] for p in view["own"]] == list(range(1, 7))
    case["preview"]["self"] = [6, 1, 4]
    native.reset(case)
    assert [p["ident"] for p in native.observation("self")["own_request"]["side"]["pokemon"]] == [
        "p1: slot-11", "p1: slot-9", "p1: slot-1"]


def test_missing_runtime_is_rejected_before_worker_spawn():
    from scripts.train_showdown_preview import validate
    with pytest.raises(ValueError, match="missing_preview_runtime_path_checkout"):
        validate({})


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_hidden_set_selection_and_rng_do_not_change_preview_features(native, side):
    case = deepcopy(fixture_scenarios()[0])
    for team in case["teams"].values():
        for p in team: p["gender"] = "N" if p["species"] == "Rotom-Wash" else "M"
    other = "opponent" if side == "self" else "self"
    before = public_preview(native.preview(case, side))
    altered = deepcopy(case)
    altered["preview"] = {"self": [6, 3, 5], "opponent": [4, 2, 1]}
    altered["seed"] = [611, 722, 833, 944]
    p = altered["teams"][other][1]
    p.update(moves=["Protect", "Earthquake"], item="Choice Scarf", ability="Sand Veil",
             evs={"hp": 32, "atk": 32, "spd": 2})
    after = public_preview(native.preview(altered, side))
    encoder = PreviewEncoder(CATALOG)
    assert before == after
    assert np.array_equal(encoder.encode(before), encoder.encode(after))
    for p in after["opponent"]:
        assert all(p[k] == {"knowledge": "unknown"} for k in ("item", "ability", "moves", "stats"))
    for key in ("scenario", "seed", "opponent_selected_three", "native_state"):
        bad = deepcopy(after); bad[key] = {}
        with pytest.raises(ValueError): encoder.encode(bad)
    bad = deepcopy(after); bad["opponent"][0]["ability"] = "Blaze"
    with pytest.raises(ValueError): encoder.encode(bad)
    raw = native.preview(case, side); raw["events"].append("|switch|p2a: slot-0|Scizor|100/100")
    with pytest.raises(ValueError): public_preview(raw)


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_illusion_last_brought_order_really_changes_native_appearance(native, side):
    from advisor.learned_full_domain import load_inventory
    case = deepcopy(fixture_scenarios()[0])
    case["teams"][side][0] = deepcopy(load_inventory()["species"]["zoroark"]["witness"])
    other = "opponent" if side == "self" else "self"
    appearances = []
    for ordered in ([1, 2, 3], [1, 3, 2]):
        case["preview"][side] = ordered
        native.reset(case)
        own = native.observation(side)
        assert own["own_request"]["side"]["pokemon"][0]["details"].startswith("Zoroark")
        role = "p1" if side == "self" else "p2"
        line = next(line for line in native.observation(other)["events"] if line.startswith(f"|switch|{role}a:"))
        appearances.append(line.split("|")[3].split(",")[0])
    assert appearances == ["Rotom-Wash", "Garchomp"]


class Spaces(gym.Env):
    def __init__(self):
        self.observation_space = gym.spaces.Box(-8, 8, (DIMENSION,), np.float32)
        self.action_space = gym.spaces.Discrete(120)


def test_exact_tokens_bit_safety_gradient_actor_critic_and_checkpoint(native, tmp_path):
    encoder = PreviewEncoder(CATALOG)
    public = public_preview(native.preview(fixture_scenarios()[0], "self"))
    assert encoder.categories.token("items", public["own"][0]["item"]) == 2
    assert encoder.categories.token("items", public["opponent"][0]["item"]) == 1
    x = encoder.encode(public)
    assert x.shape == (12 * ROW,)
    torch.set_num_threads(1)
    model = MaskablePPO(PreviewPolicy, Spaces(), seed=75011, device="cpu", gamma=1., gae_lambda=.95, n_steps=8, batch_size=8)
    reference = MaskablePPO(PreviewPolicy, Spaces(), seed=75011, device="cpu", gamma=1., gae_lambda=.95, n_steps=8, batch_size=8)
    assert tensor_identity(model.policy.state_dict()) == tensor_identity(reference.policy.state_dict())
    features = torch.tensor(x)[None]
    mask = np.ones((1, 120), bool); mask[:, 30:] = False
    distribution = model.policy.get_distribution(features, action_masks=mask)
    assert torch.all(distribution.distribution.probs[:, 30:] == 0)
    value = model.policy.predict_values(features)
    loss = -distribution.log_prob(torch.tensor([7])).mean() + value.square().mean()
    model.policy.optimizer.zero_grad(); loss.backward()
    for embedding in model.policy.mlp_extractor.embeddings.values():
        assert embedding.weight.grad is not None and torch.isfinite(embedding.weight.grad).all()
        assert embedding.weight.grad.abs().sum() > 0
    model.policy.optimizer.step()
    config = {"battle_model_sha256": "test-fixture-no-battle-loaded"}
    meta = save_preview_checkpoint(model, encoder, tmp_path / "preview", config)
    loaded = LearnedPreviewPolicy(tmp_path / "preview.zip", CATALOG, expected_sha256=meta["model_sha256"])
    assert optimizer_identity(loaded.model) == optimizer_identity(model)
    assert loaded.infer(public) == LearnedPreviewPolicy(tmp_path / "preview.zip", CATALOG).infer(public)
    assert torch.equal(model.policy.predict_values(features), loaded.model.policy.predict_values(features))
    from advisor.learned_policy import LearnedPolicy
    with pytest.raises(ValueError): LearnedPolicy(tmp_path / "preview.zip", CATALOG)
    bad = features.clone(); bad[0, NUMERIC] = .5
    with pytest.raises(ValueError, match="nonbinary"): model.policy.get_distribution(bad)
    with pytest.raises(ValueError): save_preview_checkpoint(model, encoder, tmp_path / "preview", config)


def test_native_timeout_has_no_false_terminal_learning_label():
    class Native:
        def reset(self, scenario): return {"terminated": False, "truncated": True}
    with pytest.raises(RuntimeError, match="no_terminal_learning_label"):
        execute_preview_battle(Native(), fixture_scenarios()[0], "self", 0, None, None)


def test_native_real_ppo_frozen_battle_weights_and_optimizer_resume(tmp_path):
    checkout, battle = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT"), os.environ.get("POKEADVICE_PREVIEW_BATTLE_MODEL")
    if not checkout or not battle: pytest.skip("external trusted final V4 model required")
    sha = sha256(Path(battle).read_bytes()).hexdigest()
    class Provider:
        def __call__(self, split, index): return deepcopy(fixture_scenarios()[0])
    env = PreviewLearningEnv(checkout, CATALOG, battle, sha, Provider(), opponents=("max_power",))
    try:
        torch.set_num_threads(1)
        model = MaskablePPO(PreviewPolicy, env, seed=75011, device="cpu", n_steps=8, batch_size=8, n_epochs=1, gamma=1., gae_lambda=.95)
        before = tensor_identity(model.policy.state_dict())
        frozen = tensor_identity(env.player.model.policy.state_dict())
        model.learn(8)
        assert model.num_timesteps == 8 and tensor_identity(model.policy.state_dict()) != before
        assert tensor_identity(env.player.model.policy.state_dict()) == frozen
        assert not any(p.requires_grad for p in env.player.model.policy.parameters())
        assert sha256(Path(battle).read_bytes()).hexdigest() == sha
        config = {"battle_model_sha256": sha}
        meta = save_preview_checkpoint(model, env.encoder, tmp_path / "native_preview", config)
        restored = LearnedPreviewPolicy(tmp_path / "native_preview.zip", CATALOG).model
        assert optimizer_identity(restored) == meta["optimizer"]
        restored.set_env(env); restored.learn(8, reset_num_timesteps=False)
        assert restored.num_timesteps == 16 and optimizer_identity(restored)["steps_min"] > meta["optimizer"]["steps_min"]
    finally:
        env.close()


def test_seat_and_cluster_evaluation_accounting():
    from scripts.evaluate_showdown_preview import summarize
    records = [{"policy": policy, "case": case, "seat": seat, "rival": rival,
        "outcome": "win" if policy == "trained" else "loss", "entropy": 1.,
        "preview_action": 0, "native_rejections": 0, "native_decisions": 1}
        for policy in ("random", "initial", "trained") for case in range(8)
        for seat in ("self", "opponent") for rival in ("tactical", "champions")]
    summary = summarize(records)
    assert summary["trained_minus_baseline"]["random"]["win_fraction_difference"] == 1
    assert summary["trained_minus_baseline"]["random"]["case_clusters"] == 8
    assert summary["policies"]["trained"]["outcomes"] == {"win": 32}
