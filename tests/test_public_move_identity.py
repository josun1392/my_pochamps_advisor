"""Public identity, equal initialization, masks/permutations and strict reload."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
gym = pytest.importorskip("gymnasium")
pytest.importorskip("sb3_contrib")
from sb3_contrib import MaskablePPO
from advisor.learned_action_policy import TacticalActionConditionedPolicy
from advisor.learned_move_identity import (
    OwnMoveTokenEncoder, CONTROL, TREATMENT, CONTEXT, ACTION, BASE_ACTION,
)
from advisor.learned_move_identity_policy import OwnMoveTokenPolicy, transfer_v3_to_own_move
from advisor.learned_policy import LearnedPolicy
from advisor.learned_tactics_encoder import TacticalObservationEncoder
from advisor.learned_evaluation_bank import EvaluationCaseBank
from scripts.train_showdown_autonomous import save_checkpoint, validate_config

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_mc_domain_v1/catalog.json"


class Spaces(gym.Env):
    def __init__(self, dimension):
        self.action_space = gym.spaces.Discrete(35)
        self.observation_space = gym.spaces.Box(-2, 4, (dimension,), dtype=np.float32)


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


def model(encoder, seed=73, policy=OwnMoveTokenPolicy):
    torch.set_num_threads(1)
    return MaskablePPO(policy, Spaces(encoder.dimension), seed=seed, n_steps=8,
                       batch_size=8, learning_rate=5e-5, device="cpu")


def test_static_alias_and_versioned_control_information():
    c, t = [OwnMoveTokenEncoder(CATALOG, v) for v in (CONTROL, TREATMENT)]
    for a, b in (("rest", "imprison"), ("encore", "disable"), ("taunt", "torment")):
        assert c.static_descriptor(a) == c.static_descriptor(b)
        assert c.tokens[a] == c.tokens[b]
        assert t.tokens[a] != t.tokens[b]
    assert len(set(t.tokens.values())) == len(t.tokens)
    assert "recharge" in t.tokens
    assert c.catalog_fingerprint != t.catalog_fingerprint
    old = TacticalObservationEncoder(CATALOG)
    assert old.version == "showdown-learned-observation-v3" and old.dimension == 7411
    assert old.catalog_fingerprint == c.feature_contract["base_v3_catalog_fingerprint"]


def test_public_only_unknown_absence_and_legal_unknown_move(view):
    c = OwnMoveTokenEncoder(CATALOG, CONTROL)
    assert c._row({"known_item": None}) != c._row({"known_item": {}})
    for root in ("native_state", "seed", "checkpoint", "teams", "queue", "scenario"):
        with pytest.raises(ValueError, match="privileged"):
            c.encode({**view, root: {}})
    changed = deepcopy(view)
    changed["own_request"]["active"][0]["moves"][0]["id"] = "unverifiedmove"
    changed["action_mask"][6] = True
    with pytest.raises(ValueError, match="unknown_public_legal_own_move"):
        c.encode(changed)


def test_matched_transfer_distribution_value_and_fresh_adam(view):
    old = TacticalObservationEncoder(CATALOG)
    source = model(old, policy=TacticalActionConditionedPolicy)
    # Source optimizer is deliberately nonempty. Transfer must not copy moments.
    sum(p.sum() for p in source.policy.parameters()).backward()
    source.policy.optimizer.step()
    assert source.policy.optimizer.state
    targets = []
    mask = np.array(view["action_mask"])[None, :]
    with torch.no_grad():
        x = torch.tensor(old.encode(view))[None, :]
        expected = source.policy.get_distribution(x, action_masks=mask).distribution.probs
        expected_value = source.policy.predict_values(x)
    for version in (CONTROL, TREATMENT):
        encoder = OwnMoveTokenEncoder(CATALOG, version)
        target = model(encoder)
        transfer_v3_to_own_move(target.policy, source.policy)
        assert not target.policy.optimizer.state
        with torch.no_grad():
            x = torch.tensor(encoder.encode(view))[None, :]
            actual = target.policy.get_distribution(x, action_masks=mask).distribution.probs
            value = target.policy.predict_values(x)
        torch.testing.assert_close(actual, expected, atol=1e-7, rtol=1e-6)
        torch.testing.assert_close(value, expected_value, atol=1e-7, rtol=1e-6)
        assert not actual[0, ~mask[0]].any()
        targets.append(target)
    a, b = [m.policy.state_dict() for m in targets]
    assert a.keys() == b.keys()
    assert all(torch.equal(a[k], b[k]) for k in a)
    assert sum(p.numel() for p in targets[0].policy.parameters()) == sum(p.numel() for p in targets[1].policy.parameters())


def test_action_row_permutation_value_invariance_and_embedding_gradient(view):
    encoder = OwnMoveTokenEncoder(CATALOG, TREATMENT)
    m = model(encoder)
    x = torch.tensor(encoder.encode(view))[None, :]
    permutation = torch.randperm(35)
    y = torch.cat((x[:, :CONTEXT], x[:, CONTEXT:].reshape(1, 35, ACTION)[:, permutation].flatten(1)), dim=1)
    with torch.no_grad():
        torch.testing.assert_close(m.policy.mlp_extractor.forward_actor(y), m.policy.mlp_extractor.forward_actor(x)[:, permutation])
        torch.testing.assert_close(m.policy.predict_values(y), m.policy.predict_values(x), atol=1e-7, rtol=1e-6)
    m.policy.mlp_extractor.forward_actor(x).sum().backward()
    assert m.policy.mlp_extractor.move_embedding.weight.grad.abs().sum() > 0
    bad = x.clone()
    bad[0, CONTEXT + BASE_ACTION - 1] = .5
    with pytest.raises(ValueError, match="nonbinary"):
        m.policy.predict_values(bad)


def test_save_reload_and_manifest_arm_mismatch(view, tmp_path):
    encoder = OwnMoveTokenEncoder(CATALOG, TREATMENT)
    m = model(encoder)
    path = save_checkpoint(m, encoder, tmp_path / "new", {})
    restored = LearnedPolicy(path, CATALOG)
    assert restored.infer(view)["action_index"] in range(35)
    metadata = Path(path).with_suffix(".json")
    data = json.loads(metadata.read_text())
    data["feature_contract"]["token_map_sha256"] = "incorrect"
    metadata.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="own_move_feature_contract"):
        LearnedPolicy(path, CATALOG)


def test_evaluation_bank_hash_and_final_access_fail_closed(tmp_path):
    from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
    bank = {"schema_version": "showdown-experimental-evaluation-bank-v1", "scope": "test",
            "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID,
            "native_validated": True, "panels": {"uniform": [[{}] * 6]}}
    path = tmp_path / "bank.json"
    raw = json.dumps(bank).encode(); path.write_bytes(raw)
    digest = sha256(raw).hexdigest()
    with pytest.raises(ValueError, match="contract"):
        EvaluationCaseBank(path, digest, scope="validation")
    with pytest.raises(ValueError, match="hash"):
        EvaluationCaseBank(path, "wrong", scope="test")
    provider = EvaluationCaseBank(path, digest, scope="test")
    assert provider("test", 19) == provider("test", 19)
    with pytest.raises(ValueError, match="partition"):
        provider("train", 19)


def test_transfer_config_requires_verified_fresh_optimizer():
    config = {"schema_version": "showdown-autonomous-training-v1", "max_runtime_seconds": 60,
              "experiments": [{"seed": 62011, "steps": 4096, "encoder_version": CONTROL,
                               "transfer_model": "trusted.zip"}]}
    with pytest.raises(ValueError, match="explicit_fresh_optimizer"):
        validate_config(config)
    config["experiments"][0]["fresh_optimizer"] = True
    validate_config(config)
