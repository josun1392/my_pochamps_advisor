"""Coordinator-only, public-root conditional native branches; never oracle labels.

Checkpoints must be constructed from explicitly declared hypothetical teams.
This module cannot infer a posterior over hidden sets. Its caller must test all
hypotheses against the same delivered player view before admitting any samples.
No checkpoint, hypothesis ID, future seed or opponent request reaches a policy.
"""
from copy import deepcopy
from hashlib import sha256
import json

SCHEMA = "showdown-public-action-conditional-signals-v1"


def public_decision(view):
    """Remove transport timing only, retaining ALL delivered public evidence."""
    return {k: deepcopy(v) for k, v in view.items()
            if k not in {"episode_id", "revision", "events"}}


def public_identity(view):
    return sha256(json.dumps(public_decision(view), sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def require_public_equivalence(reference, hypothetical):
    if public_decision(reference) != public_decision(hypothetical):
        raise ValueError("hypothesis_contradicts_delivered_public_decision")


def candidate_actions(view, limit=5):
    """One public representative per family, then a second attack/switch.

    Selection is coverage-based, not chosen using sampled outcomes or private
    damage. Native request masks remain authoritative (including retry updates).
    """
    from advisor.learned_tactical_diagnostics import action_class
    if view["request_state"] != "move" or not 2 <= limit <= 8:
        raise ValueError("supported_branch_decision_required")
    legal = [i for i, m in enumerate(view["action_mask"]) if m]
    rows = {}
    for a in legal:
        rows.setdefault(action_class(view, a), []).append(a)
    result = [rows[c][0] for c in ("attack", "switch", "recovery", "defense", "setup", "status_or_field") if c in rows]
    for c in ("attack", "switch"):
        if c in rows:
            result.extend(rows[c][1:2])
    return result[:limit]


def public_position(view):
    """Descriptive visible health only; unknown fractions remain unknown.

    This is not a damage model, reward or a completed-game return.
    """
    own = view["own_request"].get("side", {}).get("pokemon", [])
    own_health = []
    for p in own:
        hp = p.get("condition", "").split()[0]
        if hp == "0": own_health.append(0.)
        elif "/" in hp:
            n, d = hp.split("/")
            own_health.append(int(n) / int(d))
    other = view["state"]["opponent_side"]
    active = other["pokemon"].get(other["active_identity"], {}) if isinstance(other["active_identity"], str) else {}
    return {"own_brought_health_fractions": own_health,
            "opponent_active_visible_hp_fraction": active.get("hp_fraction"),
            "public_turn": view["turn"], "request_state": view["request_state"]}


def branch_candidate(env, checkpoint, reference, *, side, action, future_seed,
                     own_policy, opponent_policy, short_horizon=8, stopping=None):
    """Specific hypothetical execution plus fixed public-policy continuation.

    Common initial RNG is a variance-control device, not identical downstream
    random events after choices diverge. No private snapshot is a data feature.
    A rejected initial candidate has NO action-return label.
    """
    if side not in {"self", "opponent"} or not 1 <= short_horizon <= 32:
        raise ValueError("bounded_branch_scope_required")
    env.restart(checkpoint, future_seed=future_seed)
    view = env.observation(side, include_history=True)
    require_public_equivalence(reference, view)
    if type(action) is not int or not 0 <= action < 35 or not view["action_mask"][action]:
        raise ValueError("masked_conditional_candidate")
    other = "opponent" if side == "self" else "self"
    initial_history = len(view["public_history"])
    traces, rejection_count, short = [], 0, None
    for step in range(4096):
        if stopping and stopping(): raise TimeoutError("action_signal_budget_exhausted")
        view = env.observation(side, include_history=True)
        rival = env.observation(other, include_history=True)
        chosen = action if step == 0 else own_policy.act(view)
        opposing = opponent_policy.act(rival)
        if not view["action_mask"][chosen] or not rival["action_mask"][opposing]:
            raise ValueError("conditional_policy_mask_violation")
        result = env.step({side: chosen, other: opposing}, revision=view["revision"])
        after = env.observation(side, include_history=True)
        rejection_count += int(result["action_rejected"])
        if step < short_horizon:
            traces.append({"step": step + 1, "own_selected_action": chosen,
                           "own_native_choice": view["choices"][chosen],
                           "own_action_mask": list(view["action_mask"]),
                           "action_rejected": result["action_rejected"],
                           "events": after["public_history"][len(view["public_history"]):],
                           "position": public_position(after)})
        if result["action_rejected"] and step == 0:
            return {"status": "initial_candidate_rejected_no_label", "native_rejections": rejection_count,
                    "trace": traces, "terminal_return": None}
        if step + 1 == short_horizon or result["terminated"] or result["truncated"]:
            if short is None:
                short = {"decisions": step + 1, "position": public_position(after),
                         "terminated": result["terminated"], "truncated": result["truncated"],
                         "value_estimate": (own_policy.infer(after)["discounted_return_estimate"]
                            if not result["terminated"] and not result["truncated"] and hasattr(own_policy, "infer") else None)}
        if result["terminated"] or result["truncated"]:
            return {"status": "completed", "decisions": step + 1,
                    "terminated": result["terminated"], "truncated": result["truncated"],
                    "winner": result["winner"],
                    "terminal_return": result["rewards"][side] if result["terminated"] else None,
                    "native_rejections": rejection_count, "short_continuation": short,
                    "immediate": traces[0], "trace": traces,
                    "visible_history_sha256": sha256("\n".join(after["public_history"][initial_history:]).encode()).hexdigest()}
    raise ValueError("conditional_branch_did_not_close")
