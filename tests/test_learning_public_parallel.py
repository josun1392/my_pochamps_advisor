"""Policy-visible results, function-preserving public features and real spawn."""

from copy import deepcopy
import os
from pathlib import Path
import numpy as np
import pytest
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from advisor.learned_action_encoder import make_encoder
from advisor.learned_action_policy import PublicInteractionPolicy, transfer_v3_weights
from advisor.learned_gym import ShowdownLearningEnv
from advisor.learned_parallel import LearningEnvFactory
from advisor.learned_policy import LearnedPolicy
from advisor.learned_public_interactions import public_history_summary, VERSION
from scripts.train_showdown_autonomous import validate_config

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_initial_v1/catalog.json"


@pytest.fixture(scope="module")
def checkout():
    value = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not value:
        pytest.skip("pinned native checkout required")
    return value


def test_gym_info_has_no_opponent_private_request_or_future_rng(checkout):
    env = ShowdownLearningEnv(
        checkout,
        make_encoder(CATALOG, "showdown-learned-observation-v3"),
        opponents=["max_power"],
    )
    try:
        env.reset(seed=781)
        for _ in range(96):
            action = int(np.flatnonzero(env.action_masks())[-1])
            _, _, ended, truncated, info = env.step(action)
            assert info["schema_version"] == "showdown-learning-info-v2"
            assert set(info["native_outcome"]) == {
                "revision",
                "decisions",
                "terminated",
                "truncated",
                "winner",
                "action_rejected",
                "rewards",
            }
            if ended or truncated:
                assert env.drain_completed() and env.drain_completed() == []
                env.reset()
        assert env.learning_resources()["rss_bytes"] > 0
    finally:
        env.close()


def test_public_history_failure_order_and_wish_are_samples(checkout):
    encoder = make_encoder(CATALOG, VERSION)
    env = ShowdownLearningEnv(checkout, encoder)
    try:
        view = deepcopy(env.current)
        own = view["state"]["self_side"]["active_identity"]
        other = view["state"]["opponent_side"]["active_identity"]
        view["turn"] = 3
        view["public_history"] = [
            "|start",
            "|turn|1",
            f"|move|{other}|Surf|{own}",
            f"|move|{own}|Recover|{own}",
            f"|-fail|{own}|heal",
            "|turn|2",
        ]
        h, last = public_history_summary(view, encoder.catalog, encoder.tactics)
        assert h[:4] == [1, 0, 1, 1] and last == "recover"
        unknown = deepcopy(view)
        unknown["public_history"][2] = f"|move|{other}|Unidentified Move|{own}"
        assert (
            public_history_summary(unknown, encoder.catalog, encoder.tactics)[0][2] == 0
        )
        view["public_history"] += [f"|move|{own}|Wish|{own}", "|turn|3"]
        h, last = public_history_summary(view, encoder.catalog, encoder.tactics)
        assert h[3] == 0 and h[12] == 1 and last == "wish"
        changed = deepcopy(view)
        changed.update(revision=999, episode_id="other-session")
        np.testing.assert_array_equal(encoder.encode(view), encoder.encode(changed))
        for k in ("seed", "native_state", "teams", "queue"):
            changed[k] = {}
            with pytest.raises(ValueError, match="privileged"):
                encoder.encode(changed)
            changed.pop(k)
    finally:
        env.close()


def test_v3_transfer_preserves_masked_policy_value_and_native_legality(checkout):
    source = LearnedPolicy(ROOT / "models/showdown_tactical_v4/model.zip", CATALOG)
    encoder = make_encoder(CATALOG, VERSION)
    env = ShowdownLearningEnv(checkout, encoder)
    vector = DummyVecEnv([lambda: env])
    try:
        model = MaskablePPO(
            PublicInteractionPolicy,
            vector,
            n_steps=128,
            batch_size=128,
            seed=71,
            device="cpu",
        )
        transfer_v3_weights(model.policy, source.model.policy)
        for _ in range(12):
            view = env.current
            old = torch.tensor(source.encoder.encode(view))[None]
            new = torch.tensor(encoder.encode(view))[None]
            mask = np.asarray(view["action_mask"])[None]
            with torch.no_grad():
                a = source.model.policy.get_distribution(
                    old, action_masks=mask
                ).distribution.probs
                b = model.policy.get_distribution(
                    new, action_masks=mask
                ).distribution.probs
                torch.testing.assert_close(a, b, rtol=1e-6, atol=1e-7)
                torch.testing.assert_close(
                    source.model.policy.predict_values(old),
                    model.policy.predict_values(new),
                    rtol=1e-6,
                    atol=5e-7,
                )
            _, _, ended, truncated, _ = env.step(int(a.argmax()))
            if ended or truncated:
                env.reset()
    finally:
        vector.close()


