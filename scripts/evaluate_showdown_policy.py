"""Paired, held-out native battle evaluations. No training or hidden policy input."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from collections import Counter
from copy import deepcopy
import json
from math import sqrt
from time import perf_counter
import numpy as np
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_policy import LearnedPolicy
from advisor.learned_scenarios import scenario
from advisor.learned_encoder import identifier, fingerprint
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learned_public_metrics import public_heal_failure_attribution


def wilson(wins, n):
    if not n:
        return [0, 1]
    z = 1.959963984540054
    p = wins / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [center - margin, center + margin]


def native_heal_failures(history, role="p1"):
    """Legacy recipient-event count, not attribution to a requested recovery.

    Opponent Heal Pulse can also fail on this recipient. Use the separate
    versioned attribution field for explicit executed-move source evidence.
    """
    total, longest, run = 0, 0, 0
    last_failed = False
    for line in history:
        parts = line.split("|")
        if len(parts) > 2 and parts[2].startswith(role):
            if parts[1] in {"move", "switch", "drag"}:
                if not last_failed or parts[1] != "move":
                    run = 0
                last_failed = False
            elif parts[1] == "-fail" and len(parts) > 3 and parts[3] == "heal":
                total += 1
                run += 1
                longest = max(longest, run)
                last_failed = True
    return total, longest


NATIVE_SEAT_CONTRACT = "own_team_preserving_native_seats_v1"
FIXTURE_SEAT_CONTRACT = "fixed_fixture_policy_seats_v1"


def seat_scenario(case, candidate_seat, contract=NATIVE_SEAT_CONTRACT):
    """Explicitly distinguish physical-seat swaps from paired team assignment.

    The original contract moves a candidate's own team with it to p2. The fixed
    fixture contract keeps both native teams/preview orders in place and assigns
    the candidate to the other real request owner; it therefore plays each team.
    """
    if candidate_seat not in ("p1", "p2"):
        raise ValueError("invalid_candidate_seat")
    if contract not in (NATIVE_SEAT_CONTRACT, FIXTURE_SEAT_CONTRACT):
        raise ValueError("invalid_evaluation_seat_contract")
    case = deepcopy(case)
    if candidate_seat == "p2" and contract == NATIVE_SEAT_CONTRACT:
        if case.get("history"):
            raise ValueError("seat_swap_cannot_reinterpret_observed_history")
        for key in ("teams", "preview"):
            if key in case:
                case[key] = {"self": case[key]["opponent"], "opponent": case[key]["self"]}
        if "learning_start" in case:
            case["learning_start"]["prefix"] = [list(reversed(p)) for p in case["learning_start"].get("prefix", [])]
    return case


def paired_comparisons(records, policies):
    """Resample paired case clusters, retaining all configured rival strata."""
    cases = sorted({r["case"] for r in records})
    scores = {
        kind: np.asarray(
            [
                sum(
                    r["winner"] == "self" and not r["truncated"]
                    for r in records
                    if r["policy"] == kind and r["case"] == case
                )
                / max(
                    1, sum(r["policy"] == kind and r["case"] == case for r in records)
                )
                for case in cases
            ]
        )
        for kind in policies
    }
    rng = np.random.default_rng(20261012)
    draws = rng.integers(0, len(cases), size=(2000, len(cases)))
    result = []
    for kind in policies:
        if kind in {"random", "max_power", "heuristic", "untrained"}:
            continue
        for base in (
            "random",
            "heuristic",
            "champions_heuristic",
            "tactical_heuristic",
            "max_power",
            "untrained",
            "previous",
            "previous_action",
            "previous_initial",
            "previous_generalization",
            "previous_tactical",
            "control",
            "cold_v2",
        ):
            if base not in scores or kind == base:
                continue
            difference = scores[kind] - scores[base]
            interval = np.quantile(difference[draws].mean(axis=1), [0.025, 0.975])
            result.append(
                {
                    "policy": kind,
                    "baseline": base,
                    "paired_win_fraction_difference": float(difference.mean()),
                    "case_cluster_bootstrap_95": [float(x) for x in interval],
                    "independent_case_clusters": len(cases),
                    "resamples": 2000,
                }
            )
    return result


def evaluate(
    checkout,
    catalog,
    policies,
    *,
    split="validation",
    cases=24,
    offset=0,
    curriculum_version="showdown-learning-curriculum-v1",
    rivals=None,
    stopping=None,
    progress=None,
    tactical_diagnostics=False,
    case_provider=None,
    candidate_seat="p1",
    seat_contract=NATIVE_SEAT_CONTRACT,
):
    if candidate_seat not in ("p1", "p2"):
        raise ValueError("invalid_candidate_seat")
    candidate_side = "self" if candidate_seat == "p1" else "opponent"
    rival_side = "opponent" if candidate_side == "self" else "self"
    if not 1 <= cases <= 256 or split not in {"validation", "test", "unseen"}:
        raise ValueError("bounded_held_out_evaluation_required")
    full_domain_identity = None
    if curriculum_version == "showdown-learning-curriculum-v7":
        from advisor.learned_full_domain import curriculum_identity

        full_domain_identity = curriculum_identity()
    elif curriculum_version == "showdown-learning-curriculum-v8":
        from advisor.learned_full_roster import study_identity

        full_domain_identity = study_identity()
    started = perf_counter()
    records = []
    rivals = rivals or {kind: kind for kind in ("random", "max_power", "heuristic")}
    if not 1 <= len(rivals) <= 6 or "all" in rivals:
        raise ValueError("bounded_named_rivals_required")
    with ShowdownEnvironment(checkout, max_decisions=256) as env:
        for kind, policy in policies.items():
            for opponent, rival_policy in rivals.items():
                for index in range(offset, offset + cases):
                    if stopping and stopping():
                        raise TimeoutError("held_out_evaluation_budget_exhausted")
                    from advisor.learned_tactical_curriculum import (
                        reset_learning_episode,
                    )

                    canonical_case = (case_provider(split, index) if case_provider is not None
                                      else scenario(split, index, version=curriculum_version))
                    native_case = seat_scenario(canonical_case, candidate_seat, seat_contract)
                    start_info = reset_learning_episode(env, native_case)
                    rival = (
                        VisibleBaseline(rival_policy, index + 919)
                        if isinstance(rival_policy, str)
                        else rival_policy
                    )
                    player = (
                        VisibleBaseline(policy, index + 191)
                        if isinstance(policy, str)
                        else policy
                    )
                    values = []
                    steps = 0
                    action_counts = Counter()
                    tactical_counts = Counter()
                    requested_heal_full_hp = 0
                    native_rejections = 0
                    prefix_history_length = len(
                        env.observation("self", include_history=True)["public_history"]
                    )
                    if tactical_diagnostics:
                        from advisor.learned_tactical_diagnostics import (
                            TacticalDiagnostics,
                        )

                        diagnostics = TacticalDiagnostics()
                    while True:
                        own, other = (
                            env.observation(candidate_side, include_history=True),
                            env.observation(rival_side, include_history=True),
                        )
                        if isinstance(player, LearnedPolicy):
                            proof = player.infer(own)
                            action = proof["action_index"]
                            if not own["action_mask"][26]:
                                values.append(proof["discounted_return_estimate"])
                        else:
                            action = player.act(own)
                        if tactical_diagnostics:
                            d = diagnostics.describe(own, action)
                            active = own["state"]["self_side"]["active_identity"]
                            active_row = (
                                own["state"]["self_side"]["pokemon"].get(active, {})
                                if isinstance(active, str)
                                else {}
                            )
                            if (
                                d["selected"] == "recovery"
                                and active_row.get("hp_fraction") == 1
                            ):
                                requested_heal_full_hp += 1
                            tactical_counts["selected:" + d["selected"]] += 1
                            for available in d["available"]:
                                tactical_counts["available:" + available] += 1
                                tactical_counts[
                                    f"available:{available}:selected:{d['selected']}"
                                ] += 1
                            if d.get("public_type_prior") == "unfavorable" and d.get(
                                "better_bench_prior"
                            ):
                                tactical_counts["unfavorable_better_bench"] += 1
                                tactical_counts[
                                    "unfavorable_better_bench:selected:" + d["selected"]
                                ] += 1
                            if (
                                d.get("hp_band") == "injured"
                                and "recovery" in d["available"]
                            ):
                                tactical_counts["injured_recovery_available"] += 1
                                tactical_counts[
                                    "injured_recovery_available:selected:"
                                    + d["selected"]
                                ] += 1
                        action_counts[
                            "wait"
                            if action == 26
                            else "forced_switch"
                            if action < 6 and own["request_state"] == "switch"
                            else "voluntary_switch"
                            if action < 6
                            else "attack_or_status"
                        ] += 1
                        result = env.step(
                            {candidate_side: action, rival_side: rival.act(other)},
                            revision=own["revision"],
                        )
                        steps += 1
                        native_rejections += int(result["action_rejected"])
                        if result["terminated"] or result["truncated"]:
                            break
                    reward = result["rewards"][candidate_side]
                    history = env.observation(candidate_side, include_history=True)[
                        "public_history"
                    ][prefix_history_length:]
                    own_moves = Counter(
                        identifier(parts[3])
                        for line in history
                        for parts in [line.split("|")]
                        if len(parts) > 3
                        and parts[1] == "move"
                        and parts[2].startswith(candidate_seat)
                    )
                    heal_failures, longest_failures = native_heal_failures(history, candidate_seat)
                    error = (
                        float(
                            np.mean(
                                [
                                    (v - (player.model.gamma ** (len(values) - 1 - i)) * reward) ** 2
                                    for i, v in enumerate(values)
                                ]
                            )
                        )
                        if values and not result["truncated"]
                        else None
                    )
                    records.append(
                        {
                            "policy": kind,
                            "opponent": opponent,
                            "case": index,
                            "winner": ("self" if result["winner"] == candidate_side else "opponent"
                                       if result["winner"] == rival_side else None),
                            "raw_native_winner": result["winner"],
                            "candidate_seat": candidate_seat,
                            "seat_contract": seat_contract,
                            "canonical_scenario_sha256": fingerprint(canonical_case),
                            "native_scenario_sha256": fingerprint(native_case),
                            "initial_native_seed": native_case.get("seed"),
                            "native_choice_rejections": native_rejections,
                            "truncated": result["truncated"],
                            "decisions": steps,
                            "return": reward,
                            "value_discounted_return_mse": error,
                            "value_gamma": player.model.gamma if isinstance(player, LearnedPolicy) else None,
                            "training_objective": player.metadata.get("training_objective")
                            if isinstance(player, LearnedPolicy) else None,
                            "initial_discounted_return_estimate": values[0]
                            if values
                            else None,
                            "action_counts": dict(action_counts),
                            "native_own_move_counts": dict(own_moves),
                            "native_own_failed_heals": heal_failures,
                            # Legacy count names the recipient, not the move's actor.
                            "native_heal_failure_attribution": public_heal_failure_attribution(history, candidate_seat),
                            "native_own_max_consecutive_failed_heals": longest_failures,
                            "requested_heal_full_hp": requested_heal_full_hp
                            if tactical_diagnostics
                            else None,
                            "tactical_counts": dict(tactical_counts),
                            "curriculum_start": start_info,
                            "public_event_counts": dict(
                                Counter(
                                    line.split("|")[1]
                                    for line in env.observation(
                                        candidate_side, include_history=True
                                    )["public_history"]
                                    if line.startswith("|")
                                )
                            ),
                        }
                    )
                if progress:
                    progress(records)
    summaries = []
    for kind in policies:
        for opponent in (*rivals, "all"):
            rows = [
                r
                for r in records
                if r["policy"] == kind
                and (opponent == "all" or r["opponent"] == opponent)
            ]
            counts = Counter(
                "truncated" if r["truncated"] else r["winner"] or "draw" for r in rows
            )
            n = len(rows)
            wins = counts["self"]
            valid = [
                r["value_discounted_return_mse"]
                for r in rows
                if r["value_discounted_return_mse"] is not None
            ]
            summaries.append(
                {
                    "policy": kind,
                    "opponent": opponent,
                    "n": n,
                    "wins": wins,
                    "losses": counts["opponent"],
                    "draws": counts["draw"],
                    "truncated": counts["truncated"],
                    "win_fraction": wins / n,
                    "wilson_95": wilson(wins, n),
                    "mean_return": sum(r["return"] for r in rows) / n,
                    "mean_decisions": sum(r["decisions"] for r in rows) / n,
                    "action_counts": dict(
                        sum((Counter(r["action_counts"]) for r in rows), Counter())
                    ),
                    "native_own_move_counts": dict(
                        sum(
                            (Counter(r["native_own_move_counts"]) for r in rows),
                            Counter(),
                        )
                    ),
                    "native_own_failed_heals": sum(
                        r["native_own_failed_heals"] for r in rows
                    ),
                    "native_own_max_consecutive_failed_heals": max(
                        (r["native_own_max_consecutive_failed_heals"] for r in rows),
                        default=0,
                    ),
                    "requested_heal_full_hp": sum(
                        r["requested_heal_full_hp"] for r in rows
                    )
                    if tactical_diagnostics
                    else None,
                    "tactical_counts": dict(
                        sum((Counter(r["tactical_counts"]) for r in rows), Counter())
                    ),
                    "public_event_counts": dict(
                        sum(
                            (Counter(r["public_event_counts"]) for r in rows), Counter()
                        )
                    ),
                    "value_discounted_return_mse": sum(valid) / len(valid)
                    if valid
                    else None,
                }
            )
    return {
        "schema_version": "showdown-learned-evaluation-v1",
        "split": split,
        "curriculum_version": curriculum_version,
        **({"evaluation_case_bank": case_provider.identity} if case_provider is not None else {}),
        **(
            {"full_domain_identity": full_domain_identity}
            if full_domain_identity
            else {}
        ),
        "cases_per_opponent": cases,
        "offset": offset,
        "candidate_seat": candidate_seat,
        "seat_contract": seat_contract,
        "interpretation": "held_out_sampled_win_frequencies_not_exact_probabilities",
        "elapsed_s": perf_counter() - started,
        "policies": {
            k: (v if isinstance(v, str) else v.model_id) for k, v in policies.items()
        },
        "rivals": {
            k: v if isinstance(v, str) else v.model_id for k, v in rivals.items()
        },
        "summaries": summaries,
        "paired_comparisons": paired_comparisons(records, policies),
        "uncertainty_scope": "per_stratum_Wilson_and_paired_case_cluster_bootstrap; pooled_Wilson_is_descriptive",
        "action_count_scope": "forced_switch_includes_faint_or_pivot_request_switch; native_own_move_counts_are_public_executed_moves",
        "records": records,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", type=Path, required=True)
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--model", type=Path, action="append", default=[])
    p.add_argument("--untrained", type=Path)
    p.add_argument("--cases", type=int, default=24)
    p.add_argument(
        "--split", default="validation", choices=["validation", "test", "unseen"]
    )
    p.add_argument("--offset", type=int, default=0)
    p.add_argument(
        "--curriculum",
        default="showdown-learning-curriculum-v1",
        choices=[
            "showdown-learning-curriculum-v1",
            "showdown-learning-curriculum-v2",
            "showdown-learning-curriculum-v3",
        ],
    )
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("new_evaluation_output_required")
    policies = {kind: kind for kind in ("random", "max_power", "heuristic")}
    if a.untrained:
        policies["untrained"] = LearnedPolicy(
            a.untrained, a.catalog, require_manifest=False
        )
    for path in a.model:
        policies[path.stem] = LearnedPolicy(path, a.catalog)
    report = evaluate(
        a.checkout,
        a.catalog,
        policies,
        split=a.split,
        cases=a.cases,
        offset=a.offset,
        curriculum_version=a.curriculum,
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    main()
