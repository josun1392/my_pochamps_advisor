"""Offline calibration contracts: zero native games and zero PPO transitions."""
from copy import deepcopy
import json
import pytest

from advisor.learned_difficulty_calibration import (
    ANALYSIS, RIVALS, PublicSampler, PublicRetryAudit, AttemptRateGuard, analyze, audit_receipts, game_slots, sample_seed,
)
from advisor.learned_execution_alignment import content_hash, digest, durable_json


def cases():
    return [{"index": i, "scenario_SHA256": str(i)} for i in range(128)]


def test_exact_budget_two_real_seats_and_all_seven_rivals():
    slots = game_slots(cases())
    assert len(slots) == 1792
    assert len({tuple(s.values()) for s in slots}) == 1792
    assert {r: sum(s["rival"] == r for s in slots) for r in RIVALS} == dict.fromkeys(RIVALS, 256)
    assert sum(s["seat"] == "p2" for s in slots) == 896
    with pytest.raises(ValueError):
        game_slots(cases()[:-1])
    with pytest.raises(ValueError):
        game_slots([cases()[0]]*128)


def test_seeded_own_public_sampling_exact_repeat_and_no_original_mutation():
    p = [0.] * 35
    p[6], p[7] = .25, .75
    proof = {"action_probabilities": p, "discounted_return_estimate": .3}
    view = {"revision": 0, "action_mask": [int(v>0) for v in p], "choices": [str(i) if v else None for i,v in enumerate(p)]}
    received = []
    def infer(v):
        received.append(v)
        return proof
    slot = game_slots(cases())[0]
    a,b = PublicSampler(infer,slot), PublicSampler(infer,slot)
    selected = [a(view)["action_index"] for _ in range(100)]
    assert selected == [b(view)["action_index"] for _ in range(100)]
    assert set(selected) == {6,7} and all(v is view for v in received)
    assert "action_index" not in proof
    assert a.pending == b.pending
    assert sample_seed(slot) != sample_seed({**slot, "seat":"p2"})
    p[2] = .1  # forbidden probability mass/normalization fails before submission
    with pytest.raises(ValueError):
        a(view)


def event(revision, decision, rejected=True):
    mask = [0]*35
    mask[6] = 1
    return {"before":{side:{"episode_id":"same", "revision":revision, "action_mask":mask}
                      for side in ("self","opponent")},
        "actions":{"self":6,"opponent":6},
        "result":{"decisions":decision,"action_rejected":rejected}}


def test_retries_progress_only_reset_total_preserved_and_wait_included():
    a = PublicRetryAudit(13)
    for i in range(7):
        a.observe(event(i,0))
    a.observe(event(7,1,False))
    a.observe(event(8,1))
    state = next(iter(a.monitor.pending.values()))
    assert state["total_rejections"] == 8 and state["consecutive_rejections"] == 1
    for i in range(9,15):
        a.observe(event(i,1))
    with pytest.raises(ValueError, match="eight_retries_without_native_progress"):
        a.observe(event(15,1))
    b = PublicRetryAudit(14)
    for i in range(7):
        e = event(i,1)
        e["before"]["self"]["action_mask"] = [int(j==26) for j in range(35)]
        e["actions"]["self"] = 26
        b.observe(e)
    with pytest.raises(ValueError, match="eight_retries"):
        b.observe(event(7,1))
    illegal = event(0,0)
    illegal["actions"]["self"] = 4
    with pytest.raises(ValueError, match="mask_illegal"):
        PublicRetryAudit(1).observe(illegal)


def test_storage_resume_no_uncertain_reexecution_and_corruption(tmp_path):
    (tmp_path/"receipts").mkdir()
    slots = game_slots(cases())
    assert audit_receipts(tmp_path,slots,"plan") == []
    start = {"phase":"game_started","index":0,"slot_sha256":content_hash(slots[0])}
    ledger = tmp_path/"game_ledger.jsonl"
    ledger.write_text(json.dumps(start)+"\n")
    with pytest.raises(ValueError,match="uncertain"):
        audit_receipts(tmp_path,slots,"plan")
    decisions = tmp_path/"decisions.gz"
    decisions.write_bytes(b"fixture")
    record = {"winner":"self"}
    row = {"slot":slots[0],"plan_sha256":"plan","record":record,"record_sha256":content_hash(record),
           "decisions_path":str(decisions),"decisions_sha256":digest(decisions)}
    receipt = tmp_path/"receipts"/"game_0000.json"
    durable_json(receipt,row)
    end = {"phase":"game_committed","index":0,"receipt_sha256":digest(receipt)}
    ledger.write_text(json.dumps(start)+"\n"+json.dumps(end)+"\n")
    assert audit_receipts(tmp_path,slots,"plan") == [row]
    with pytest.raises(ValueError):
        audit_receipts(tmp_path,slots,"other-plan")
    decisions.write_bytes(b"corrupt")
    with pytest.raises(ValueError,match="receipt_corrupt"):
        audit_receipts(tmp_path,slots,"plan")


