"""Preserved native inputs, NO new battles. One explicitly metered fixture update.

The synthetic target below tests the consumer's mathematical connection only.
It is not a public teacher output, real training label or learnability result.
"""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch

from advisor.learning_resources import atomic_json
from tests.test_integrated_micro_contract import fixture_target


def test_preserved_native_foundation_consumer_one_metered_clone_update():
    contract_path = os.environ.get("POKEADVICE_MICRO_WIRING_CONTRACT")
    if not contract_path:
        pytest.skip("explicit verified clone-only contract required; never start native")
    from advisor.learned_policy import LearnedPolicy
    from scripts.pilot_foundation_integrated_micro import MicroLedger
    from scripts.train_showdown_autonomous import apply_public_teacher_decision, optimizer_steps
    cfg = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    output = Path(cfg["output"])
    if output.exists(): pytest.fail("fixture update already executed; do not duplicate")
    path = Path(cfg["model"])
    original_hash = sha256(path.read_bytes()).hexdigest()
    assert original_hash == cfg["model_SHA256"]
    learner = LearnedPolicy(path, cfg["catalog"], expected_model_id=original_hash)
    model, encoder = learner.model, learner.encoder
    lines = Path(cfg["public_decisions"]).read_bytes()
    assert sha256(lines).hexdigest() == cfg["public_decisions_SHA256"]
    v = next(json.loads(line)["public_before"] for line in lines.decode("utf-8").splitlines()
        if sum(json.loads(line)["public_before"]["action_mask"]) >= 2)
    features = torch.as_tensor(encoder.encode(v)[None])
    mask = np.asarray(v["action_mask"], bool)[None]
    with torch.no_grad():
        dist = model.policy.get_distribution(features, action_masks=mask).distribution
        before_prob = dist.probs.clone(); before_logits = dist.logits.clone()
        before_value = model.policy.predict_values(features).clone()
    # Deliberately non-oracle fixture: choose the least-probable legal action.
    action = min(np.flatnonzero(mask[0]), key=lambda a: float(before_prob[0, a]))
    def assess(view, **kw):
        d = fixture_target(view, **kw)
        d["target"] = [float(a == action) for a in range(35)]
        return d
    provider = SimpleNamespace(assess=assess)
    saved = {k: p.clone() for k, p in model.policy.state_dict().items()}
    adam_before = deepcopy(model.policy.optimizer.state_dict())
    clock = optimizer_steps(model)
    ledger = MicroLedger(cfg["ledger"])
    # Native actor/critic outputs are unchanged by opt-out.
    off = apply_public_teacher_decision(model, encoder, v, provider, policy_id=original_hash,
        learning_step=model.num_timesteps, enabled=False, ledger=ledger)
    assert off["optimizer_updates"] == 0 and optimizer_steps(model) == clock
    assert all(torch.equal(saved[k], p) for k, p in model.policy.state_dict().items())
    result = apply_public_teacher_decision(model, encoder, v, provider, policy_id=original_hash,
        learning_step=model.num_timesteps, enabled=True, ledger=ledger)
    gradients = {n: float(p.grad.norm()) for n, p in model.policy.named_parameters() if p.grad is not None}
    assert result["optimizer_updates"] == 1 and optimizer_steps(model) == clock+1
    assert any(gradients.values()) and any(not torch.equal(saved[k], p) for k, p in model.policy.state_dict().items())
    assert all(torch.isfinite(p).all() for p in model.policy.parameters())
    with torch.no_grad():
        after_dist = model.policy.get_distribution(features, action_masks=mask).distribution
        after_prob = after_dist.probs.clone()
        after_logits = after_dist.logits.clone()
        after_value = model.policy.predict_values(features).clone()
    assert not torch.equal(before_prob, after_prob)
    assert not after_prob[~torch.as_tensor(mask)].any()
    assert sha256(path.read_bytes()).hexdigest() == original_hash
    # No save, original checkpoint and Adam are never written. Discard clone.
    atomic_json(output, {**result, "scope": "synthetic_contract_fixture_not_teacher_quality",
        "model_SHA256": original_hash, "Adam_before": clock, "Adam_after": optimizer_steps(model),
        "restored_Adam_entries": len(adam_before["state"]), "target_fixture_action": int(action),
        "probability_max_abs_delta": float((after_prob-before_prob).abs().max()),
        "logits_max_abs_delta": float((after_logits-before_logits).abs().max()),
        "value_max_abs_delta": float((after_value-before_value).abs().max()),
        "fixture_probability_before": float(before_prob[0,action]),
        "fixture_probability_after": float(after_prob[0,action]),
        "gradient_norms": gradients, "new_native_starts": 0, "new_transitions": 0,
        "new_Adam": 1, "model_saved": False})
