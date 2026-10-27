"""Bounded first-action search feasibility, never deployed policy or PPO labels."""
import numpy as np
from advisor.learned_tactical_diagnostics import action_class

VERSION = "foundation-action-search-teacher-feasibility-v1"

# This is deliberately distinct from the privileged, fixed-hidden-state search
# above. A public response surrogate is useful diagnostic evidence, but is not
# automatically an admissible native branch teacher.
PUBLIC_VERSION = "foundation-public-search-teacher-admission-v1"
PUBLIC_KEYS = frozenset(("schema_version", "episode_id", "revision", "side", "turn",
    "request_state", "terminated", "truncated", "events", "own_request",
    "visible_active_health", "action_schema_version", "action_mask", "choices",
    "interpretation", "public_history", "projection_coverage", "state"))


def public_teacher_binding(view, *, policy_id, learning_step):
    """Bind an authenticated player view; never accept a coordinator envelope.

    The observation adapter remains the authority for the nested public state.
    Unknown additional fields are rejected, including innocuous-looking future
    additions, rather than silently extending the teacher information boundary.
    """
    from copy import deepcopy
    from advisor.learned_encoder import fingerprint
    if not isinstance(view, dict) or set(view) - PUBLIC_KEYS:
        raise ValueError("teacher_requires_public_observation_only")
    forbidden = {"native_state", "opponent_request", "checkpoint", "seed", "future_seed",
        "teams", "input_log", "auxiliary_labels", "coordinator_v5_supervision", "rng", "prng"}
    def reject_private(node):
        if isinstance(node, dict):
            if forbidden & set(node):
                raise ValueError("teacher_requires_public_observation_only")
            for value in node.values():
                reject_private(value)
        elif isinstance(node, (tuple, list)):
            for value in node:
                reject_private(value)
    reject_private(view)
    mask = view.get("action_mask", [])
    choices = view.get("choices", [])
    if (view.get("schema_version") != "showdown-policy-observation-v1"
            or view.get("action_schema_version") != "showdown-policy-actions-v1"
            or len(mask) != 35 or any(type(m) not in (int, bool) or m not in (0, 1) for m in mask)
            or not any(mask) or len(choices) != 35
            or any(mask[a] and (not isinstance(choices[a], str) or not choices[a]) for a in range(35))
            or not isinstance(view.get("episode_id"), str)
            or type(view.get("revision")) is not int
            or type(view.get("turn")) is not int
            or view.get("side") not in ("self", "opponent")
            or not isinstance(policy_id, str) or not policy_id
            or type(learning_step) is not int or learning_step < 0):
        raise ValueError("invalid_teacher_decision_binding")
    role = "p1" if view["side"] == "self" else "p2"
    if view.get("own_request", {}).get("side", {}).get("id") != role:
        raise ValueError("teacher_own_request_role_mismatch")
    public = deepcopy(view)
    binding = {"episode_id": view["episode_id"], "revision": view["revision"],
        "side": view["side"], "turn": view["turn"], "policy_id": policy_id,
        "learning_step": learning_step, "public_SHA256": fingerprint(public),
        "mask_SHA256": fingerprint(mask), "action_schema_version": view["action_schema_version"]}
    return public, binding


class PublicInformationSearchTeacher:
    """Public-only admission gate over the existing bounded response owner.

    No native checkpoint, real hidden set, Foundation probability or result is
    an input. Current surrogate limitations cause abstention. Removing them
    requires a separately reviewed public-hypothesis producer, not a flag that
    relabels the old privileged search output.
    """
    version = PUBLIC_VERSION

    def __init__(self, *, catalog, checkout):
        from advisor.learned_public_best_response import PublicBestResponseOpponent
        self.response = PublicBestResponseOpponent(catalog=catalog, checkout=checkout)

    def assess(self, view, *, policy_id, learning_step):
        public, binding = public_teacher_binding(view, policy_id=policy_id, learning_step=learning_step)
        base = {"schema_version": PUBLIC_VERSION, "binding": binding,
            "status": "abstain", "target": None, "evidence_scope": "public_only_admission"}
        if public["request_state"] != "move" or sum(public["action_mask"]) < 2:
            return {**base, "reason": "no_nontrivial_public_comparison"}
        self.response.act(public)
        decision = self.response.last_decision
        # A fallback is NEVER a supervised target. Nor do the surrogate's
        # uncertain availability, neutral unknown modifiers or nominal utility
        # become complete native outcomes simply because it chose an action.
        reason = decision.get("fallback") or "conditional_surrogate_not_public_native_branch_evidence"
        return {**base, "reason": reason,
            "diagnostic": {"response_version": self.response.kind,
                "compared_candidates": len(decision.get("comparisons", [])),
                "limitations": list(decision.get("limitations", [])),
                "unknown_response_availability": sum(r.get("current_availability", "").startswith("unknown")
                    for r in decision.get("responses", []))}}


def validate_public_teacher_target(decision, view, *, policy_id, learning_step):
    """Structural/provenance validation, NOT certification of label quality.

    The in-process provider must still pass its public evidence/coverage gate.
    The consumer cannot accept old select_from_search() dictionaries or a
    terminal outcome masquerading as an executed trajectory/return target.
    """
    _, binding = public_teacher_binding(view, policy_id=policy_id, learning_step=learning_step)
    if (decision.get("schema_version") != PUBLIC_VERSION or decision.get("binding") != binding
            or decision.get("evidence_scope") != "public_only_admission"):
        raise ValueError("stale_or_unbound_public_teacher_target")
    target = decision.get("target")
    if decision.get("status") == "abstain":
        if target is not None:
            raise ValueError("abstaining_teacher_has_target")
        return None
    if decision.get("status") != "supported":
        raise ValueError("unsupported_public_teacher_status")
    p = np.asarray(target, dtype=float)
    mask = np.asarray(view["action_mask"], dtype=bool)
    if (p.shape != (35,) or not np.isfinite(p).all() or (p < 0).any()
            or p[~mask].any() or not np.isclose(p.sum(), 1., atol=1e-8, rtol=0)):
        raise ValueError("teacher_target_must_be_legal_distribution")
    return p


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
