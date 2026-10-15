"""Native conditional execution, public consistency and no invented labels."""
from copy import deepcopy
import os
import pytest
import numpy as np
from advisor.learned_action_signals import (public_decision, public_identity,
    require_public_equivalence, candidate_actions, branch_candidate, public_position)
from advisor.learned_baselines import VisibleBaseline
from advisor.showdown_environment import ShowdownEnvironment
from scripts.verify_showdown_integration import fixture_scenarios


@pytest.fixture
def env():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("pinned native engine required")
    with ShowdownEnvironment(checkout) as e:
        e.reset(fixture_scenarios()[0]); yield e


def test_only_transport_is_ignored_and_unknown_is_preserved(env):
    v = env.observation("self", include_history=True)
    other = deepcopy(v); other.update(episode_id="new", revision=999, events=[])
    require_public_equivalence(v, other)
    assert public_identity(v) == public_identity(other)
    for field in ("choices", "action_mask", "own_request", "public_history", "state"):
        changed = deepcopy(v); changed[field] = None
        with pytest.raises(ValueError, match="contradicts"): require_public_equivalence(v, changed)
    for field in ("native_state", "future_seed", "hypothesis", "opponent_request"):
        assert field not in public_decision(v)
    assert public_position(v)["opponent_active_visible_hp_fraction"] == 1.


def test_hypotheses_need_full_public_consistency_and_encoder_equivalence(env):
    from advisor.learned_strategic_public import StrategicPublicCategoricalEncoder
    from pathlib import Path
    encoder = StrategicPublicCategoricalEncoder(Path("models/showdown_mc_domain_v1/catalog.json"))
    baseline = env.observation("self", include_history=True)
    changed = fixture_scenarios()[0]
    changed["teams"]["opponent"][0].update(item="Choice Scarf", moves=["U-turn", "Iron Head", "Protect"])
    env.reset(changed)
    hypothesis = env.observation("self", include_history=True)
    require_public_equivalence(baseline, hypothesis)
    np.testing.assert_array_equal(encoder.encode(baseline), encoder.encode(hypothesis))
    assert hypothesis["state"]["opponent_side"]["pokemon"]["p2a: slot-0"]["known_item"] == {"knowledge":"unknown"}


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_future_rng_branch_preserves_public_root_and_original_checkpoint(env, side):
    v = env.observation(side, include_history=True); cp = env.save(); untouched = deepcopy(cp)
    env.restart(cp, future_seed=[13, 19, 23, 29])
    require_public_equivalence(v, env.observation(side, include_history=True))
    reseeded = env.save()
    assert reseeded["provenance"]["counterfactual_future_seed"] == [13,19,23,29]
    for key in cp["native_state"]:
        if key != "prng": assert cp["native_state"][key] == reseeded["native_state"][key]
    env.restart(cp)
    assert env.save() == cp == untouched
    for seed in ([True, 2, 3, 4], [1,2,3], [65536,0,0,0]):
        with pytest.raises(ValueError, match="future_seed"): env.restart(cp, future_seed=seed)
    assert env.save() == cp


def test_executed_candidate_reproducible_public_policies_and_masks(env):
    class Guard:
        def __init__(self): self.actor = VisibleBaseline("max_power", 9); self.count = 0
        def act(self, v):
            assert all(k not in v for k in ("native_state", "future_seed", "hypotheses", "opponent_request", "teams"))
            assert "own_request" in v and "public_history" in v
            self.count += 1
            return self.actor.act(v)
    cp = env.save(); v = env.observation("self", include_history=True)
    actions = candidate_actions(v)
    assert set(actions) <= {i for i, m in enumerate(v["action_mask"]) if m}
    def run():
        return branch_candidate(env, cp, v, side="self", action=6, future_seed=[11,22,33,44],
                                own_policy=Guard(), opponent_policy=Guard())
    a, b = run(), run()
    assert a == b and a["terminated"] and not a["truncated"]
    assert a["terminal_return"] in (-1,0,1)
    assert a["immediate"]["own_native_choice"] == v["choices"][6]
    assert a["trace"][0]["own_action_mask"][6]
    assert any("|move|p1a: slot-0|Flamethrower|" in line for line in a["immediate"]["events"])
    with pytest.raises(ValueError, match="masked"): branch_candidate(env, cp, v, side="self", action=25,
        future_seed=[1,2,3,4], own_policy=Guard(), opponent_policy=Guard())