def test_spawn_matches_dummy_seeded_episodes_and_masks(checkout):
    factories = [
        LearningEnvFactory(
            checkout,
            str(CATALOG),
            "showdown-learned-observation-v3",
            i * 100000,
            "showdown-learning-curriculum-v3",
            ("max_power",),
            {},
        )
        for i in range(2)
    ]
    a, b = DummyVecEnv(factories), SubprocVecEnv(factories, start_method="spawn")
    try:
        a.seed(791)
        b.seed(791)
        np.testing.assert_array_equal(a.reset(), b.reset())
        for _ in range(40):
            ma, mb = (
                np.array(a.env_method("action_masks")),
                np.array(b.env_method("action_masks")),
            )
            np.testing.assert_array_equal(ma, mb)
            actions = [int(np.flatnonzero(mask)[-1]) for mask in ma]
            xa, ra, da, ia = a.step(actions)
            b.step_async(actions)
            xb, rb, db, ib = b.step_wait()
            np.testing.assert_array_equal(xa, xb)
            np.testing.assert_array_equal(ra, rb)
            np.testing.assert_array_equal(da, db)
            assert [i["native_outcome"] for i in ia] == [
                i["native_outcome"] for i in ib
            ]
        assert a.env_method("drain_completed") == b.env_method("drain_completed")
    finally:
        a.close()
        b.close()


def test_worker_and_tensor_limits_fail_closed():
    config = {
        "schema_version": "showdown-autonomous-training-v1",
        "max_runtime_seconds": 60,
        "envs": 8,
        "vector_backend": "subproc",
        "memory_mib": 8192,
        "cpu_percent": 50,
        "cpu_threads": 4,
        "checkpoint_steps": 1024,
        "experiments": [{"seed": 911, "steps": 1024, "encoder_version": VERSION}],
    }
    assert validate_config(config) == config
    for key, bad in (
        ("envs", 16),
        ("memory_mib", 3072),
        ("cpu_threads", 16),
        ("gpu_memory_fraction", 0.9),
    ):
        changed = dict(config, **{key: bad})
        with pytest.raises(ValueError):
            validate_config(changed)


def test_failed_heal_counts_require_native_failure_events():
    from scripts.evaluate_showdown_policy import native_heal_failures

    own = "p1a: slot-0"
    history = [
        f"|move|{own}|Recover|{own}",
        f"|-fail|{own}|heal",
        "|move|p2a: slot-0|Surf|p1a: slot-0",
        f"|move|{own}|Recover|{own}",
        f"|-fail|{own}|heal",
        f"|move|{own}|Recover|{own}",
        f"|-heal|{own}|100/100",
        f"|move|{own}|Recover|{own}",
        f"|-fail|{own}|heal",
    ]
    assert native_heal_failures(history) == (3, 2)
    assert native_heal_failures(
        [
            f"|move|{own}|Recover|{own}",
            f"|-heal|{own}|100/100",
            "|-fail|p2a: slot-0|heal",
        ]
    ) == (0, 0)


def test_coherent_curriculum_native_legality_and_disjoint_species(checkout):
    from advisor.learned_scenarios import scenario, TRAIN
    from advisor.learned_coherent_curriculum import EXTRA_TRAIN, EXTRA_UNSEEN
    from advisor.learned_roster import BROAD_TRAIN, BROAD_UNSEEN
    from advisor.showdown_environment import ShowdownEnvironment

    version = "showdown-learning-curriculum-v5"
    train_pool = {r[0] for r in TRAIN + BROAD_TRAIN + EXTRA_TRAIN}
    unseen_pool = {r[0] for r in BROAD_UNSEEN + EXTRA_UNSEEN}
    assert len(train_pool) == 55 and len(unseen_pool) == 20
    assert not train_pool & unseen_pool
    covered = set()
    with ShowdownEnvironment(checkout) as env:
        for split in ("validation", "unseen"):
            for index in range(27000, 27096):
                case = scenario(split, index, version=version)
                assert case == scenario(split, index, version=version)
                assert case != scenario("train", index, version=version)
                env.reset(case)
                for team in case["teams"].values():
                    covered.update(p["species"] for p in team)
                    assert all(p["item"] != "Choice Scarf" for p in team)
                assert any(env.observation("self")["action_mask"])
    assert covered == train_pool | unseen_pool


