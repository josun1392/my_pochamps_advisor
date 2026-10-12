"""Broad legality, public tactical semantics and frozen-model compatibility."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import numpy as np
import pytest
import torch
from advisor.learned_action_encoder import make_encoder
from advisor.learned_action_policy import (
    ActionExtractor,
    TacticalActionConditionedPolicy,
)
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_roster import BROAD_TRAIN, BROAD_UNSEEN
from advisor.learned_scenarios import TRAIN, scenario
from advisor.learned_tactics_encoder import (
    CONTEXT,
    ACTION,
    VERSION,
    TacticalObservationEncoder,
    public_side_conditions,
)
from advisor.learned_policy import LearnedPolicy
from advisor.showdown_environment import ShowdownEnvironment
from scripts.evaluate_showdown_policy import paired_comparisons

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_initial_v1/catalog.json"
CURRICULUM = "showdown-learning-curriculum-v3"


@pytest.fixture(scope="module")
def checkout():
    value = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not value:
        pytest.skip("external pinned native engine required")
    return value


@pytest.fixture(scope="module")
def view(checkout):
    with ShowdownEnvironment(checkout) as env:
        env.reset(scenario("validation", 11000, version=CURRICULUM))
        yield env.observation("self", include_history=True)


def test_broad_roster_disjoint_and_native_legality(checkout, tmp_path):
    assert len(TRAIN + BROAD_TRAIN) == 40 and len(BROAD_UNSEEN) == 14
    assert not {p[0] for p in TRAIN + BROAD_TRAIN} & {p[0] for p in BROAD_UNSEEN}
    cases = [
        scenario(split, i, version=CURRICULUM)
        for split in ("train", "validation", "unseen")
        for i in range(128)
    ]
    teams = [team for c in cases for team in c["teams"].values()]
    seen = {p["species"] for t in teams for p in t}
    assert seen == {p[0] for p in TRAIN + BROAD_TRAIN + BROAD_UNSEEN}
    path = tmp_path / "teams.json"
    path.write_text(json.dumps(teams), encoding="utf-8")
    code = "const fs=require('fs'),ps=require(process.argv[1]+'/dist/sim');const v=new ps.TeamValidator('gen9championsbssregmc');for(const t of JSON.parse(fs.readFileSync(process.argv[2]))){const e=v.validateTeam(t);if(e)throw Error(JSON.stringify(e));}"
    subprocess.run(
        ["node", "-e", code, checkout, str(path)], check=True, capture_output=True
    )
    assert scenario("train", 100000, version=CURRICULUM) != scenario(
        "validation", 0, version=CURRICULUM
    )
    assert scenario("validation", 11000, version=CURRICULUM) == scenario(
        "validation", 11000, version=CURRICULUM
    )


def test_side_conditions_absence_layers_removal_and_perspective():
    observation = {"side": "self", "public_history": []}
    assert public_side_conditions(observation)[9] == 0
    observation["public_history"] = [
        "|start",
        "|-sidestart|p1: self|Spikes",
        "|-sidestart|p1: self|Spikes",
        "|-sidestart|p2: opponent|move: Reflect",
    ]
    features = public_side_conditions(observation)
    assert (
        features[0] == pytest.approx(2 / 3) and features[9] == 1 and features[14] == 1
    )
    observation["side"] = "opponent"
    assert public_side_conditions(observation) == features[10:] + features[:10]
    observation["side"] = "self"
    observation["public_history"].append("|-sideend|p1: self|Spikes")
    assert public_side_conditions(observation)[0] == 0
    observation["public_history"].append("|-swapsideconditions")
    assert public_side_conditions(observation)[4] == 1


def test_tactics_native_facts_masks_immutability_and_privileged_rejection(view):
    encoder = TacticalObservationEncoder(CATALOG)
    original = deepcopy(view)
    x = encoder.encode(view)
    assert x.shape == (CONTEXT + 35 * ACTION,) and np.isfinite(x).all()
    assert view == original
    np.testing.assert_array_equal(
        x[CONTEXT:].reshape(35, ACTION)[:, -1], view["action_mask"]
    )
    assert encoder._tactic("willowisp")[0] == 1
    assert encoder._tactic("recover")[23] == 0.5
    assert encoder._tactic("swordsdance")[6] == pytest.approx(2 / 6)
    assert encoder._tactic("irondefense")[7] == pytest.approx(2 / 6)
    for key in ("seed", "teams", "checkpoint", "queue", "native_state"):
        with pytest.raises(ValueError, match="privileged"):
            encoder.encode({**view, key: {}})
    with pytest.raises(ValueError, match="public_history"):
        encoder.encode({k: v for k, v in view.items() if k != "public_history"})
    assert (
        make_encoder(CATALOG, VERSION).catalog_fingerprint
        == encoder.catalog_fingerprint
    )


def test_frozen_v1_v2_inference_still_legal(view):
    for name in ("showdown_initial_v1", "showdown_action_v2"):
        policy = LearnedPolicy(ROOT / f"models/{name}/model.zip", CATALOG)
        assert view["action_mask"][policy.act(view)]


def test_v3_hidden_set_seed_and_provenance_do_not_enter_features(checkout):
    from scripts.verify_showdown_integration import fixture_scenarios

    encoder = TacticalObservationEncoder(CATALOG)
    case = fixture_scenarios()[0]
    for team in case["teams"].values():
        for pokemon in team:
            pokemon["gender"] = "N" if pokemon["species"] == "Rotom-Wash" else "M"
    altered = deepcopy(case)
    altered["teams"]["opponent"][0].update(
        item="Choice Scarf",
        moves=["U-turn", "Iron Head"],
        evs={"hp": 32, "atk": 32, "spd": 2},
    )
    with ShowdownEnvironment(checkout) as env:
        env.reset(case)
        visible = env.observation("self", include_history=True)
        before = encoder.encode(visible)
        env.reset(altered, seed=[901, 802, 703, 604])
        np.testing.assert_array_equal(
            before, encoder.encode(env.observation("self", include_history=True))
        )
        visible.update(episode_id="unrelated-identity", revision=999)
        np.testing.assert_array_equal(before, encoder.encode(visible))


def test_v3_action_permutation_and_value_symmetry(view):
    torch.set_num_threads(1)
    encoder = TacticalObservationEncoder(CATALOG)
    x = encoder.encode(view)
    changed = deepcopy(view)
    slots = changed["own_request"]["active"][0]["moves"]
    slots[0], slots[1] = slots[1], slots[0]
    pairs = [(6, 7), (10, 11), (27, 28), (31, 32)]
    order = list(range(35))
    for a, b in pairs:
        changed["action_mask"][a], changed["action_mask"][b] = (
            changed["action_mask"][b],
            changed["action_mask"][a],
        )
        order[a], order[b] = order[b], order[a]
    y = encoder.encode(changed)
    np.testing.assert_array_equal(x[:CONTEXT], y[:CONTEXT])
    np.testing.assert_allclose(
        x[CONTEXT:].reshape(35, ACTION)[order],
        y[CONTEXT:].reshape(35, ACTION),
        atol=1e-7,
    )
    network = ActionExtractor(CONTEXT, ACTION)
    with torch.no_grad():
        torch.testing.assert_close(
            network.forward_actor(torch.tensor(x)[None])[0][order],
            network.forward_actor(torch.tensor(y)[None])[0],
        )
        torch.testing.assert_close(
            network.forward_critic(torch.tensor(x)[None]),
            network.forward_critic(torch.tensor(y)[None]),
        )


def test_paired_clusters_use_configured_rival_count():
    records = [
        {
            "policy": p,
            "case": case,
            "winner": "self" if p == "candidate" else "opponent",
            "truncated": False,
        }
        for p in ("candidate", "heuristic")
        for case in range(4)
        for rival in range(4)
    ]
    result = paired_comparisons(records, {"candidate": None, "heuristic": None})
    assert result[0]["paired_win_fraction_difference"] == 1
    assert result[0]["case_cluster_bootstrap_95"] == [1, 1]


def test_native_evaluation_records_executed_player_moves(checkout):
    from scripts.evaluate_showdown_policy import evaluate

    result = evaluate(
        checkout,
        CATALOG,
        {"heuristic": "heuristic"},
        cases=1,
        offset=11000,
        curriculum_version=CURRICULUM,
        rivals={"heuristic": "heuristic"},
    )
    row = result["records"][0]
    assert sum(row["native_own_move_counts"].values()) > 0
    assert (
        result["summaries"][0]["native_own_move_counts"]
        == row["native_own_move_counts"]
    )
    assert "pivot" in result["action_count_scope"]


def test_adapted_public_baseline_completes_native_battle(checkout):
    own, other = (
        VisibleBaseline("champions_heuristic", 41),
        VisibleBaseline("heuristic", 42),
    )
    with ShowdownEnvironment(checkout) as env:
        env.reset(scenario("validation", 11003, version=CURRICULUM))
        for _ in range(256):
            first = env.observation("self", include_history=True)
            second = env.observation("opponent", include_history=True)
            snapshot = deepcopy(first)
            action = own.act(first)
            assert first == snapshot and first["action_mask"][action]
            outcome = env.step(
                {"self": action, "opponent": other.act(second)},
                revision=first["revision"],
            )
            if outcome["terminated"] or outcome["truncated"]:
                break
        assert outcome["terminated"]


def test_adapted_recovery_uses_upstream_target_enum():
    from types import SimpleNamespace
    from poke_env.battle import Move

    heal = Move("recover", gen=9)
    baseline = VisibleBaseline("champions_heuristic")
    baseline.battle = SimpleNamespace(
        active_pokemon=SimpleNamespace(current_hp_fraction=0.3),
        opponent_active_pokemon=object(),
        available_moves=[heal],
    )
    player = SimpleNamespace(_estimate_matchup=lambda a, b: 0.5)
    assert baseline._champions_choice(player) is heal


def test_native_haze_clears_projected_boosts_and_matches_poke_env(checkout):
    own = [(s, a, m) for s, a, m, _, _ in TRAIN if s != "Scizor"][:5]

    def member(s, a, m):
        return {
            "species": s,
            "ability": a,
            "moves": m,
            "level": 50,
            "nature": "Adamant",
            "evs": {"hp": 32, "atk": 32, "spe": 2},
        }

    case = {
        "scenario_id": "public-haze-regression",
        "teams": {
            "self": [
                member(
                    "Scizor",
                    "Technician",
                    ["Swords Dance", "Bullet Punch", "U-turn", "Close Combat"],
                )
            ]
            + [member(*p) for p in own],
            "opponent": [
                member("Toxapex", "Regenerator", ["Haze", "Surf", "Toxic", "Recover"])
            ]
            + [member(*p) for p in own],
        },
        "seed": [1, 2, 3, 4],
        "preview": {"self": [1, 2, 3], "opponent": [1, 2, 3]},
        "history": [],
        "assumptions": ["hypothetical regression only"],
    }
    with ShowdownEnvironment(checkout) as env:
        env.reset(case)
        view = env.observation("self", include_history=True)
        env.step({"self": 6, "opponent": 6}, revision=view["revision"])
        view = env.observation("self", include_history=True)
        assert "|-clearallboost" in view["public_history"]
        row = view["state"]["self_side"]["pokemon"][
            view["state"]["self_side"]["active_identity"]
        ]
        assert row["stat_stages"].get("atk", 0) == 0
        baseline = VisibleBaseline("heuristic", 12)
        baseline.act(view)
        assert baseline.battle.active_pokemon.boosts["atk"] == 0


@pytest.mark.parametrize(
    "event,expected",
    [
        ("-clearboost", {}),
        ("-clearpositiveboost", {"atk": 0, "def": -1}),
        ("-clearnegativeboost", {"atk": 2, "def": 0}),
        ("-invertboost", {"atk": -2, "def": 1}),
    ],
)
def test_public_target_boost_events_do_not_change_native_request_or_truth(
    view, event, expected
):
    from advisor.showdown_observation import project_policy_observation

    original = deepcopy(view)
    identity = view["state"]["opponent_side"]["active_identity"]
    history = view["public_history"] + [
        f"|-setboost|{identity}|atk|2",
        f"|-setboost|{identity}|def|-1",
        f"|{event}|{identity}",
    ]
    result = project_policy_observation(view, history)
    assert (
        result["state"]["opponent_side"]["pokemon"][identity]["stat_stages"] == expected
    )
    assert original == view and result["own_request"] == view["own_request"]


def test_v3_actual_updates_reload_strategy_ui_and_rollback(checkout, tmp_path):
    from sb3_contrib import MaskablePPO
    from advisor.learned_gym import ShowdownLearningEnv
    from scripts.train_showdown_autonomous import save_checkpoint, optimizer_steps
    from tests.test_showdown_strategy_evaluation import configuration
    from tests.test_showdown_shadow_ui import run
    from advisor.showdown_worker import ShowdownWorker
    from llm.advisor_learned_strategy import valid_learned_evidence

    encoder = TacticalObservationEncoder(CATALOG)
    torch.set_num_threads(1)
    with ShowdownLearningEnv(checkout, encoder, curriculum_version=CURRICULUM) as env:
        model = MaskablePPO(
            TacticalActionConditionedPolicy,
            env,
            n_steps=128,
            batch_size=128,
            n_epochs=2,
            seed=101,
            device="cpu",
        )
        before = torch.cat(
            [p.detach().flatten() for p in model.policy.parameters()]
        ).clone()
        model.learn(256)
        assert (
            optimizer_steps(model) > 0
            and (
                torch.cat([p.detach().flatten() for p in model.policy.parameters()])
                - before
            )
            .abs()
            .sum()
            > 0
        )
        path = save_checkpoint(
            model, encoder, tmp_path / "native-v3", {"curriculum_version": CURRICULUM}
        )
        restored = LearnedPolicy(path, CATALOG)
        assert restored.act(env.current) == int(
            model.predict(
                encoder.encode(env.current),
                deterministic=True,
                action_masks=env.action_masks(),
            )[0]
        )
    snapshot, builder, context = configuration(horizon=1)
    context["learned_policy"] = {
        "schema_version": "showdown-learned-config-v1",
        "enabled": True,
        "model_path": path,
        "catalog_path": str(CATALOG),
        "expected_model_id": restored.model_id,
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


def test_frozen_v2_function_transfer_preserves_legal_distribution_value_and_optimizer(
    checkout,
):
    from sb3_contrib import MaskablePPO
    from advisor.learned_gym import ShowdownLearningEnv
    from advisor.learned_action_policy import transfer_v2_weights

    source = LearnedPolicy(ROOT / "models/showdown_action_v2/model.zip", CATALOG)
    encoder = TacticalObservationEncoder(CATALOG)
    with ShowdownLearningEnv(checkout, encoder, curriculum_version=CURRICULUM) as env:
        target = MaskablePPO(
            TacticalActionConditionedPolicy,
            env,
            n_steps=128,
            batch_size=128,
            n_epochs=2,
            seed=211,
            device="cpu",
        )
        transfer_v2_weights(target.policy, source.model.policy)
        assert not target.policy.optimizer.state
        for i in range(24):
            env.reset(seed=11000 + i)
            observation = env.current
            mask = env.action_masks()[None, :]
            with torch.no_grad():
                old = torch.tensor(source.encoder.encode(observation))[None]
                new = torch.tensor(encoder.encode(observation))[None]
                torch.testing.assert_close(
                    source.model.policy.get_distribution(
                        old, action_masks=mask
                    ).distribution.probs,
                    target.policy.get_distribution(
                        new, action_masks=mask
                    ).distribution.probs,
                    atol=1e-6,
                    rtol=1e-6,
                )
                torch.testing.assert_close(
                    source.model.policy.predict_values(old),
                    target.policy.predict_values(new),
                    atol=1e-6,
                    rtol=1e-6,
                )
        target.learn(256)
        assert target.policy.optimizer.state
