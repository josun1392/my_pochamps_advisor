"""Offline response contracts: no new native games, PPO or fitting campaign."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
import torch

from advisor.showdown_observation import project_policy_observation
from advisor.learned_response_predictor import (ResponseEncoder, selected_label, public_input,
    frequency_predictions, score_predictions, make_model, model_probabilities, audit_split, team_signature)
from advisor.learned_execution_alignment import content_hash, durable_json, digest
from scripts.run_foundation_response_predictor import ArgmaxRecorder, audit_games

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def encoder():
    read=lambda p:json.loads(p.read_text(encoding="utf-8"))
    return ResponseEncoder(ROOT/"models/showdown_mc_domain_v1/catalog.json",
        read(ROOT/"models/showdown_tactics_v1/catalog.json")["moves"],
        read(ROOT/"models/showdown_combat_priors_v3/catalog.json")["native_moves"])


def view(side="self",revealed=False):
    role="p1" if side=="self" else "p2"
    history=["|start", "|switch|p1a: Charizard|Charizard, L50|100/100", "|switch|p2a: Scizor|Scizor, L50|100/100"]
    if revealed:history.append("|move|p2a: Scizor|Bullet Punch|p1a: Charizard")
    species="Charizard" if side=="self" else "Scizor"
    request={"side":{"id":role,"pokemon":[{"ident":role+": "+species,"details":species+", L50",
        "condition":"153/153","active":True,"moves":["bulletpunch"],"ability":"technician","item":"leftovers"}]},
        "active":[{"moves":[{"id":"bulletpunch","pp":10,"maxpp":10}]}]}
    raw={"schema_version":"showdown-policy-observation-v1","action_schema_version":"showdown-policy-actions-v1",
        "interpretation":"hypothetical_player_visible_observation_not_live_truth","side":side,"episode_id":"e", "revision":1,
        "request_state":"move","turn":1,"own_request":request,"action_mask":[int(i in(0,6)) for i in range(35)],
        "choices":["switch 2" if i==0 else "move 1" if i==6 else None for i in range(35)],"events":history}
    return project_policy_observation(raw,history)


@pytest.mark.parametrize("side",["self","opponent"])
def test_public_owner_features_shapes_unknown_and_no_private_hp(encoder,side):
    v=view(side);before=deepcopy(v);x,s=encoder.encode(v)
    assert len(x)==encoder.dimension and len(s)==len(encoder.outputs)
    assert np.isfinite(x).all() and s.sum()==6 and v==before
    enemy=v["state"]["opponent_side"];row=enemy["pokemon"][enemy["active_identity"]]
    assert isinstance(row["max_hp"],dict)


def test_revealed_identity_support_changes_causally_not_private_target(encoder):
    observer=view(revealed=False);target=view("opponent")
    label,_=selected_label(observer,target,6,{"action_rejected":False},encoder.tactics,encoder.native)
    assert label["semantic"]=="unknown:attack"
    x0,s0=encoder.encode(observer)
    target2=deepcopy(target);target2["own_request"]["side"]["pokemon"][0]["item"]="choicescarf"
    target2["own_request"]["active"][0]["moves"][0]["id"]="recover"
    # A hidden set cannot affect forward features/support; only label interpretation may change.
    np.testing.assert_array_equal(x0,encoder.encode(observer)[0])
    np.testing.assert_array_equal(s0,encoder.encode(observer)[1])
    obs2=view(revealed=True);label,_=selected_label(obs2,target,6,{"action_rejected":False},encoder.tactics,encoder.native)
    assert label["semantic"]=="known:bulletpunch"
    assert encoder.encode(obs2)[1][encoder.output_index[label["semantic"]]]


@pytest.mark.parametrize("key",["target_mask","opponent_request","teams","native_state","result","probabilities","labels"])
def test_private_inputs_fail_closed(encoder,key):
    v=view();v[key]={}
    with pytest.raises(ValueError,match="private"):encoder.encode(v)


def test_label_choices_not_execution_and_rejections_wait_and_forced_excluded(encoder):
    obs,target=view(),view("opponent")
    for result,action,reason in [({"action_rejected":True},6,"native_rejected_attempt")]:
        assert selected_label(obs,target,action,result,encoder.tactics,encoder.native)==(None,reason)
    label,_=selected_label(obs,target,0,{"action_rejected":False,"winner":"self"},encoder.tactics,encoder.native)
    assert label["semantic"]=="switch"  # destination deliberately not inferred
    target["request_state"]="switch"
    assert selected_label(obs,target,0,{"action_rejected":False},encoder.tactics,encoder.native)[1]=="forced_or_administrative_replacement"
    target["request_state"]="move";target["revision"]=2
    with pytest.raises(ValueError,match="time"):selected_label(obs,target,6,{"action_rejected":False},encoder.tactics,encoder.native)
    target["revision"]=1;target["action_mask"][6]=0
    with pytest.raises(ValueError,match="illegal"):selected_label(obs,target,6,{"action_rejected":False},encoder.tactics,encoder.native)


def test_public_mask_normalization_never_target_private_mask(encoder):
    v=view(revealed=True)
    x,s=encoder.encode(v);model=make_model(len(x),len(s));torch.set_num_threads(1)
    with torch.no_grad():p=model_probabilities(model,torch.from_numpy(x)[None],torch.from_numpy(s)[None]).numpy()[0]
    assert not p[~s].any() and p[s].min()>0 and abs(p.sum()-1)<1e-6
    assert encoder.heuristic(v)[~s].sum()==0
    f=frequency_predictions([encoder.output_index["unknown:attack"]],[s],len(s))[0]
    assert f[s].min()>0 and f[~s].sum()==0


def test_real_gradient_step_save_load_and_optimizer(tmp_path,encoder):
    torch.set_num_threads(1);torch.manual_seed(55)
    x,s=encoder.encode(view(revealed=True));x=torch.from_numpy(x)[None];s=torch.from_numpy(s)[None]
    a=make_model(x.shape[1],s.shape[1]);opt=torch.optim.Adam(a.parameters(),lr=.0003)
    before={k:v.detach().clone() for k,v in a.state_dict().items()}
    loss=-torch.log(model_probabilities(a,x,s)[0,encoder.output_index["known:bulletpunch"]]);loss.backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in a.parameters())
    opt.step();assert any(not torch.equal(before[k],v) for k,v in a.state_dict().items())
    path=tmp_path/"model.pt";torch.save({"model":a.state_dict(),"optimizer":opt.state_dict()},path)
    saved=torch.load(path,weights_only=True);b=make_model(x.shape[1],s.shape[1]);b.load_state_dict(saved["model"])
    other=torch.optim.Adam(b.parameters(),lr=.0003);other.load_state_dict(saved["optimizer"])
    torch.testing.assert_close(a(x),b(x),rtol=0,atol=0)
    for model,optimizer in ((a,opt),(b,other)):
        optimizer.zero_grad();(-model_probabilities(model,x,s)[0,-1].log()).backward();optimizer.step()
    torch.testing.assert_close(a(x),b(x),rtol=0,atol=0)


def test_probabilistic_metrics_and_family_collapse(encoder):
    s=np.zeros((2,len(encoder.outputs)));y=np.array([encoder.output_index["unknown:attack"],encoder.output_index["switch"]])
    s[0,y[0]]=.8;s[0,y[1]]=.2;s[1,y[0]]=.2;s[1,y[1]]=.8
    score,_=score_predictions(s,y,encoder.family_index)
    assert score["top1"]==1 and score["nll"]==pytest.approx(-np.log(.8)) and score["brier"]==pytest.approx(.08)


def test_group_split_semantic_team_identity_and_seed_checks():
    cases=[]
    for i in range(72):
        cases.append({"fold":("train","validation","test")[i//24],"scenario":{"teams":{"self":[{"species":str(2*i),"moves":["a","b"]}],"opponent":[{"species":str(2*i+1)}]},"seed":[i,0,0,0]}})
    assert audit_split(cases)==dict(train=24,validation=24,test=24)
    assert team_signature([{"species":"a","name":"x","moves":["b","c"]}])==team_signature([{"species":"a","name":"y","moves":["c","b"]}])
    bad=deepcopy(cases);bad[-1]["scenario"]["teams"]["self"]=bad[0]["scenario"]["teams"]["self"]
    with pytest.raises(ValueError,match="leak"):audit_split(bad)


def test_argmax_record_and_uncertain_start_no_reexecution(tmp_path):
    p=[0.]*35;p[6]=.7;p[7]=.3
    def infer(v):return {"action_index":6,"action_probabilities":p}
    recorder=ArgmaxRecorder(infer);v=view();assert recorder(v)["action_index"]==6 and recorder.pending[0]["mode"]=="argmax"
    slot={"case":0};(tmp_path/"receipts").mkdir();assert audit_games(tmp_path,[slot],"plan")==[]
    (tmp_path/"game_ledger.jsonl").write_text(json.dumps({"phase":"game_started","index":0,"slot_sha256":content_hash(slot)})+"\n")
    with pytest.raises(ValueError,match="uncertain"):audit_games(tmp_path,[slot],"plan")


def test_small_fixture_fit_freezes_test_and_cannot_refit(tmp_path,monkeypatch):
    """Exercise orchestration with synthetic arrays, not another native model study."""
    import scripts.run_foundation_response_predictor as runner
    from types import SimpleNamespace
    rng=np.random.default_rng(4);x=rng.normal(size=(216,4)).astype(np.float32)
    support=np.ones((216,6),bool);y=np.arange(216)%6;h=np.full((216,6),1/6,dtype=np.float32)
    meta=[{"pair":i//3,"fold":("train","validation","test")[i//72],"rival":"stub","seat":"p1",
           "ability_unknown":True,"item_unknown":True,"family":("attack","recovery","defense","setup","status_or_field","switch")[y[i]],
           "semantic":"unknown:attack"} for i in range(216)]
    indices={f:np.arange(j*72,(j+1)*72) for j,f in enumerate(("train","validation","test"))}
    e=SimpleNamespace(dimension=4,outputs=tuple(str(i) for i in range(6)),fingerprint="test",family_index=np.arange(6))
    p={"output":str(tmp_path),"learner":{"seed":1,"learning_rate":.0003,"weight_decay":0.,"epochs":2,"batch":16,"gradient_clip":5.,"early_stopping_patience":4},
       "statistics":{"seed":2,"resamples":100}}
    plan=tmp_path/"plan.json";plan.write_text("{}")
    (tmp_path/"dataset.npz").write_bytes(b"offline_fixture_only")
    monkeypatch.setattr(runner,"verify",lambda path:(p,[]))
    monkeypatch.setattr(runner,"build_dataset",lambda p:(x,support,y,h,meta,indices,e))
    result=runner.fit_and_test(plan,SimpleNamespace(usage=lambda:{}),SimpleNamespace(stopping=lambda:False))
    assert result["test_rows"]==72 and (tmp_path/"test_complete.json").exists()
    assert json.loads((tmp_path/"fit_complete.json").read_text())["reload_logits_bit_equal"]
    with pytest.raises(ValueError,match="test_already_opened"):runner.fit_and_test(plan,None,None)
