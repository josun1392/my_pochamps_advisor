"""Synthetic authority/shape fixtures only; no native or policy execution."""
from copy import deepcopy
from fractions import Fraction
import json
from types import SimpleNamespace
import pytest

from advisor.learned_confirmation_evaluation import (
    IndependentConfirmationSource, IndependentConfirmationRunner, ConfirmationReceiptStore,
    VERSION, READY_VERSION, CASE_START, CASES, POINTS, STARTS,
)
from advisor.learned_prospective_evaluation import SHOWDOWN_COMMIT, FORMAT_ID, OPPONENTS, file_sha
from advisor.learned_prospective_runner import ApprovedSealedRunner, FOUNDATION


def write(path,value):
    path.write_text(json.dumps(value),encoding="utf-8")
    return {"path":path.name,"sha256":file_sha(path)}


@pytest.fixture
def fixture(tmp_path):
    teams=[[{"species":f"Structural-{j}-{k}","moves":["tackle"]} for k in range(6)] for j in range(576)]
    shared={"engine_commit":SHOWDOWN_COMMIT,"format_id":FORMAT_ID,"inventory_sha256":"e"*64}
    parts=[write(tmp_path/f"part{i}.json",{**shared,"schema_version":"showdown-full-domain-generated-teams-v1",
            "seed":[10,i,20,30],"teams":teams[i*192:(i+1)*192]}) for i in range(3)]
    asset=write(tmp_path/"teams.json",{**shared,"teams":teams})
    frozen=tmp_path/"model.zip";frozen.write_bytes(b"synthetic-policy-not-a-real-checkpoint")
    model={"kind":"frozen_model","path":str(frozen),"sha256":file_sha(frozen)}
    cases=[{"index":CASE_START+i,"case_id":"independent-confirmation-v1-"+str(CASE_START+i),
        "partition":"independent_confirmation","admitted":True,"team_indices":{"a":2*i,"b":2*i+1},
        "ordered3":{"a":[6,1,3],"b":[4,2,5]},
        "native_seeds":{o+":"+s:[i,oi,si,3] for oi,o in enumerate(("a","b")) for si,s in enumerate(("self","opponent"))}}
        for i in range(CASES)]
    m={"schema_version":VERSION,**shared,"native_team_validated":True,"team_asset":asset,"native_batches":parts,
       "cases":cases,"reference_policy":model,"opponent_order":list(OPPONENTS),
       "opponents":{k:dict(model) for k in OPPONENTS},
       "measure":{"name":"Q_independent_confirmation_v1","cases":288,"owners":["a","b"],
       "seats":["self","opponent"],"opponents":list(OPPONENTS),"points":3456,"point_mass":"1/3456",
       "case_mass":"1/288","renormalize":False,"historical_TRAIN_prior":False}}
    path=tmp_path/"manifest.json";write(path,m)
    return tmp_path,path,m


def ready(fixture):
    tmp,path,m=fixture;h=file_sha(path)
    novelty=write(tmp/"novelty.json",{"status":"PASS","manifest_sha256":h,"cases":288,"all_cases_admitted":True,
        "unique_teams":576,"old_semantic_team_overlap":0,"old_raw_team_overlap":0,"old_case_id_overlap":0,
        "old_case_index_overlap":0,"old_seed_overlap":0,"catalog_all_sets_supported":True})
    rp=tmp/"ready.json";write(rp,{"schema_version":READY_VERSION,"status":"CONFIRMATION_SOURCE_READY",
        "manifest_sha256":h,"novelty_audit":novelty})
    return IndependentConfirmationSource(path,h,readiness=rp,readiness_sha256=file_sha(rp))


def approval(tmp,source):
    c="c"*64
    p=tmp/"approval.json"
    write(p,{"schema_version":"independent-confirmation-authorization-v1","authority":"T1","status":"APPROVED",
        "authority_ref":"SYNTHETIC_TEST_NOT_REAL_PERMISSION","source_sha256":source.sha256,
        "Foundation_sha256":source.manifest["reference_policy"]["sha256"],"candidate_sha256":c,
        "mode":"T1_argmax","cases":288,"points_per_model":3456,"models":2,"native_starts_max":6912,
        "replacement":False,"replay":False,"primary":"paired_terminal_return_16K_minus_Foundation"})
    return p,c


def test_exact_measure_and_real_seats(fixture):
    source=ready(fixture);points=list(source.points());m=source.manifest
    assert len(points)==len({p["point_key"] for p in points})==POINTS
    assert len({p["case_id"] for p in points})==CASES
    assert sum((p["mass"] for p in points),Fraction())==1
    for p in points:
        case=m["cases"][p["case_index"]-CASE_START]
        assert p["scenario"]["preview"][p["seat"]]==case["ordered3"][p["candidate_team"]]
        assert p["scenario"]["seed"]==case["native_seeds"][p["candidate_team"]+":"+p["seat"]]
        assert p["scenario"]["teams"][p["seat"]]==source._teams[case["team_indices"][p["candidate_team"]]]


def test_unready_and_no_extra_protocol_budget(fixture):
    _,path,_=fixture;source=IndependentConfirmationSource(path,file_sha(path))
    with pytest.raises(ValueError,match="not_ready"):next(source.points())
    with pytest.raises(ValueError,match="no_extra_protocol"):source.protocol_scenarios()


