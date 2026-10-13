"""Public categorical contracts, entity bindings, native integration and rollback."""
from copy import deepcopy
import json
import os
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
gym = pytest.importorskip("gymnasium")
pytest.importorskip("sb3_contrib")
from sb3_contrib import MaskablePPO
from advisor.learned_action_encoder import make_encoder
from advisor.learned_action_policy import TacticalActionConditionedPolicy, PublicInteractionPolicy
from advisor.learned_public_categories import (
    PublicCategoricalEncoder, VERSION, BASE_CONTEXT, BASE_ACTION, CONTEXT, ACTION,
    ENTITY, ENTITIES, ENTITY_NUMERIC, BITS, UNKNOWN, ABSENT, PAD, KNOWN_MOVES,
)
from advisor.learned_public_categories_policy import PublicCategoricalPolicy, transfer_public_categorical_weights
from advisor.learned_public_interactions import PublicInteractionEncoder
from advisor.learned_tactics_encoder import TacticalObservationEncoder
from advisor.learned_policy import LearnedPolicy
from scripts.train_showdown_autonomous import save_checkpoint, validate_config
from scripts.build_showdown_public_categories import build, OUTPUT

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_mc_domain_v1/catalog.json"


class Spaces(gym.Env):
    def __init__(self, dimension):
        self.action_space = gym.spaces.Discrete(35)
        self.observation_space = gym.spaces.Box(-2, 4, (dimension,), dtype=np.float32)


def model(encoder, policy=PublicCategoricalPolicy):
    torch.set_num_threads(1)
    return MaskablePPO(policy, Spaces(encoder.dimension), seed=91, n_steps=8,
                       batch_size=8, learning_rate=5e-5, device="cpu")


@pytest.fixture(scope="module")
def view():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned native engine required")
    from advisor.showdown_environment import ShowdownEnvironment
    from advisor.learned_scenarios import scenario
    with ShowdownEnvironment(checkout) as env:
        env.reset(scenario("train", 3401, version="showdown-learning-curriculum-v8"))
        return env.observation("self", include_history=True)


def split(encoder, view):
    x = encoder.encode(view)
    return x, x[BASE_CONTEXT:CONTEXT].reshape(ENTITIES, ENTITY), x[CONTEXT:].reshape(35, ACTION)


def decode(bits):
    return int(np.dot(bits, 2 ** np.arange(len(bits))))


def test_vocabulary_native_source_reproducibility_and_no_aliasing():
    assert json.loads(OUTPUT.read_text()) == build()
    encoder = PublicCategoricalEncoder(CATALOG)
    assert {k: len(v) for k, v in encoder.tokens.items()} == {"species": 1586, "moves": 939, "abilities": 215, "items": 166}
    for kind, tokens in encoder.tokens.items():
        assert len(set(tokens.values())) == len(tokens)
        assert not set(tokens.values()) & {PAD, UNKNOWN, ABSENT}
        for value in ({}, {"knowledge": "unknown"}, ""):
            assert encoder.token(kind, value) == UNKNOWN
        assert encoder.token(kind, None) == ABSENT
    for a, b in (("rest", "imprison"), ("encore", "disable")):
        assert encoder.token("moves", a) != encoder.token("moves", b)
    assert encoder.token("species", "Scizor-Mega") != encoder.token("species", "Scizor")
    assert encoder.token("abilities", "Mega Sol") != encoder.token("abilities", "Drought")
    assert encoder.token("items", "Life Orb") != encoder.token("items", "Leftovers")
    assert make_encoder(CATALOG, VERSION).feature_contract == encoder.feature_contract


