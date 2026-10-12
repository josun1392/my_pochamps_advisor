"""Native diversity, public-only data, masked return weighting and recovery."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
pytest.importorskip("sb3_contrib")
pytest.importorskip("poke_env")
from advisor.learned_action_encoder import make_encoder
from advisor.learned_native_curriculum import load_bank, native_case
from advisor.learned_champions_metadata import make_champions_battle
from advisor.learned_gym import ShowdownLearningEnv
from advisor.learned_offline import (
    TrajectoryWriter,
    load_dataset,
    advantage_weights,
    fit_offline,
    file_hash,
)
from advisor.learned_policy import LearnedPolicy
from advisor.learned_scenarios import scenario
from advisor.learning_resources import atomic_json
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
from scripts.train_showdown_autonomous import save_checkpoint, validate_config

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_initial_v1/catalog.json"


@pytest.fixture(scope="module")
def checkout():
    value = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not value:
        pytest.skip("pinned external native checkout required")
    return value


def test_native_bank_diversity_and_old_unseen_reservations():
    from advisor.learned_coherent_curriculum import EXTRA_UNSEEN
    from advisor.learned_roster import BROAD_UNSEEN

    bank = load_bank()
    train, unseen = set(bank["train_base_species"]), set(bank["unseen_base_species"])
    assert len(train) >= 180 and len(unseen) >= 35 and not train & unseen
    assert {p[0].split("-")[0] for p in BROAD_UNSEEN + EXTRA_UNSEEN} <= {
        p.split("-")[0] for p in unseen
    }
    for split in ("train", "validation", "test", "unseen"):
        assert len(bank["coverage"][split]) >= 35
        seen = set()
        for team in bank["teams"][split]:
            items = [p["item"] for p in team if p["item"]]
            assert len(team) == 6 and len(items) == len(set(items))
            seen.add(sha256(json.dumps(team, sort_keys=True).encode()).hexdigest())
        assert len(seen) == bank["counts"][split]
    training = {json.dumps(t, sort_keys=True) for t in bank["teams"]["train"]}
    for split in ("validation", "test", "unseen"):
        assert not training & {
            json.dumps(t, sort_keys=True) for t in bank["teams"][split]
        }
    old = scenario("train", 913, version="showdown-learning-curriculum-v5")
    assert old == scenario("train", 913, version="showdown-learning-curriculum-v5")
    original = native_case("train", 901)
    changed = deepcopy(original)
    changed["teams"]["self"][0]["moves"].clear()
    assert native_case("train", 901) == original
    assert native_case("train", 0) != native_case("validation", 0)


def test_new_mega_public_metadata_does_not_mutate_upstream_gen9():
    from poke_env.data import GenData
    import logging

    original = GenData.from_gen(9).pokedex
    snapshot = deepcopy(original)
    battle = make_champions_battle("test-public", "self", logging.getLogger("test"), 9)
    mon = battle.get_pokemon("p1: Malamar", details="Malamar, L50")
    mon.forme_change("Malamar-Mega")
    assert mon.base_stats == battle._data.pokedex["malamarmega"]["baseStats"]
    assert battle._data.pokedex is not original and original == snapshot


def test_fresh_species_bank_rejects_training_and_pretraining_overlap():
    from advisor.learned_native_curriculum import FRESH_VERSION, FRESH_BANK, _load_bank
    from advisor.learned_scenarios import TRAIN
    from advisor.learned_roster import BROAD_TRAIN
    from advisor.learned_coherent_curriculum import EXTRA_TRAIN

    bank = _load_bank(FRESH_BANK, FRESH_VERSION)
    prior = {p[0].split("-")[0] for p in TRAIN + BROAD_TRAIN + EXTRA_TRAIN}
    assert len(bank["unseen_base_species"]) == 17 and not prior & set(
        bank["unseen_base_species"]
    )
    for split in ("train", "validation", "test"):
        with pytest.raises(
            ValueError, match="cannot_be_used_for_training_or_selection"
        ):
            scenario(split, 880000, version=FRESH_VERSION)


def test_native_bank_episodes_and_behavior_receive_only_own_partial_views(checkout):
    encoder = make_encoder(CATALOG, "showdown-learned-observation-v3")
    seen = []

    class Actor:
        def act(self, view):
            assert view["side"] in {"self", "opponent"}
            assert not set(view) & {
                "seed",
                "teams",
                "native_state",
                "queue",
                "checkpoint",
            }
            encoder.encode(view)
            seen.append(view["side"])
            allowed = np.flatnonzero(view["action_mask"])
            return int(
                next((i for i in allowed if 10 <= i <= 13 or i >= 27), allowed[-1])
            )

    env = ShowdownLearningEnv(
        checkout,
        encoder,
        curriculum_version="showdown-learning-curriculum-v6",
        opponents=["actor"],
        opponent_factory=lambda kind, seed: Actor(),
    )
    try:
        ended = 0
        for _ in range(600):
            decision = env.behavior_decision("actor")
            assert set(decision) == {"action", "category"}
            _, reward, terminal, truncated, info = env.step(decision["action"])
            if terminal or truncated:
                assert reward in {-1, 0, 1}
                ended += 1
                if ended == 20:
                    break
                env.reset()
        assert ended == 20 and set(seen) == {"self", "opponent"}
        assert all(not row["truncated"] for row in env.drain_completed())
    finally:
        env.close()


def make_data(path, view, encoder):
    x = encoder.encode(view)
    mask = np.asarray(view["action_mask"], dtype=bool)
    actions = np.flatnonzero(mask)
    writer = TrajectoryWriter(
        path,
        16,
        encoder.dimension,
        {
            "engine_commit": SHOWDOWN_COMMIT,
            "format_id": FORMAT_ID,
            "encoder_version": encoder.version,
            "catalog_fingerprint": encoder.catalog_fingerprint,
            "observation_dimension": encoder.dimension,
            "gamma": 0.99,
            "split": "train",
        },
    )
    for action, reward in zip(actions[:2], (1.0, -1.0)):
        writer.add_episode(
            [(x, mask, int(action), "attack")] * 4, reward, "public-test"
        )
    writer.finish({})
    return path


class Budget:
    def stopping(self):
        return False


def test_advantage_weights_use_outcomes_and_stop_gradient():
    targets = torch.tensor([1.0, 0.0, -1.0])
    values = torch.zeros(3, requires_grad=True)
    weights = advantage_weights(targets, values, 0.5)
    torch.testing.assert_close(weights, torch.exp(targets / 0.5))
    assert not weights.requires_grad
    assert advantage_weights(targets, values, 0.1).max() == 20
    with pytest.raises(ValueError, match="bounded"):
        advantage_weights(targets, values, 0)


def test_public_dataset_hash_mask_return_integrity_and_exact_epoch_restart(
    checkout, tmp_path
):
    encoder = make_encoder(CATALOG, "showdown-learned-observation-v3")
    env = ShowdownLearningEnv(checkout, encoder)
    try:
        path = make_data(tmp_path / "dataset", env.current, encoder)
        arrays, manifest, identity = load_dataset(path, encoder)
        assert manifest["completed_episodes"] == 2 and len(arrays["actions"]) == 8
        np.testing.assert_allclose(arrays["returns"][:4], [0.99**3, 0.99**2, 0.99, 1])
        with pytest.raises(ValueError, match="identity_changed"):
            load_dataset(path, encoder, expected_id="changed")
        full = LearnedPolicy(
            ROOT / "models/showdown_tactical_v4/model.zip", CATALOG
        ).model
        split = LearnedPolicy(
            ROOT / "models/showdown_tactical_v4/model.zip", CATALOG
        ).model
        config = {
            "dataset": str(path),
            "dataset_id": identity,
            "mode": "awr",
            "epochs": 2,
        }
        result = fit_offline(full, encoder, config, 2803, Budget())
        assert (
            result["optimizer_updates_this_launch"] == 2
            and result["parameter_l1_change"] > 0
        )
        fit_offline(split, encoder, {**config, "epochs": 1}, 2803, Budget())
        checkpoint = save_checkpoint(
            split, encoder, tmp_path / "checkpoint", {"scope": "offline-test"}
        )
        restored = LearnedPolicy(checkpoint, CATALOG).model
        fit_offline(restored, encoder, config, 2803, Budget(), completed_epochs=1)
        for a, b in zip(full.policy.parameters(), restored.policy.parameters()):
            torch.testing.assert_close(a, b, rtol=0, atol=0)
        masked = np.load(path / "masks.npy", mmap_mode="r+")
        masked[0, arrays["actions"][0]] = False
        masked.flush()
        with pytest.raises(ValueError, match="file_hash"):
            load_dataset(path, encoder)
        metadata = json.loads((path / "manifest.json").read_text())
        metadata["files"]["masks"] = file_hash(path / "masks.npy")
        atomic_json(path / "manifest.json", metadata)
        with pytest.raises(ValueError, match="integrity"):
            load_dataset(path, encoder)
    finally:
        env.close()


def test_bounded_offline_and_frozen_opponent_config():
    config = json.loads(
        (ROOT / "config/learning/general_dedicated_cpu.json").read_text()
    )
    experiment = config["experiments"][0]
    experiment["frozen_opponents"] = {"frozen_v2": "model.zip"}
    experiment["opponents"].append("frozen_v2")
    experiment["offline"] = {"dataset": "data", "mode": "awr", "epochs": 8}
    assert validate_config(config) is config
    experiment["offline"]["temperature"] = 0
    with pytest.raises(ValueError, match="offline"):
        validate_config(config)
    experiment.pop("offline")
    experiment["frozen_opponents"] = {"heuristic": "hidden.zip"}
    with pytest.raises(ValueError, match="frozen"):
        validate_config(config)