def test_retry_rate_guard_spans_episode_boundaries_and_uses_512_attempts():
    guard = AttemptRateGuard()
    for i in range(511):
        guard.observe(i < 6)
    with pytest.raises(ValueError, match="rate_above_one_percent"):
        guard.observe(False)
    guard = AttemptRateGuard()
    for i in range(1024):
        guard.observe(i < 5)
    assert guard.attempts == guard.rejections == 0


def synthetic(kind):
    def record(slot):
        r = RIVALS.index(slot["rival"])
        win = slot["case"] % 2 == 0 if kind == "equal" else r < 2 or (2<=r<5 and slot["case"]%2==0)
        return {"winner":"self" if win else "opponent","truncated":False,"native_choice_rejections":0}
    return [{"slot":s,"record":record(s)} for s in game_slots(cases())]


def test_cluster_analysis_never_forces_tiers_or_labels_truncations_draws(monkeypatch):
    monkeypatch.setitem(ANALYSIS,"resamples",256)
    equal = analyze(synthetic("equal"),cases())
    assert not equal["three_tiers_supported"] and equal["tiers"] is None
    assert all(p["a_minus_b"] == 0 and p["case_cluster_95"] == [0,0] for p in equal["paired"])
    distinct = analyze(synthetic("distinct"),cases())
    assert distinct["three_tiers_supported"]
    assert distinct["tiers"] == {"easy":list(RIVALS[:2]),"middle":list(RIVALS[2:5]),"strong":list(RIVALS[5:])}
    truncated = synthetic("distinct")
    truncated[0]["record"]["truncated"] = True
    result = analyze(truncated,cases())
    assert not result["three_tiers_supported"]
    assert result["summary"][RIVALS[0]]["truncated"] == 1
    assert result["summary"][RIVALS[0]]["draw"] == 0
    with pytest.raises(ValueError):
        analyze(truncated[:-1],cases())
    with pytest.raises(ValueError):
        analyze(truncated+truncated[:1],cases())


def test_evaluator_public_audit_hook_unchanged_policies_and_true_seats(monkeypatch):
    import scripts.evaluate_showdown_policy as evaluator
    mask = [int(i==6) for i in range(35)]
    def view(side):
        return {"episode_id":"id","revision":0,"side":side,"request_state":"move", "turn":1,
                "action_mask":mask,"choices":["move 1" if i==6 else None for i in range(35)],
                "state":{"self_side":{},"opponent_side":{}},"public_history":[]}
    class Env:
        def __init__(self,*a,**kw): pass
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def observation(self,side,**kw): return view(side)
        def step(self,actions,revision):
            assert actions == {"self":6,"opponent":6} and revision == 0
            return {"terminated":True,"truncated":False,"winner":"opponent","decisions":1,
                    "action_rejected":False,"rewards":{"self":-1,"opponent":1}}
    class Policy:
        model_id = "frozen-stub"
        def act(self,v): return 6
    monkeypatch.setattr(evaluator,"ShowdownEnvironment",Env)
    import advisor.learned_tactical_curriculum as curriculum
    monkeypatch.setattr(curriculum,"reset_learning_episode",lambda e,c: {})
    scenario = {"teams":{"self":["a"],"opponent":["b"]},"preview":{"self":[1,2,3],"opponent":[3,2,1]},"seed":[1,2,3,4]}
    seen=[]
    def callback(e):
        seen.append(deepcopy(e))
        e["before"]["self"]["action_mask"][6] = 0  # detached audit snapshot
    provider=lambda s,i:deepcopy(scenario)
    provider.identity = {"purpose":"offline_stub_no_native_game"}
    kwargs=dict(case_provider=provider,rivals={"rival":Policy()},cases=1,candidate_seat="p2")
    normal=evaluator.evaluate("unused", "unused", {"parent":Policy()},**kwargs)
    audited=evaluator.evaluate("unused", "unused", {"parent":Policy()},transition_observer=callback,**kwargs)
    assert normal["records"] == audited["records"]
    assert audited["records"][0]["winner"] == "self" and seen[0]["before"]["opponent"]["side"] == "opponent"
    assert not set(seen[0]) & {"scenario","checkpoint","native_state","rng"}
    assert seen[0]["before"]["self"]["action_mask"][6] == 1