def test_numeric_features_and_individual_relationships_are_preserved(view):
    encoder, old = PublicCategoricalEncoder(CATALOG), PublicInteractionEncoder(CATALOG)
    x, entities, actions = split(encoder, view)
    base = old.encode(view)
    np.testing.assert_array_equal(x[:BASE_CONTEXT], base[:BASE_CONTEXT])
    reconstructed = np.concatenate((actions[:, :BASE_ACTION - 1], actions[:, -1:]), axis=1)
    np.testing.assert_array_equal(reconstructed, base[BASE_CONTEXT:].reshape(35, BASE_ACTION))
    np.testing.assert_array_equal(x, encoder.encode(deepcopy(view)))
    own = sorted(view["state"]["self_side"]["pokemon"].items())
    for i, (_, row) in enumerate(own):
        np.testing.assert_array_equal(entities[i, :63], np.array(old._row(row), dtype=np.float32))
        offset = ENTITY_NUMERIC
        for kind, key in (("species", "details"), ("abilities", "current_ability"), ("items", "known_item")):
            assert decode(entities[i, offset:offset + BITS[kind]]) == encoder.token(kind, row.get(key, {}))
            offset += BITS[kind]
        for j, move in enumerate(row["known_moves"]):
            assert decode(entities[i, offset + j * 10:offset + (j + 1) * 10]) == encoder.token("moves", move)
    # Every own native candidate references its exact record, not a pooled team.
    names = {key.split(": ", 1)[-1]: i + 1 for i, (key, _) in enumerate(own)}
    for i, p in enumerate(view["own_request"]["side"]["pokemon"]):
        assert decode(actions[i, BASE_ACTION - 1:BASE_ACTION + 4]) == names[p["ident"].split(": ", 1)[-1]]
    # Own/opponent previews are public records independent of appearance identities.
    assert entities[12, 66] == entities[18, 66] == 1
    for i in (12, 18):
        assert decode(entities[i, ENTITY_NUMERIC + 11:ENTITY_NUMERIC + 20]) == UNKNOWN


def test_unknown_absence_no_hidden_inference_and_fail_closed(view):
    encoder = PublicCategoricalEncoder(CATALOG)
    own_key = next(iter(view["state"]["self_side"]["pokemon"]))
    variants = []
    for item in ({"knowledge": "unknown"}, None, "lifeorb", "leftovers"):
        changed = deepcopy(view)
        changed["state"]["self_side"]["pokemon"][own_key]["known_item"] = item
        variants.append(encoder.encode(changed))
    assert all(not np.array_equal(a, b) for i, a in enumerate(variants) for b in variants[i + 1:])
    # A legal species does not reveal which of its possible abilities/items/moves is held.
    _, rows, _ = split(encoder, view)
    opponent = rows[6]
    assert decode(opponent[ENTITY_NUMERIC + 11:ENTITY_NUMERIC + 20]) == UNKNOWN
    for root in ("native_state", "seed", "checkpoint", "scenario", "teams", "queue"):
        with pytest.raises(ValueError, match="privileged"):
            encoder.encode({**view, root: {"hidden": "marker"}})
    wrong = deepcopy(view); wrong["state"]["state_version"] = "showdown-policy-state-v1"
    with pytest.raises(ValueError, match="versioned_public_state"):
        encoder.encode(wrong)
    wrong = deepcopy(view); wrong["state"]["self_side"]["pokemon"][own_key]["known_item"] = "futureunknownitem"
    with pytest.raises(ValueError, match="unsupported_known_public_items"):
        encoder.encode(wrong)
    wrong = deepcopy(view); wrong["state"]["self_side"]["pokemon"][own_key]["known_moves"] = ["protect"] * (KNOWN_MOVES + 1)
    with pytest.raises(ValueError, match="capacity"):
        encoder.encode(wrong)
    wrong = deepcopy(view); wrong["own_request"]["active"][0]["moves"][0]["id"] = "unknownlegalmove"
    with pytest.raises(ValueError, match="unsupported_known_public_moves"):
        encoder.encode(wrong)
    wrong = deepcopy(view); wrong["action_mask"][5] = True
    with pytest.raises(ValueError, match="unbound_public_legal_switch"):
        encoder.encode(wrong)
    wrong = deepcopy(view); wrong["state"]["self_side"]["pokemon"]["p1z: duplicate"] = deepcopy(next(iter(wrong["state"]["self_side"]["pokemon"].values())))
    wrong["state"]["self_side"]["pokemon"]["p1a: duplicate"] = deepcopy(wrong["state"]["self_side"]["pokemon"]["p1z: duplicate"])
    with pytest.raises(ValueError, match="ambiguous_own"):
        encoder.encode(wrong)


@pytest.mark.parametrize("old_encoder,old_policy", [(TacticalObservationEncoder, TacticalActionConditionedPolicy),
                                                   (PublicInteractionEncoder, PublicInteractionPolicy)])