def test_timeout_is_missing_terminal_label_not_zero(env):
    cp = env.save()
    # A separate actual supported native episode limit, no checkpoint mutation.
    e = ShowdownEnvironment(worker=env.worker, max_decisions=1)
    try:
        e.reset(fixture_scenarios()[0]); v=e.observation("self",include_history=True)
        row=branch_candidate(e,e.save(),v,side="self",action=8,future_seed=[1,2,3,4],
            own_policy=VisibleBaseline("max_power"),opponent_policy=VisibleBaseline("max_power"))
        assert row["truncated"] and not row["terminated"] and row["terminal_return"] is None
    finally: e.close()
    assert env.save() == cp


def test_future_samples_vary_damage_without_changing_decision(env):
    cp=env.save();view=env.observation("self",include_history=True);health=[]
    for n in range(12):
        env.restart(cp,future_seed=[81,83,89,n])
        require_public_equivalence(view,env.observation("self",include_history=True))
        env.step({"self":7,"opponent":6},revision=0)
        health.append(public_position(env.observation("self",include_history=True))["opponent_active_visible_hp_fraction"])
    assert len(set(health))>1


def test_publicly_legal_hidden_trap_rejection_has_no_action_label(env):
    scenario=fixture_scenarios()[0]
    scenario["teams"]["self"][0]=deepcopy(scenario["teams"]["opponent"][0])
    scenario["teams"]["opponent"][0]={"species":"Gengar","ability":"Cursed Body","item":"Gengarite",
        "level":50,"moves":["Shadow Ball","Protect"],"nature":"Timid","evs":{"spa":32,"spe":32,"hp":2}}
    scenario["teams"]["opponent"][5]=deepcopy(fixture_scenarios()[0]["teams"]["opponent"][0])
    env.reset(scenario);env.step({"self":8,"opponent":11},revision=0)
    view=env.observation("self",include_history=True)
    assert view["action_mask"][1] and view["own_request"]["active"][0]["maybeTrapped"]
    row=branch_candidate(env,env.save(),view,side="self",action=1,future_seed=[1,3,5,7],
        own_policy=VisibleBaseline("max_power"),opponent_policy=VisibleBaseline("max_power"))
    assert row["status"]=="initial_candidate_rejected_no_label"
    assert row["terminal_return"] is None and row["native_rejections"]==1
    assert not any(env.observation("self")["action_mask"][:6])


def test_frozen_source_mismatch_fails_before_model_or_native_access(tmp_path):
    from scripts.evaluate_showdown_action_signals import evaluate
    from advisor.learned_action_signals import SCHEMA
    plan={"schema_version":SCHEMA,"states":[{}],"future_seeds":[[1,2,3,n] for n in range(4)],
          "rivals":["max_power"],"source_hashes":{"advisor/learned_action_signals.py":"bad"}}
    with pytest.raises(ValueError,match="source_identity"):evaluate(plan,tmp_path)


@pytest.mark.parametrize("side", ["self", "opponent"])
def test_terminal_label_uses_actual_native_candidate_seat(env, side):
    v=env.observation(side,include_history=True)
    row=branch_candidate(env,env.save(),v,side=side,action=6,future_seed=[19,31,43,59],
        own_policy=VisibleBaseline("max_power"),opponent_policy=VisibleBaseline("max_power"))
    assert row["terminated"] and not row["truncated"]
    assert row["terminal_return"] == (1 if row["winner"]==side else -1 if row["winner"] else 0)
