from copy import deepcopy
import numpy as np
import pytest

from advisor.learned_action_search_teacher import (
    public_candidates, select_from_search, summarize_confirmation,
)


def public():
    return {"request_state":"move","action_mask":[int(6<=a<=9) for a in range(35)],
        "choices":["move "+str(a-5) if 6<=a<=9 else None for a in range(35)],
        "own_request":{"active":[{"moves":[{"id":"tackle"},{"id":"recover"},
            {"id":"swordsdance"},{"id":"protect"}]}]}}


def probs():
    p=np.zeros(35);p[6:10]=[.7,.2,.08,.02];return p


def outcome(value=1,truncated=False):
    return {"terminated":not truncated,"truncated":truncated,
            "terminal_return":None if truncated else value}


def test_candidates_are_distinct_legal_public_and_outcome_independent():
    view=public();before=deepcopy(view);c=public_candidates(view,probs())
    assert c["actions"]==[6,7,8] and c["baseline"]==6
    changed={**view,"unused_hidden_native_truth":{"future_winner":"opponent","secret_set":"no input"}}
    assert public_candidates(changed,probs())==c and view==before
    assert len({r["native_choice"] for r in c["candidates"]})==3
    assert all(view["action_mask"][a] for a in c["actions"])


def test_second_alternative_prefers_new_family_without_changing_argmax():
    view=public();view["own_request"]["active"][0]["moves"][1]={"id":"quickattack"}
    c=public_candidates(view,probs())
    assert c["actions"]==[6,7,8]
    assert c["candidates"][2]["family"]=="setup"
    view["action_mask"][8]=view["action_mask"][9]=0
    view["choices"][8]=view["choices"][9]=None
    p=probs();p[6:10]=[.8,.2,0,0]
    assert public_candidates(view,p)["actions"]==[6,7]
    p[0]=.1
    with pytest.raises(ValueError):public_candidates(view,p)


def test_search_ties_retain_baseline_and_confirmation_is_not_a_selection_input():
    contract=public_candidates(public(),probs())
    rows={6:[outcome(1),outcome(-1)],7:[outcome(1),outcome(1)],8:[outcome(-1),outcome(-1)]}
    selected=select_from_search(contract,rows)
    assert selected["selected"]==7 and selected["search_return_gain"]==1
    tie={a:[outcome(1)] for a in contract["actions"]}
    assert select_from_search(contract,tie)["selected"]==6
    assert rows[6][0]["terminal_return"]==1


def test_truncation_has_no_completed_return_or_teacher_label():
    contract=public_candidates(public(),probs())
    rows={a:[outcome(1)] for a in contract["actions"]}
    rows[8]=[outcome(truncated=True)]
    result=select_from_search(contract,rows)
    assert result["status"]=="incomplete_search_no_teacher"
    assert result["selected"]==contract["baseline"] and not result["means"]


def test_confirmation_can_reverse_search_and_keeps_all_roots():
    changed={"root":"changed","baseline_action":6,"selected_action":7,"baseline_family":"attack",
        "selected_family":"recovery","search_gain":2,
        "pairs":[{"baseline":outcome(1),"selected":outcome(-1)} for _ in range(10)]}
    retained={"root":"retained","baseline_action":6,"selected_action":6,"baseline_family":"attack",
        "selected_family":"attack","search_gain":0,
        "pairs":[{"baseline":outcome(1),"selected":outcome(1)} for _ in range(10)]}
    result=summarize_confirmation([changed,retained],resamples=1000)
    assert result["search_mean_gain"]==1 and result["confirmation_mean_gain"]==-1
    assert result["root_clusters"]==2 and result["observed_worsened"]==1 and result["observed_ties"]==1
    assert result["root_rows"][0]["evidence"]=="conditional_worsening"
    assert result["root_rows"][1]["evidence"]=="baseline_retained"


def test_plan_rejects_overlapping_search_confirmation_before_file_access():
    from scripts.pilot_foundation_action_search_teacher import validate_plan
    with pytest.raises(ValueError,match="bounded_teacher"):
        validate_plan({"PPO":1})
    plan={"schema":"foundation-action-search-teacher-plan-v1","native_cap":1008,"global_cap":1024,
        "regression_reserve":16,"PPO":0,"device":"cpu","workers":1,"cpu_percent":50,
        "memory_mib":12288,"max_seconds":900,"search_seeds":[[1,2,3,4]]*6,
        "confirmation_seeds":[[5,6,7,8]]*10}
    with pytest.raises(ValueError,match="disjoint"):validate_plan(plan)