def test_function_preserving_transfer_with_explicit_fresh_optimizer(view, old_encoder, old_policy):
    source_encoder, encoder = old_encoder(CATALOG), PublicCategoricalEncoder(CATALOG)
    source, target = model(source_encoder, old_policy), model(encoder)
    sum(p.sum() for p in source.policy.parameters()).backward(); source.policy.optimizer.step()
    assert source.policy.optimizer.state
    transfer_public_categorical_weights(target.policy, source.policy)
    assert not target.policy.optimizer.state
    with torch.no_grad():
        a, b = torch.tensor(source_encoder.encode(view))[None], torch.tensor(encoder.encode(view))[None]
        mask = np.array(view["action_mask"])[None]
        torch.testing.assert_close(source.policy.get_distribution(a, action_masks=mask).distribution.probs,
                                   target.policy.get_distribution(b, action_masks=mask).distribution.probs, atol=1e-7, rtol=1e-6)
        torch.testing.assert_close(source.policy.predict_values(a), target.policy.predict_values(b), atol=1e-7, rtol=1e-6)


def test_actor_critic_permutation_masking_and_shared_embedding_gradients(view):
    encoder = PublicCategoricalEncoder(CATALOG); m = model(encoder)
    x = torch.tensor(encoder.encode(view))[None]
    permutation = torch.randperm(35)
    y = torch.cat((x[:, :CONTEXT], x[:, CONTEXT:].reshape(1, 35, ACTION)[:, permutation].flatten(1)), dim=1)
    mask = np.array(view["action_mask"])[None]
    with torch.no_grad():
        p = m.policy.get_distribution(x, action_masks=mask).distribution.probs
        q = m.policy.get_distribution(y, action_masks=mask[:, permutation]).distribution.probs
        torch.testing.assert_close(q, p[:, permutation])
        torch.testing.assert_close(m.policy.predict_values(x), m.policy.predict_values(y), atol=1e-7, rtol=1e-6)
        assert not p[0, ~mask[0]].any()
    m.policy.mlp_extractor.forward_actor(x).sum().backward()
    for embedding in m.policy.mlp_extractor.embeddings.values():
        assert embedding.weight.grad.abs().sum() > 0
    bad = x.clone(); bad[0, BASE_CONTEXT + ENTITY_NUMERIC] = .5
    with pytest.raises(ValueError, match="nonbinary"):
        m.policy.predict_values(bad)


def test_strict_save_reload_and_original_contract_backwards_compatibility(view, tmp_path):
    encoder = PublicCategoricalEncoder(CATALOG); m = model(encoder)
    path = save_checkpoint(m, encoder, tmp_path / "categorical", {})
    restored = LearnedPolicy(path, CATALOG)
    with torch.no_grad():
        x = torch.tensor(encoder.encode(view))[None]; mask = np.array(view["action_mask"])[None]
        expected = m.policy.get_distribution(x, action_masks=mask).distribution.probs[0].numpy()
    np.testing.assert_array_equal(restored.infer(view)["action_probabilities"], expected.astype(float))
    for v in ("showdown-learned-observation-v3", "showdown-learned-observation-v4"):
        old = make_encoder(CATALOG, v)
        policy = TacticalActionConditionedPolicy if v.endswith("v3") else PublicInteractionPolicy
        old_path = save_checkpoint(model(old, policy), old, tmp_path / v, {})
        assert LearnedPolicy(old_path, CATALOG).infer(view)["encoder_version"] == v
    metadata = Path(path).with_suffix(".json"); data = json.loads(metadata.read_text())
    data["feature_contract"]["token_map_sha256"] = "mismatch"; metadata.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="public_categorical_feature_contract"):
        LearnedPolicy(path, CATALOG)


def test_trainer_opt_in_config_and_fresh_optimizer_requirement():
    config = {"schema_version": "showdown-autonomous-training-v1", "max_runtime_seconds": 60,
              "experiments": [{"seed": 91, "steps": 4096, "encoder_version": VERSION}]}
    validate_config(config)
    config["experiments"][0]["transfer_model"] = "trusted.zip"
    with pytest.raises(ValueError, match="explicit_fresh_optimizer"):
        validate_config(config)
    config["experiments"][0]["fresh_optimizer"] = True
    validate_config(config)


