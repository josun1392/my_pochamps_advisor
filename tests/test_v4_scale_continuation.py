"""Additive 256-team and fixed-window contracts; no replacement learner."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from advisor.learned_training_subset import (
    NativeTrainingSubset, extend_native_training_subset, VERSION_64, VERSION_256,
)
from tests.test_learnability_ladder import subset
from scripts.train_showdown_snapshot_league import (
    VERSION, FIXED_VERSION, generation_config, validate_chain_plan,
)


def test_256_extends_exact_parent_and_protects_reserved_train_teams(tmp_path):
    parent, digest = subset(tmp_path, 64, schema_version=VERSION_64)
    old_contract=json.loads(parent.read_text());old_contract["excluded_stage1_diagnostic_indices"]=list(range(64,80))
    parent.write_text(json.dumps(old_contract));digest=sha256(parent.read_bytes()).hexdigest()
    before = parent.read_bytes()
    kw = dict(membership_seed=78151, seed_namespace="v4-scale-test", excluded_train_indices=range(64,96))
    c = extend_native_training_subset(parent, digest, **kw)
    assert c == extend_native_training_subset(parent, digest, **kw)
    assert c["schema_version"] == VERSION_256 and len(c["team_indices"]) == 256
    assert c["team_indices"][:64] == list(range(64))
    assert not set(c["team_indices"]) & set(range(64,96))
    out = tmp_path / "256.json"; out.write_text(json.dumps(c))
    p = NativeTrainingSubset(out, sha256(out.read_bytes()).hexdigest())
    assert p("train", 77151) == p("train", 77151)
    with pytest.raises(ValueError): p("test", 77151)
    for change in ({"parent_team_indices":list(range(1,65))},
                   {"excluded_train_indices":[0]}, {"parent_subset_sha256":"wrong"},
                   {"parent_split":"validation"}):
        out.write_text(json.dumps({**c,**change}))
        with pytest.raises(ValueError):NativeTrainingSubset(out,sha256(out.read_bytes()).hexdigest())
    assert parent.read_bytes() == before
    with pytest.raises(ValueError):extend_native_training_subset(parent,digest,**{**kw,"excluded_train_indices":[0]})
    inherited=extend_native_training_subset(parent,digest,membership_seed=3,seed_namespace="inherit")
    assert not set(inherited["team_indices"]) & set(range(64,80))


def test_durable_endpoint_without_completed_validation_entry(tmp_path):
    from scripts.train_showdown_snapshot_league import fixed_budget_endpoint
    directory=tmp_path/"experiment_00/checkpoint_0002_ppo_2048_fixed";directory.mkdir(parents=True)
    path=directory/"model.zip";path.write_bytes(b"trusted_test_fixture_not_loaded_as_pickle")
    metadata={"stage":"ppo","total_steps":2048,"optimizer_steps":64,"model_sha256":sha256(path.read_bytes()).hexdigest(),
        "training_config_fingerprint":"config-id","encoder_version":"showdown-public-categorical-observation-v4",
        "catalog_fingerprint":"catalog","training_objective":{},"training_regularizer":{}}
    path.with_suffix(".json").write_text(json.dumps(metadata))
    result={"transitions":2048,"evaluations":[]}
    assert fixed_budget_endpoint(tmp_path,{"model_timesteps":0},result,"config-id")["model_timesteps"]==2048
    with pytest.raises(ValueError):fixed_budget_endpoint(tmp_path,{"model_timesteps":0},result,"different-config")


def test_fixed_window_bounds_do_not_expand_v0_league():
    p={"schema_version":FIXED_VERSION,"generations":2,"generation_transitions":1048576,
       "continuation_seeds":{"s1":78151},"beta":.001}
    validate_chain_plan(p,"F-s1")
    for change in ({"generations":3},{"generation_transitions":2097152},
                   {"schema_version":VERSION},{"generation_transitions":True}):
        with pytest.raises(ValueError):validate_chain_plan({**p,**change},"F-s1")
    with pytest.raises(ValueError):validate_chain_plan(p,"L-s1")
    legacy={**p,"schema_version":VERSION,"generation_transitions":262144,"generations":4,
            "continuation_seeds":{"s1":76011,"s2":76012}}
    for chain in ("F-s1","F-s2","L-s1","L-s2"):validate_chain_plan(legacy,chain)


def test_fixed_window_chains_from_actual_previous_parent_without_transfer():
    from scripts.train_showdown_autonomous import validate_config
    p={"schema_version":FIXED_VERSION,"generations":2,"generation_transitions":1048576,
       "continuation_seeds":{"s1":78151},"beta":.001,
       "fixed_opponents":["max_power","champions_heuristic","tactical_heuristic","previous","historical"],
       "base_config":{"schema_version":"showdown-autonomous-training-v1","max_runtime_seconds":3600,
           "envs":8,"memory_mib":12288,"checkpoint_steps":65536,"previous_model":"previous.zip",
           "experiments":[{"encoder_version":"showdown-public-categorical-observation-v4",
               "gamma":1.,"gae_lambda":.95,"historical_model":"history.zip"}]}}
    parent={"path":"v4-window0-endpoint.zip","sha256":"a"*64}
    c=generation_config(p,"F-s1",1,parent,[parent])
    validate_config(c)
    e=c["experiments"][0]
    assert e["initial_model"]==parent["path"] and e["initial_model_id"]==parent["sha256"]
    assert e["fresh_optimizer"] is False and "transfer_model" not in e
    assert e["zero_avoiding_beta"]==.001 and e["seed"]==79151
    assert c["transition_budget_scope"]=="trained_rollouts_v1"