def test_new_action_rows_keep_slot_permutation_symmetry_and_hidden_isolation(checkout):
    from advisor.learned_public_interactions import CONTEXT, ACTION
    from scripts.verify_showdown_integration import fixture_scenarios
    from advisor.showdown_environment import ShowdownEnvironment

    encoder = make_encoder(CATALOG, VERSION)
    case = fixture_scenarios()[0]
    for team in case["teams"].values():
        for p in team:
            p["gender"] = "N" if p["species"] == "Rotom-Wash" else "M"
    changed = deepcopy(case)
    changed["teams"]["opponent"][0].update(
        item="Choice Scarf",
        moves=["U-turn", "Iron Head"],
        evs={"hp": 32, "atk": 32, "spd": 2},
    )
    with ShowdownEnvironment(checkout) as env:
        env.reset(case)
        view = env.observation("self", include_history=True)
        x = encoder.encode(view)
        env.reset(changed, seed=[901, 802, 703, 604])
        np.testing.assert_array_equal(
            x, encoder.encode(env.observation("self", include_history=True))
        )
    swapped = deepcopy(view)
    swapped["own_request"]["active"][0]["moves"][:2] = reversed(
        swapped["own_request"]["active"][0]["moves"][:2]
    )
    roster = swapped["own_request"]["side"]["pokemon"]
    roster[1], roster[2] = roster[2], roster[1]
    order = list(range(35))
    for a, b in ((1, 2), (6, 7), (10, 11), (27, 28), (31, 32)):
        order[a], order[b] = order[b], order[a]
        swapped["action_mask"][a], swapped["action_mask"][b] = (
            swapped["action_mask"][b],
            swapped["action_mask"][a],
        )
    y = encoder.encode(swapped)
    np.testing.assert_allclose(x[:CONTEXT], y[:CONTEXT], atol=1e-7, rtol=0)
    np.testing.assert_allclose(
        x[CONTEXT:].reshape(35, ACTION)[order],
        y[CONTEXT:].reshape(35, ACTION),
        atol=1e-7,
        rtol=0,
    )


def test_public_interaction_actual_opt_in_strategy_keeps_default_and_truth(
    checkout, tmp_path
):
    import json
    from scripts.train_showdown_autonomous import save_checkpoint
    from advisor.showdown_worker import ShowdownWorker
    from llm.advisor_learned_strategy import valid_learned_evidence
    from tests.test_showdown_strategy_evaluation import configuration
    from tests.test_showdown_shadow_ui import run

    source = LearnedPolicy(ROOT / "models/showdown_tactical_v4/model.zip", CATALOG)
    encoder = make_encoder(CATALOG, VERSION)
    env = ShowdownLearningEnv(checkout, encoder)
    vector = DummyVecEnv([lambda: env])
    try:
        model = MaskablePPO(
            PublicInteractionPolicy,
            vector,
            n_steps=128,
            batch_size=128,
            device="cpu",
            seed=11,
        )
        transfer_v3_weights(model.policy, source.model.policy)
        path = save_checkpoint(model, encoder, tmp_path / "checkpoint", {})
    finally:
        vector.close()
    snapshot, builder, context = configuration(horizon=1)
    context["learned_policy"] = {
        "schema_version": "showdown-learned-config-v1",
        "enabled": True,
        "model_path": path,
        "catalog_path": str(CATALOG),
        "expected_model_id": json.loads(Path(path).with_suffix(".json").read_text())[
            "model_sha256"
        ],
    }
    original = deepcopy((snapshot, context))
    with ShowdownWorker(checkout) as worker:
        baseline = run(snapshot, builder)
        result = run(
            snapshot, builder, showdown_context=context, showdown_bridge=worker
        )
    assert (snapshot, context) == original
    for key in (
        "orchestration",
        "exact_outcome_ledgers",
        "descriptive_metrics",
        "opponent_response_profiles",
        "execution_coverage",
    ):
        assert result[key] == baseline[key]
    evidence = result["explanation"]["sampled_simulation"]
    for row in evidence["scenarios"]:
        assert row["learned_policy"]["status"] == "evaluated"
        assert valid_learned_evidence(row["learned_policy"], evidence, row)
        assert row["learned_policy"]["inference"]["encoder_version"] == VERSION
