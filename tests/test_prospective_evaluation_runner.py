"""Offline runner contracts only; synthetic labels, no policy/native calls."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from advisor.learned_encoder import fingerprint
from advisor.learned_prospective_evaluation import OPPONENTS
from advisor.learned_prospective_runner import (
    protocol_points, ProtocolRunner, ApprovedSealedRunner, ReceiptStore, PublicTraceAudit,
    validate_terminal_record, paired_panel_analysis, FOUNDATION, CANDIDATE, inference_public_view,
)

F, C, V = "a"*64, "b"*64, "c"*64


def test_inference_envelope_keeps_public_receipt_metadata_without_private_roots():
    view = event(3, 0, False)["before"]["self"]
    view["events"] = ["|turn|1"]
    observed = inference_public_view(view)
    assert observed["episode_id"] == "episode" and observed["revision"] == 3
    assert observed["events"] == view["events"]
    observed["own_request"].clear()
    assert view["own_request"]
    with pytest.raises(ValueError):inference_public_view({**view, "seed": [1,2,3,4]})


def test_inference_envelope_refuses_missing_identity():
    view = event(0, 0, False)["before"]["self"];view.pop("episode_id")
    with pytest.raises(ValueError,match="metadata_missing"):inference_public_view(view)


class Source:
    sha256 = "d"*64

    @property
    def manifest(self):
        return {"reference_policy": {"sha256": F}, "opponents": {OPPONENTS[2]: {"sha256": V}},
            "cases": [{"case_id": "protocol"+str(i), "index": i,
                       "native_seeds": {o+":"+s: [i, j, k, 9] for j,o in enumerate(("a","b"))
                                        for k,s in enumerate(("self","opponent"))}} for i in range(4)]}

    def protocol_scenarios(self):
        for i, owner, seat in [(0,"a","self"),(1,"b","opponent")]:
            other = "opponent" if seat == "self" else "self"
            yield {"case_id": "protocol"+str(i), "owner": owner, "seat": seat,
                "scenario": {"teams": {seat: [{"species": owner}], other: [{"species": "other"}]},
                             "preview": {seat: [6,1,3], other: [4,2,5]},
                             "seed": [0,0,0,0], "history": []}}


def test_protocol_mapping_both_actual_seats_uses_frozen_cell_seed():
    points = list(protocol_points(Source()))
    assert len(points) == len({p["point_key"] for p in points}) == 12
    for p in points:
        assert p["scenario"]["teams"][p["seat"]][0]["species"] == p["candidate_team"]
        assert p["scenario"]["preview"][p["seat"]] == [6,1,3]
        case = Source().manifest["cases"][p["case_index"]]
        assert p["scenario"]["seed"] == case["native_seeds"][p["candidate_team"]+":"+p["seat"]]
    assert points[0]["scenario"] == points[1]["scenario"] == points[2]["scenario"]


@pytest.mark.parametrize("mutation", ["sealed","changed_scenario","wrong_model","wrong_rival"])
def test_admission_precedes_any_evaluator_or_model(tmp_path, mutation):
    def forbidden(*a, **k): pytest.fail("evaluation executed without admission")
    runner = ProtocolRunner(Source(),tmp_path,"unused","unused",C,evaluator=forbidden)
    p = next(protocol_points(Source())); actor = SimpleNamespace(model_id=F); rival=p["opponent"]
    if mutation == "sealed": p["point_key"] = "sealed"
    if mutation == "changed_scenario": p["scenario"]["seed"][0] += 1
    if mutation == "wrong_model": actor.model_id = V
    if mutation == "wrong_rival": rival = "random"
    with pytest.raises(ValueError):
        runner.run(p, FOUNDATION, actor, rival)
    assert runner.store.budget.count == 0


def test_receipts_are_idempotent_and_incomplete_intent_stops(tmp_path):
    store=ReceiptStore(tmp_path); identity={"game":1}
    assert store.existing(identity) is None
    store.begin(identity)
    with pytest.raises(ValueError,match="incomplete_intent"):store.existing(identity)
    store.complete(identity,{"return":1})
    assert ReceiptStore(tmp_path).existing(identity)=={"return":1}
    with pytest.raises(ValueError,match="already_complete"):store.begin(identity)
    _,p=store.paths(identity);d=json.loads(p.read_text());d["payload"]["return"]=-1
    p.write_text(json.dumps(d))
    with pytest.raises(ValueError,match="corrupt"):store.existing(identity)


def test_start_cap_and_STOP_are_hard_limits(tmp_path):
    store=ReceiptStore(tmp_path)
    for i in range(36):store.budget.reserve({"synthetic":i})
    with pytest.raises(RuntimeError,match="budget_exhausted"):store.budget.reserve({})
    (tmp_path/"STOP").write_text("test")
    with pytest.raises(RuntimeError,match="STOP"):ReceiptStore(tmp_path).budget.reserve({})


def test_sealed_runner_requires_separate_approval_before_enumeration(tmp_path):
    source=Source()
    source.points=lambda:pytest.fail("sealed points accessed before approval")
    with pytest.raises(ValueError,match="separate_T1_approval"):
        ApprovedSealedRunner(source,tmp_path,"unused","unused",C)


def test_future_sealed_gate_prepares_exact_source_without_execution(tmp_path):
    from fractions import Fraction
    from advisor.learned_prospective_evaluation import file_sha
    class FutureSource(Source):
        ready=True
        @property
        def manifest(self):
            m=super().manifest
            m["cases"] += [{"case_id":"sealed"+str(i),"index":i+4} for i in range(96)]
            return m
        def points(self):
            return iter({"case_id":"sealed"+str(i),"point_key":str(i)+":"+str(j),"mass":Fraction(1,1152)}
                        for i in range(96) for j in range(12))
    approval={"schema_version":"prospective-sealed-comparison-authorization-v1","authority":"T1","status":"APPROVED",
        "authority_ref":"SYNTHETIC_TEST_ONLY_NOT_REAL_APPROVAL","source_sha256":FutureSource.sha256,
        "Foundation_sha256":F,"candidate_sha256":C,"mode":"T1_argmax","points_per_model":1152,
        "models":2,"native_starts_max":2304,"replacement":False,"replay":False}
    path=tmp_path/"synthetic_approval.json";path.write_text(json.dumps(approval))
    runner=ApprovedSealedRunner(FutureSource(),tmp_path/"future","unused","unused",C,
        authorization=path,authorization_sha256=file_sha(path),evaluator=lambda *a,**kw:pytest.fail("native execution"))
    assert len(runner.allowed)==1152 and runner.store.budget.maximum==2304
    assert all(p["mass"]=="1/1152" for p in runner.allowed.values())
    with pytest.raises(ValueError,match="replay_not_authorized"):
        runner.run({},FOUNDATION,SimpleNamespace(model_id=F),"unused",purpose="replay")


def terminal(point, reward):
    side=point["seat"];other="opponent" if side=="self" else "self"
    winner=side if reward==1 else other if reward==-1 else None
    record={"return":reward,"winner":"self" if reward==1 else "opponent" if reward==-1 else None,
        "raw_native_winner":winner,"truncated":False,"candidate_seat":"p1" if side=="self" else "p2",
        "case":point["case_index"],"opponent":point["opponent"],
        "canonical_scenario_sha256":fingerprint(point["scenario"]),
        "native_scenario_sha256":fingerprint(point["scenario"]),
        "initial_native_seed":point["scenario"]["seed"]}
    trace={"terminal":{"terminated":True,"truncated":False,"winner":winner,"rewards":{side:reward,other:-reward}},
        "request_refresh":{"unresolved_rejections":0,"pending_is_unresolved":False}}
    return record,trace


@pytest.mark.parametrize("seat",["self","opponent"])
@pytest.mark.parametrize("reward",[-1,0,1])
def test_native_terminal_return_and_real_seat_mapping(seat,reward):
    p=next(p for p in protocol_points(Source()) if p["seat"]==seat)
    r,t=terminal(p,reward);assert validate_terminal_record(p,r,t)
    bad=deepcopy(r);bad["raw_native_winner"]="wrong"
    with pytest.raises(ValueError,match="perspective"):validate_terminal_record(p,bad,t)


@pytest.mark.parametrize("bad",["truncated","pending","unresolved"])
def test_nonterminal_and_unresolved_cannot_be_valid_result(bad):
    p=next(protocol_points(Source()));r,t=terminal(p,1)
    if bad=="truncated":t["terminal"].update(terminated=False,truncated=True);r["truncated"]=True
    if bad=="pending":t["request_refresh"]["pending_is_unresolved"]=True
    if bad=="unresolved":t["request_refresh"]["unresolved_rejections"]=1
    with pytest.raises(ValueError,match="not_a_valid_result"):validate_terminal_record(p,r,t)


def event(revision, decisions, rejected):
    def view(side,rev):
        return {"side":side,"episode_id":"episode","revision":rev,"turn":1,
                "own_request":{"side":{"id":"p1" if side=="self" else "p2"}},
                "action_mask":[int(i==6) for i in range(35)],"choices":[None]*6+["move 1"]+[None]*28}
    return {"before":{s:view(s,revision) for s in ("self","opponent")},
            "after":{s:view(s,revision+1) for s in ("self","opponent")},
            "actions":{"self":6,"opponent":6},
            "result":{"decisions":decisions,"revision":revision+1,"action_rejected":rejected,
                      "terminated":False,"truncated":False,"winner":None,"rewards":{"self":0,"opponent":0}}}


def ended_event(truncated=False):
    row = event(0,1,False)
    row["result"].update(terminated=not truncated,truncated=truncated,
        winner=None if truncated else "self", rewards={"self":0 if truncated else 1,"opponent":0 if truncated else -1})
    for v in row["after"].values():
        v.update(terminated=not truncated,truncated=truncated,action_mask=[0]*35,choices=[None]*35)
    return row


@pytest.mark.parametrize("truncated",[False,True])
def test_zero_action_terminal_trace_is_not_an_inference_input(truncated):
    audit=PublicTraceAudit();row=ended_event(truncated);audit.observe(row)
    assert audit.proof()["terminal"]["truncated"] is truncated
    with pytest.raises(ValueError):inference_public_view(row["after"]["self"])


@pytest.mark.parametrize("truncated",[False,True])
def test_single_game_commit_duplicate_callback_and_resume_without_execution(tmp_path,truncated):
    point=next(protocol_points(Source()));calls=[]
    def evaluator(*args,**kw):
        calls.append(1)
        assert kw["case_provider"]("validation",point["case_index"])==point["scenario"]
        kw["transition_observer"](ended_event(truncated))
        record,_=terminal(point,0 if truncated else 1);record["truncated"]=truncated
        kw["progress"]([record]);kw["progress"]([record])
        return {"records":[record]}
    runner=ProtocolRunner(Source(),tmp_path,"unused","unused",C,evaluator=evaluator)
    actor=SimpleNamespace(model_id=F)
    first,new=runner.run(point,FOUNDATION,actor,point["opponent"])
    assert new and first["valid_terminal"] is not truncated
    second,new=runner.run(point,FOUNDATION,actor,point["opponent"])
    # JSON object keys (refresh window indices) become strings on reload.
    assert not new and fingerprint(first)==fingerprint(second) and calls==[1] and runner.store.budget.count==1


def test_eight_unresolved_rejections_stop_and_accepted_progress_resets():
    audit=PublicTraceAudit()
    for i in range(7):audit.observe(event(i,0,True))
    with pytest.raises(ValueError,match="eight_rejections"):audit.observe(event(7,0,True))
    audit=PublicTraceAudit()
    for i in range(7):audit.observe(event(i,0,True))
    audit.observe(event(7,1,False))
    audit.observe(event(8,1,True))
    assert audit.consecutive_rejections==1


def test_STOP_at_accepted_native_boundary_stops_before_another_decision(tmp_path):
    point=next(protocol_points(Source()))
    def evaluator(*args,**kw):
        (tmp_path/"STOP").write_text("test")
        kw["transition_observer"](event(0,1,False))
        pytest.fail("did not stop at native boundary")
    runner=ProtocolRunner(Source(),tmp_path,"unused","unused",C,evaluator=evaluator)
    with pytest.raises(TimeoutError,match="native_boundary"):
        runner.run(point,FOUNDATION,SimpleNamespace(model_id=F),point["opponent"])
    assert runner.store.budget.count==1 and not list(tmp_path.glob("result_*.json"))


def panel():
    points=[{"case_id":str(i),"point_key":f"{i}:{j}"} for i in range(96) for j in range(12)]
    records=[{"point_key":p["point_key"],"model_sha256":m,"terminated":True,
              "record":{"return":1,"winner":"self","truncated":False}} for p in points for m in (F,C)]
    return points,records


def test_paired_statistics_keep_twelve_cells_in_each_case_and_inverse_sign():
    points,rows=panel()
    for r in rows:
        if r["model_sha256"]==C:r["record"].update(**{"return":-1,"winner":"opponent"})
    result=paired_panel_analysis(points,rows,F,C)
    assert result["case_clusters"]==96 and result["cells_per_case"]==12
    assert result["candidate_minus_Foundation_win_fraction"]=={"difference":-1.,"case_cluster_95":[-1.,-1.]}
    assert result["Foundation_minus_candidate_return"]=={"difference":2.,"case_cluster_95":[2.,2.]}


@pytest.mark.parametrize("bad",["missing","duplicate","truncated","not_terminated"])
def test_panel_does_not_hide_missing_duplicate_or_nonterminal(bad):
    points,rows=panel()
    if bad=="missing":rows.pop()
    if bad=="duplicate":rows[-1]=rows[0]
    if bad=="truncated":rows[-1]["record"]["truncated"]=True
    if bad=="not_terminated":rows[-1]["terminated"]=False
    with pytest.raises(ValueError):paired_panel_analysis(points,rows,F,C)