@pytest.mark.parametrize("bad",["mass","seed","case","pair","preview","count"])
def test_shape_mutations_fail_closed(fixture,bad):
    _,path,m=fixture
    if bad=="mass":m["measure"]["point_mass"]="1/1152"
    if bad=="seed":m["cases"][1]["native_seeds"]=deepcopy(m["cases"][0]["native_seeds"])
    if bad=="case":m["cases"][0]["case_id"]="old-case"
    if bad=="pair":m["cases"][0]["team_indices"]["a"]=2
    if bad=="preview":m["cases"][0]["ordered3"]["a"]=[1,1,2]
    if bad=="count":m["cases"].pop()
    write(path,m)
    with pytest.raises(ValueError):IndependentConfirmationSource(path,file_sha(path))


def test_old_overlap_receipt_cannot_admit(fixture):
    tmp,path,_=fixture;source=ready(fixture)
    n=tmp/"novelty.json";v=json.loads(n.read_text());v["old_semantic_team_overlap"]=1
    nb=write(n,v);rp=tmp/"ready.json";r=json.loads(rp.read_text());r["novelty_audit"]=nb;write(rp,r)
    with pytest.raises(ValueError,match="novelty_not_established"):
        IndependentConfirmationSource(path,file_sha(path),readiness=rp,readiness_sha256=file_sha(rp))


def test_team_or_native_batch_mutation_is_detected(fixture):
    tmp,path,m=fixture;part=tmp/"part0.json";v=json.loads(part.read_text());v["teams"][0][0]["moves"]=["protect"]
    m["native_batches"][0]=write(part,v);write(path,m)
    with pytest.raises(ValueError,match="membership_mismatch"):IndependentConfirmationSource(path,file_sha(path))


def test_same_committed_game_kernel_and_no_preapproval_enumeration(fixture):
    source=ready(fixture);tmp,_,_=fixture
    assert IndependentConfirmationRunner.run is ApprovedSealedRunner.run
    source.points=lambda:pytest.fail("points accessed before authority check")
    with pytest.raises(ValueError,match="approval_required"):
        IndependentConfirmationRunner(source,tmp/"denied",None,None,"c"*64)
    assert not (tmp/"denied").exists()


@pytest.mark.parametrize("seat",["self","opponent"])
def test_native_kernel_reused_with_new_case_indices_and_receipts(fixture,seat):
    from tests.test_prospective_evaluation_runner import ended_event,terminal
    source=ready(fixture);tmp,_,_=fixture;auth,c=approval(tmp,source)
    point=next(p for p in source.points() if p["seat"]==seat);point["mass"]=str(point["mass"])
    def fake(*args,**kw):
        assert kw["case_provider"]("validation",point["case_index"])==point["scenario"]
        kw["transition_observer"](ended_event())
        record,_=terminal(point,1 if seat=="self" else -1)
        kw["progress"]([record]);kw["progress"]([record]);return {"records":[record]}
    runner=IndependentConfirmationRunner(source,tmp/"run",None,None,c,
        authorization=auth,authorization_sha256=file_sha(auth),evaluator=fake)
    result,new=runner.run(point,FOUNDATION,SimpleNamespace(model_id=source.manifest["reference_policy"]["sha256"]),point["opponent"])
    assert new and result["valid_terminal"] and runner.store.budget.maximum==STARTS
    with pytest.raises(ValueError,match="replay_not_authorized"):
        runner.run(point,FOUNDATION,None,None,purpose="replay")


def test_hard_budget_and_STOP(tmp_path):
    store=ConfirmationReceiptStore(tmp_path);store.budget.count=STARTS-1
    assert store.budget.reserve({"synthetic":True})==STARTS-1
    with pytest.raises(RuntimeError,match="budget_exhausted"):store.budget.reserve({})
    (tmp_path/"STOP").write_text("synthetic")
    with pytest.raises(RuntimeError,match="STOP"):store.budget.reserve({})


def synthetic_panel():
    points=[{"case_id":str(i),"point_key":f"{i}:{j}"} for i in range(288) for j in range(12)]
    rows=[{"point_key":p["point_key"],"model_sha256":m,"terminated":True,
           "record":{"return":g,"winner":"self" if g==1 else "opponent","truncated":False}}
          for p in points for m,g in (("f",-1),("c",1))]
    return points,rows


def test_confirmation_success_uses_new_return_interval_only():
    from advisor.learned_confirmation_evaluation import confirmation_panel_analysis
    result=confirmation_panel_analysis(*synthetic_panel(),"f","c")
    assert result["primary"]=="paired_terminal_return_16K_minus_Foundation"
    assert result["candidate_minus_Foundation_return"]=={"difference":2.,"case_cluster_95":[2.,2.]}
    assert result["candidate_minus_Foundation_win_fraction"]=={"difference":1.,"case_cluster_95":[1.,1.]}
    assert result["case_clusters"]==288 and result["independent_confirmation_passed"]


@pytest.mark.parametrize("bad",["missing","duplicate","truncated"])
def test_confirmation_statistics_require_complete_paired_panel(bad):
    from advisor.learned_confirmation_evaluation import confirmation_panel_analysis
    points,rows=synthetic_panel()
    if bad=="missing":rows.pop()
    if bad=="duplicate":rows[-1]=rows[0]
    if bad=="truncated":rows[-1]["record"]["truncated"]=True
    with pytest.raises(ValueError):confirmation_panel_analysis(points,rows,"f","c")