def test_native_unrevealed_set_future_rng_and_preview_binding_isolation():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned native engine required")
    from advisor.showdown_environment import ShowdownEnvironment
    from scripts.verify_showdown_integration import fixture_scenarios
    encoder = PublicCategoricalEncoder(CATALOG)
    case = fixture_scenarios()[0]
    for team in case["teams"].values():
        for pokemon in team:
            pokemon["gender"] = "N" if pokemon["species"] == "Rotom-Wash" else "M"
    changed = deepcopy(case)
    changed["teams"]["opponent"][0].update(item="Choice Scarf", moves=["U-turn", "Iron Head"],
                                              evs={"hp": 32, "atk": 32, "spd": 2})
    with ShowdownEnvironment(checkout) as env:
        env.reset(case); view = env.observation("self", include_history=True)
        before = encoder.encode(view)
        env.reset(changed, seed=[901, 802, 703, 604])
        np.testing.assert_array_equal(before, encoder.encode(env.observation("self", include_history=True)))
    # Apparent identity under possible Illusion is flagged; its preview is not merged.
    row = view["state"]["opponent_side"]["pokemon"][view["state"]["opponent_side"]["active_identity"]]
    row["identity_scope"] = "public_apparent_identity_unconfirmed"
    _, records, _ = split(encoder, view)
    assert records[6, 68] == 1 and records[18, 68] == 0


def test_bindings_change_even_when_the_inventory_of_revealed_tokens_is_equal(view):
    encoder = PublicCategoricalEncoder(CATALOG)
    changed = deepcopy(view)
    records = changed["state"]["opponent_side"]["pokemon"]
    template = deepcopy(next(iter(records.values())))
    for key, species, item, move in (("p2: revealed-A", "Scizor", "lifeorb", "rest"),
                                     ("p2: revealed-B", "Alakazam", "leftovers", "imprison")):
        records[key] = {**deepcopy(template), "identity": key, "details": species,
                        "known_item": item, "known_moves": [move]}
    swapped = deepcopy(changed)
    other = swapped["state"]["opponent_side"]["pokemon"]
    for field in ("known_item", "known_moves"):
        other["p2: revealed-A"][field], other["p2: revealed-B"][field] = other["p2: revealed-B"][field], other["p2: revealed-A"][field]
    x, y = encoder.encode(changed), encoder.encode(swapped)
    assert not np.array_equal(x[BASE_CONTEXT:CONTEXT], y[BASE_CONTEXT:CONTEXT])
    m = model(encoder)
    with torch.no_grad():
        xc, _, _ = m.policy.mlp_extractor._public_rows(torch.tensor(x)[None])
        yc, _, _ = m.policy.mlp_extractor._public_rows(torch.tensor(y)[None])
    assert not torch.equal(xc[:, BASE_CONTEXT:], yc[:, BASE_CONTEXT:])


def test_manifest_cannot_claim_categorical_encoder_for_non_categorical_policy(tmp_path):
    encoder = PublicCategoricalEncoder(CATALOG)
    path = save_checkpoint(model(encoder, TacticalActionConditionedPolicy), encoder, tmp_path / "wrong", {})
    with pytest.raises(ValueError, match="public_categorical_policy_required"):
        LearnedPolicy(path, CATALOG)


def test_small_native_learning_save_and_optimizer_reload(tmp_path):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned native engine required")
    from advisor.learned_gym import ShowdownLearningEnv
    from stable_baselines3.common.vec_env import DummyVecEnv
    torch.set_num_threads(1)
    encoder = PublicCategoricalEncoder(CATALOG)
    env = ShowdownLearningEnv(checkout, encoder, curriculum_version="showdown-learning-curriculum-v8",
                              opponents=("max_power",), collect_tactical_metrics=True)
    vector = DummyVecEnv([lambda: env])
    try:
        m = MaskablePPO(PublicCategoricalPolicy, vector, seed=917, n_steps=16, batch_size=16,
                         n_epochs=1, learning_rate=1e-4, device="cpu")
        initial = {k: v.clone() for k, v in m.policy.state_dict().items()}
        m.learn(32)
        assert m.num_timesteps == 32 and m.policy.optimizer.state
        assert any(not torch.equal(initial[k], v) for k, v in m.policy.state_dict().items())
        path = save_checkpoint(m, encoder, tmp_path / "native", {})
        restored = LearnedPolicy(path, CATALOG)
        assert restored.model.num_timesteps == 32 and restored.model.policy.optimizer.state
        before = deepcopy(env.current)
        prediction = restored.infer(env.current)
        assert env.current == before and env.action_masks()[prediction["action_index"]]
        assert prediction["evidence_class"] == "learned_policy_value"
    finally:
        vector.close()


