"""Offline fixtures only: zero native starts and zero PPO transitions."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
import torch
from test_response_predictor import view
from advisor.learned_response_predictor import ResponseEncoder
from advisor.learned_hierarchical_response import MetadataEncoder,HierarchicalResponseModel
from scripts.run_foundation_hierarchical_response import verify_partition

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def encoder():
    read=lambda p:json.loads(p.read_text(encoding="utf-8"))
    return MetadataEncoder(ResponseEncoder(ROOT/"models/showdown_mc_domain_v1/catalog.json",
        read(ROOT/"models/showdown_tactics_v1/catalog.json")["moves"],read(ROOT/"models/showdown_combat_priors_v3/catalog.json")["native_moves"]))


@pytest.mark.parametrize("side",["self","opponent"])
def test_public_candidates_shapes_identity_and_no_private_mask(encoder,side):
    v=view(side);before=deepcopy(v);x,s=encoder.encode(v)
    assert x.shape==(encoder.dimension,) and s.shape==(944,) and s.sum()==6
    assert v==before and encoder.metadata.shape[0]==944 and not encoder.identity["private_mask_in_forward_or_normalization"]
    base,s=encoder.public.encode(v);wrong=s.copy();wrong[0]=True
    with pytest.raises(ValueError,match="not_public_revelations"):encoder.context(base,wrong)
    with pytest.raises(ValueError,match="shape"):encoder.context(base,np.ones(35,bool))


@pytest.mark.parametrize("key",["target_mask","opponent_request","teams","native_state","result","probabilities"])
def test_private_data_fail_closed(encoder,key):
    v=view();v[key]={}
    with pytest.raises(ValueError,match="private"):encoder.encode(v)


def test_hierarchy_family_mass_shared_metadata_and_gradients(encoder):
    torch.set_num_threads(1);torch.manual_seed(24);x,s=encoder.encode(view(revealed=True));x=torch.from_numpy(x[None]);s=torch.from_numpy(s[None])
    model=HierarchicalResponseModel(encoder);optimizer=torch.optim.Adam(model.parameters(),lr=.0003)
    lp=model(x,s);p=lp.exp();assert torch.isfinite(lp[s]).all() and p[~s].sum()==0
    torch.testing.assert_close(p.sum(1),torch.ones(1),rtol=1e-6,atol=1e-7)
    gate=torch.softmax(model.family_head(model.context_net(x)),-1)
    actual=torch.stack([p[:,model.family_index==i].sum(1)for i in range(6)],1)
    torch.testing.assert_close(actual,gate,rtol=1e-6,atol=1e-7)
    y=encoder.public.output_index["known:bulletpunch"];(-lp[0,y]).backward()
    for owner in(model.context_net,model.family_head,model.candidate_net):
        assert any(v.grad is not None and v.grad.abs().sum()>0 for v in owner.parameters())
        assert all(v.grad is None or torch.isfinite(v.grad).all() for v in owner.parameters())
    assert not model.metadata.requires_grad and model.metadata.grad is None
    optimizer.step()
    assert all(v.shape[0]not in(938,944)for v in model.parameters())
    # Equal metadata receive equal scores even when their identity bindings differ.
    unknown=encoder.public.output_index["unknown:attack"]
    with torch.no_grad():
        model.metadata[unknown].copy_(model.metadata[y]);lp=model(x,s)
    torch.testing.assert_close(lp[0,y],lp[0,unknown],rtol=0,atol=1e-7)


def test_candidate_permutation_padding_index_zero_and_temperature(encoder):
    torch.set_num_threads(1);model=HierarchicalResponseModel(encoder)
    x=torch.zeros((2,encoder.dimension));s=torch.zeros((2,944),dtype=torch.bool);s[:,-6:]=True;s[0,0]=True;s[1,1:3]=True
    p=model.probabilities(x,s,1.)
    assert p[0,0]>0 and p[1,0]==0 and not p[~s].any()
    ids=torch.nonzero(s[0]).flatten()[None];valid=torch.ones_like(ids,dtype=torch.bool);perm=torch.arange(ids.shape[1]-1,-1,-1)
    lp=model.packed_log_probabilities(x[:1],ids,valid);reordered=model.packed_log_probabilities(x[:1],ids[:,perm],valid[:,perm])
    torch.testing.assert_close(lp,reordered[:,perm],rtol=1e-6,atol=1e-7)
    scalar=torch.tensor(1.,requires_grad=True);cached=model(x,s).detach().masked_fill(~s,0.)
    safe=torch.log_softmax((cached/scalar).masked_fill(~s,-1e9),-1);(-safe[0,0]).backward();assert torch.isfinite(scalar.grad)
    with pytest.raises(ValueError,match="bounds"):model.probabilities(x,s,0.)


def test_hidden_envelope_noninterference_both_seats_and_checkpoint(encoder,tmp_path):
    torch.set_num_threads(1);model=HierarchicalResponseModel(encoder)
    for side in("self","opponent"):
        envelope={"observer":view(side),"target_private":{"moves":["secret"],"mask":[0]*35},"future":"winner"}
        changed=deepcopy(envelope);changed["target_private"]={"item":"private","mask":[1]*35};changed["future"]="other"
        a,mask=encoder.encode(envelope["observer"]);b,other=encoder.encode(changed["observer"])
        np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(mask,other)
        with torch.no_grad():
            p=model.probabilities(torch.from_numpy(a[None]),torch.from_numpy(mask[None]));q=model.probabilities(torch.from_numpy(b[None]),torch.from_numpy(other[None]))
        torch.testing.assert_close(p,q,rtol=0,atol=0)
    path=tmp_path/"model.pt";optimizer=torch.optim.Adam(model.parameters(),lr=.0003)
    loss=-model(torch.from_numpy(a[None]),torch.from_numpy(mask[None]))[0,-1];loss.backward();optimizer.step()
    torch.save({"model":model.state_dict(),"optimizer":optimizer.state_dict(),"encoder_fingerprint":encoder.fingerprint},path)
    state=torch.load(path,weights_only=True);clone=HierarchicalResponseModel(encoder);clone.load_state_dict(state["model"])
    opt=torch.optim.Adam(clone.parameters(),lr=.0003);opt.load_state_dict(state["optimizer"])
    torch.testing.assert_close(model(torch.from_numpy(a[None]),torch.from_numpy(mask[None])),clone(torch.from_numpy(a[None]),torch.from_numpy(mask[None])),rtol=0,atol=0)


def test_disjoint_train_source_test_pairs_and_duplicate_guard():
    old=[[{"species":"old","moves":["a"]}]];cases=[]
    for pair in range(64):
        for repeat in range(8):
            i=pair*8+repeat;cases.append({"index":i,"pair":pair,"fold":"test","scenario":{"seed":[i,0,0,0],"teams":{s:[{"species":str(pair*2+j),"moves":["a"]}]for j,s in enumerate(("self","opponent"))}}})
    assert verify_partition(cases,old)["team_pairs"]==64
    wrong=deepcopy(cases);wrong[0]["scenario"]["teams"]["self"]=old[0]
    with pytest.raises(ValueError,match="leak"):verify_partition(wrong,old)
    wrong=deepcopy(cases);wrong[-1]["scenario"]["seed"]=wrong[0]["scenario"]["seed"]
    with pytest.raises(ValueError,match="seed"):verify_partition(wrong,old)


def test_saved_frozen_baseline_hierarchy_single_test_orchestration(encoder,tmp_path,monkeypatch):
    """Tiny synthetic arrays exercise serialization/metrics, no corpus fitting."""
    import scripts.run_foundation_hierarchical_response as runner
    from advisor.learned_response_predictor import make_model
    from advisor.learned_execution_alignment import digest
    from types import SimpleNamespace
    torch.set_num_threads(1);raw=[];masks=[];labels=[];meta=[];heuristic=[]
    for i in range(8):
        v=view(revealed=bool(i%2));x,s=encoder.public.encode(v);raw.append(x);masks.append(s);heuristic.append(encoder.public.heuristic(v))
        labels.append(encoder.public.output_index["known:bulletpunch"if i%2 else"unknown:attack"])
        meta.append({"pair":i//4,"rival":"fixture","seat":"p1"if i%2 else"p2","public_known_move_count":i%2,
            "ability_unknown":True,"item_unknown":True,"semantic":"known:bulletpunch"if i%2 else"unknown:attack"})
    X=np.asarray(raw);S=np.asarray(masks);Y=np.asarray(labels);H=np.asarray(heuristic)
    model=HierarchicalResponseModel(encoder);path=tmp_path/"hierarchical_best.pt"
    torch.save({"model":model.state_dict(),"mean":np.zeros(encoder.dimension,np.float32),"scale":np.ones(encoder.dimension,np.float32)},path)
    (tmp_path/"model.json").write_text(json.dumps({"model_sha256":digest(path),"temperature":1.}))
    (tmp_path/"fit_complete.json").write_text(json.dumps({"frozen_model_json_sha256":digest(tmp_path/"model.json")}))
    flat=make_model(encoder.public.dimension,944);fp=tmp_path/"flat.pt"
    torch.save({"model":flat.state_dict(),"mean":np.zeros(encoder.public.dimension,np.float32),"scale":np.ones(encoder.public.dimension,np.float32)},fp)
    (tmp_path/"flat.json").write_text(json.dumps({"temperature":1.}))
    np.savez_compressed(tmp_path/"development.npz",X=X[:2],S=S[:2],Y=Y[:2])
    (tmp_path/"development_rows.json").write_text(json.dumps([{"fold":"train"},{"fold":"validation"}]))
    (tmp_path/"dataset.npz").write_bytes(b"fixture_not_native_data")
    p={"output":str(tmp_path),"flat_model_path":str(fp),"flat_metadata_path":str(tmp_path/"flat.json"),"statistics":{"seed":1}}
    monkeypatch.setattr(runner,"metadata_encoder",lambda p:encoder)
    result=runner.test(p,(X,S,Y,H,meta,{"test":np.arange(8)},encoder.public),SimpleNamespace(usage=lambda:{}))
    assert result["test_rows"]==8 and set(result["row_scores"])=={"flat","public_heuristic","hierarchical"}
    assert (tmp_path/"test_predictions.npz").exists() and (tmp_path/"test_complete.json").exists()
    with pytest.raises(ValueError,match="already_opened"):runner.test(p,None,None)
