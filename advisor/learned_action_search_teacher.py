"""Bounded first-action search feasibility, never deployed policy or PPO labels."""
import numpy as np
from advisor.learned_tactical_diagnostics import action_class

VERSION = "foundation-action-search-teacher-feasibility-v1"


def public_candidates(public, probabilities):
    """Argmax, strongest alternative, then strongest remaining family if present."""
    p = np.asarray(probabilities, dtype=float)
    mask = np.asarray(public["action_mask"], dtype=bool)
    if (p.shape != (35,) or mask.shape != (35,) or mask.sum() < 2
            or public["request_state"] != "move" or not np.isfinite(p).all()
            or (p < 0).any() or p[~mask].any() or not np.isclose(p.sum(), 1.)):
        raise ValueError("public_teacher_candidates_require_native_distribution")
    ordered = sorted(np.flatnonzero(mask).tolist(), key=lambda a: (-p[a], a))
    selected = ordered[:2]
    families = {action_class(public,a) for a in selected}
    rest = ordered[2:]
    if rest:
        preferred = [a for a in rest if action_class(public,a) not in families]
        selected.append((preferred or rest)[0])
    choices = [public["choices"][a] for a in selected]
    if any(not c for c in choices) or len(set(choices)) != len(choices):
        raise ValueError("teacher_candidates_require_distinct_native_choices")
    return {"baseline":selected[0], "actions":selected,
        "candidates":[{"action":a,"native_choice":public["choices"][a],
            "family":action_class(public,a),"policy_probability":float(p[a])} for a in selected],
        "rule":"legal_argmax_then_highest_other_probability_then_new_family_if_available"}


def select_from_search(contract, results):
    """Search-only selection; deterministic ties retain baseline."""
    actions=contract["actions"];means={}
    for a in actions:
        rows=results[a]
        if not rows or any(not r["terminated"] or r["truncated"] or r["terminal_return"] is None for r in rows):
            return {"status":"incomplete_search_no_teacher","selected":contract["baseline"],"means":{}}
        means[a]=float(np.mean([r["terminal_return"] for r in rows]))
    chosen=max(actions,key=lambda a:(means[a],-actions.index(a)))
    return {"status":"selected","selected":chosen,"means":means,
        "baseline":contract["baseline"],"search_return_gain":means[chosen]-means[contract["baseline"]]}


def summarize_confirmation(root_results, *, bootstrap_seed=2026102607, resamples=20000):
    rows=[];incomplete=[]
    for ordinal,root in enumerate(root_results):
        ps=root["pairs"]
        if (not ps or any(p[k]["terminal_return"] is None or not p[k]["terminated"]
                         or p[k]["truncated"] for p in ps for k in ("baseline","selected"))):
            incomplete.append(root["root"]);continue
        d=np.array([p["selected"]["terminal_return"]-p["baseline"]["terminal_return"] for p in ps],float)
        rng=np.random.default_rng(bootstrap_seed+1+ordinal)
        ci=np.quantile(d[rng.integers(0,len(d),size=(resamples,len(d)))].mean(1),[.025,.975]).tolist()
        same=root["selected_action"]==root["baseline_action"]
        evidence=("baseline_retained" if same else "conditional_improvement" if ci[0]>0
                  else "conditional_worsening" if ci[1]<0 else "uncertain")
        rows.append({"root":root["root"],"baseline":root["baseline_action"],"selected":root["selected_action"],
            "baseline_family":root["baseline_family"],"selected_family":root["selected_family"],
            "baseline_return":float(np.mean([p["baseline"]["terminal_return"] for p in ps])),
            "selected_return":float(np.mean([p["selected"]["terminal_return"] for p in ps])),
            "gain":float(d.mean()),"paired_gains":d.tolist(),"paired_seed_95CI":ci,
            "observed_direction":"improved" if d.mean()>0 else "worsened" if d.mean()<0 else "tie",
            "evidence":evidence,"search_gain":root["search_gain"],
            "interpretation":"fixed_hidden_state_conditional_teacher_upper_bound_not_live_public_search"})
    if not rows:
        return {"status":"UNSUPPORTED","root_rows":[],"incomplete_roots":incomplete}
    d=np.array([r["gain"] for r in rows])
    rng=np.random.default_rng(bootstrap_seed)
    ci=np.quantile(d[rng.integers(0,len(d),size=(resamples,len(d)))].mean(1),[.025,.975]).tolist()
    improved=sum(r["gain"]>0 for r in rows)
    status=("TEACHER_FEASIBILITY_SIGNAL" if ci[0]>0 and improved>=4
            else "UNSUPPORTED" if ci[1]<0 else "INCONCLUSIVE")
    return {"status":status,"root_rows":rows,"incomplete_roots":incomplete,
        "root_clusters":len(rows),"confirmation_mean_gain":float(d.mean()),"root_cluster_95CI":ci,
        "search_mean_gain":float(np.mean([r["search_gain"] for r in rows])),
        "selected_alternatives":sum(r["selected"]!=r["baseline"] for r in rows),
        "observed_improved":improved,"observed_worsened":sum(r["gain"]<0 for r in rows),
        "observed_ties":sum(r["gain"]==0 for r in rows),
        "uncertain_changed_roots":sum(r["evidence"]=="uncertain" for r in rows),
        "scope":"disjoint_confirmation_seeds_same_PPO_collected_training_roots_not_new_team_evaluation"}