def test_opt_in_strategy_evidence_keeps_exact_ranking_and_runtime_truth(tmp_path):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned native engine required")
    from advisor.showdown_worker import ShowdownWorker
    from llm.advisor_learned_strategy import valid_learned_evidence
    from tests.test_showdown_strategy_evaluation import configuration
    from tests.test_showdown_shadow_ui import run
    encoder = PublicCategoricalEncoder(CATALOG)
    path = save_checkpoint(model(encoder), encoder, tmp_path / "opt_in", {})
    snapshot, builder, context = configuration(horizon=1)
    context["learned_policy"] = {
        "schema_version": "showdown-learned-config-v1", "enabled": True,
        "model_path": path, "catalog_path": str(CATALOG),
        "expected_model_id": json.loads(Path(path).with_suffix(".json").read_text())["model_sha256"],
    }
    before = deepcopy((snapshot, context))
    with ShowdownWorker(checkout) as worker:
        baseline = run(snapshot, builder)
        result = run(snapshot, builder, showdown_context=context, showdown_bridge=worker)
    assert (snapshot, context) == before
    for key in ("orchestration", "exact_outcome_ledgers", "descriptive_metrics",
                "opponent_response_profiles", "execution_coverage"):
        assert result[key] == baseline[key]
    evidence = result["explanation"]["sampled_simulation"]
    for row in evidence["scenarios"]:
        assert row["learned_policy"]["status"] == "evaluated"
        assert valid_learned_evidence(row["learned_policy"], evidence, row)
        assert row["learned_policy"]["inference"]["encoder_version"] == VERSION


def test_new_encoder_factory_spawn_matches_dummy_without_privileged_inputs():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned native engine required")
    from advisor.learned_parallel import LearningEnvFactory
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
    factories = [LearningEnvFactory(checkout, str(CATALOG), VERSION, i * 100000,
                                   "showdown-learning-curriculum-v8", ("max_power",), {}) for i in range(2)]
    outputs = []
    for cls in (DummyVecEnv, SubprocVecEnv):
        vector = cls(factories, **({"start_method": "spawn"} if cls is SubprocVecEnv else {}))
        try:
            vector.seed(937)
            frames = [vector.reset()]
            assert frames[0].shape == (2, PublicCategoricalEncoder.dimension)
            for _ in range(4):
                masks = np.array(vector.env_method("action_masks"))
                actions = [int(np.flatnonzero(mask)[-1]) for mask in masks]
                frames.append(vector.step(actions)[0])
            outputs.append(frames)
        finally:
            vector.close()
    for dummy, spawned in zip(*outputs):
        np.testing.assert_array_equal(dummy, spawned)


def test_native_boolean_mega_request_has_exact_public_candidate_form():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned native engine required")
    from advisor.showdown_environment import ShowdownEnvironment
    from advisor.learned_scenarios import scenario
    encoder = PublicCategoricalEncoder(CATALOG)
    cases = (scenario("train", i) for i in range(100))
    case = next(c for c in cases if c["teams"]["self"][c["preview"]["self"][0] - 1]["item"].endswith("ite X"))
    with ShowdownEnvironment(checkout) as env:
        env.reset(case); view = env.observation("self", include_history=True)
        assert view["own_request"]["active"][0]["canMegaEvo"] is True
        mega = next(i for i in range(10, 14) if view["action_mask"][i])
        _, _, actions = split(encoder, view)
        start = BASE_ACTION - 1 + 5 + 10
        expected = encoder.token("species", "Charizard-Mega-X")
        assert decode(actions[mega, start:start + 11]) == expected
        assert decode(actions[mega - 4, start:start + 11]) == encoder.token("species", "Charizard")
        missing = deepcopy(view)
        own = missing["state"]["self_side"]
        own["pokemon"][own["active_identity"]]["known_item"] = {"knowledge": "unknown"}
        _, _, rows = split(encoder, missing)
        assert decode(rows[mega, start:start + 11]) == UNKNOWN
        rival = env.observation("opponent", include_history=True)
        env.step({"self": mega, "opponent": int(np.flatnonzero(rival["action_mask"])[0])}, revision=view["revision"])
        after = env.observation("self", include_history=True)
        _, records, _ = split(encoder, after)
        own = after["state"]["self_side"]
        index = [k for k, _ in sorted(own["pokemon"].items())].index(own["active_identity"])
        assert decode(records[index, ENTITY_NUMERIC:ENTITY_NUMERIC + 11]) == expected
