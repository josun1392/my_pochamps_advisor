from copy import deepcopy
import hashlib
import json
from types import MappingProxyType

import pytest

from llm.advisor_current_state_runtime_admission import admit_current_state_observation
from llm.advisor_detached_observed_rng_reconciliation import materialize_historical_predictive_action_binding
from llm.advisor_offline_strategy_episode_dataset import (
    materialize_offline_strategy_dataset, materialize_offline_strategy_episode,
)
from llm.advisor_offline_strategy_transition_replay import materialize_offline_strategy_transition
from llm.advisor_pokemon_switch_observation import admit_pokemon_switch_observation
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_observed_scalar_attack_rng_reconciliation import _ledger as scalar_ledger
from tests.test_offline_strategy_transition_replay import _attack_case, _features, _run, _switch_case
from tests.test_production_pokemon_switch_observation_wiring import _manager as switch_manager


def _attack_step(manager, turn, hp_before, hp_after):
    decision = manager.capture_runtime_state_snapshot("s")
    owner = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "pikachu"}
    target = {"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "eevee"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=decision, decision_owner=owner)
    assert d0["status"] == "resolved"
    ledger = scalar_ledger(critical=False)
    bindings = {
        "session_id": "s", "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": owner, "attacker": owner, "target": target, "move_id": "shadow-ball",
    }
    ledger["bindings"] = deepcopy(bindings)
    for leaf in ledger["terminal_leaves"]:
        leaf["provenance"] = deepcopy(bindings)
    features = _features(decision, d0, "attack:shadow-ball", "attack", ledger)
    binding = materialize_historical_predictive_action_binding(predictive_ledger=ledger, turn_number=turn)
    assert binding["status"] == "resolved"
    executed = admit_previous_action_history_observation(
        runtime_session_manager=manager, captured_session_id="s", side="self",
        execution_move_id="shadow-ball", selected_move_id="shadow-ball",
        source_action_id=binding["source_action_id"], result_class="success", turn_number=turn,
    )
    assert executed["status"] == "resolved"
    hp = admit_current_state_observation(
        runtime_session_manager=manager, captured_session_id="s",
        event_kind="exact_hp_transition_observed",
        payload={"hp_before": hp_before, "hp_after": hp_after}, side="self", turn_number=turn,
    )
    assert hp["status"] == "resolved"
    result = materialize_offline_strategy_transition(
        feature_contract=features, candidate_id="attack:shadow-ball",
        decision_runtime_snapshot=decision, decision_turn_number=turn,
        observation_snapshot=manager.read_collection_snapshot(),
        executed_observation_id=executed["observations"][0]["observation_id"],
        next_runtime_snapshot=manager.capture_runtime_state_snapshot("s"),
        next_state_observation_id=hp["observation"]["observation_id"],
        historical_binding=binding, predictive_ledger=ledger,
    )
    assert result["status"] == "resolved", result
    return result


def _switch_step(manager, turn):
    decision = manager.capture_runtime_state_snapshot("s")
    owner = {"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "pikachu"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=decision, decision_owner=owner)
    assert d0["status"] == "resolved"
    candidate = "manual_switch:raichu"
    bindings = {
        "session_id": "s", "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": owner,
    }
    ledger = {
        "status": "evaluable", "schema_version": "exact-predictive-outcome-ledger-v1",
        "horizon": "immediate_action_consequence", "candidate_id": candidate,
        "action_type": "manual_switch", "bindings": deepcopy(bindings),
        "terminal_leaves": ({
            "leaf_id": "switch", "candidate_id": candidate, "action_type": "manual_switch",
            "probability": {"numerator": 1, "denominator": 1},
            "consequences": {"target_final_hp": None, "own_final_hp": None},
            "provenance": deepcopy(bindings),
        },),
        "terminal_probability_mass": {"numerator": 1, "denominator": 1},
    }
    features = _features(decision, d0, candidate, "manual_switch", ledger)
    switched = admit_pokemon_switch_observation(
        runtime_session_manager=manager, captured_session_id="s", side="self",
        switch_in_slot_index=1, switch_in_pokemon_id="raichu", turn_number=turn,
    )
    assert switched["status"] == "resolved"
    result = materialize_offline_strategy_transition(
        feature_contract=features, candidate_id=candidate,
        decision_runtime_snapshot=decision, decision_turn_number=turn,
        observation_snapshot=manager.read_collection_snapshot(),
        executed_observation_id=switched["observation"]["observation_id"],
        next_runtime_snapshot=manager.capture_runtime_state_snapshot("s"),
        next_state_observation_id=switched["observation"]["observation_id"],
    )
    assert result["status"] == "resolved", result
    return result


def _chain(*, switch=False, gap=False):
    manager = switch_manager()
    first = _attack_step(manager, 4, 90, 80)
    if gap:
        intervening = admit_current_state_observation(
            runtime_session_manager=manager, captured_session_id="s",
            event_kind="exact_hp_transition_observed",
            payload={"hp_before": 80, "hp_after": 75}, side="self", turn_number=5,
        )
        assert intervening["status"] == "resolved"
    second = _switch_step(manager, 5) if switch else _attack_step(manager, 5, 75 if gap else 80, 70)
    return first, second


def _editable(value):
    if isinstance(value, dict) or hasattr(value, "items"):
        return {key: _editable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_editable(item) for item in value]
    return value


def _frozen(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    return value


def _corrupted_record(record, change):
    """Reidentify a deliberately corrupt record to exercise episode checks."""
    value = _editable(record)
    change(value)
    next_provenance = {key: value["next_state"][key] for key in (
        "session_id", "state_fingerprint", "last_applied_observation_sequence", "observation_id", "turn_number",
    )}
    identity = {
        "decision": value["decision_provenance"], "action": value["executed_action"],
        "next_state": next_provenance, "feature_row": value["decision_feature_row"],
    }
    encoded = json.dumps(identity, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    value["transition_id"] = "offline-transition:" + hashlib.sha256(encoded).hexdigest()
    return _frozen(value)


def test_one_transition_episode_is_readonly_and_terminal_unavailable():
    transition = _run(_attack_case())
    before = _editable(transition)
    episode = materialize_offline_strategy_episode([transition])
    assert episode["status"] == "resolved", episode
    assert episode["transition_ids"] == (transition["transition_id"],)
    assert episode["terminal_status"] == {"availability": "unavailable", "reason": "battle_terminality_not_observed"}
    assert "reward" not in episode and "return" not in episode
    assert _editable(transition) == before
    with pytest.raises(TypeError):
        episode["transitions"][0]["next_state"]["observed_summary"]["battle_terminal"]["availability"] = "available"


@pytest.mark.parametrize("switch", [False, True])
def test_two_real_transitions_sort_and_prove_exact_continuity(switch):
    first, second = _chain(switch=switch)
    episode = materialize_offline_strategy_episode([second, first])
    forward = materialize_offline_strategy_episode([first, second])
    assert episode == forward
    assert episode["status"] == "resolved", episode
    assert episode["transition_ids"] == (first["transition_id"], second["transition_id"])
    assert episode["continuity_gaps"] == ()
    assert first["next_state"]["state_fingerprint"] == second["decision_provenance"]["source_runtime_fingerprint"]
    if switch:
        assert episode["final_next_state"]["turn_number"] == 5
        assert second["next_state"]["observed_summary"]["decision_side_active_owner"]["value"]["pokemon_id"] == "raichu"


def test_dataset_orders_isolated_sessions_and_is_readonly():
    first = materialize_offline_strategy_episode([_run(_attack_case())])
    second = materialize_offline_strategy_episode([_run(_switch_case())])
    dataset = materialize_offline_strategy_dataset([first, second])
    assert dataset["status"] == "resolved", dataset
    assert dataset == materialize_offline_strategy_dataset([second, first])
    assert tuple(row["session_id"] for row in dataset["episodes"]) == ("replay", "s")
    assert "reward" not in dataset
    with pytest.raises(TypeError):
        dataset["episodes"][0]["session_id"] = "foreign"


def test_real_intervening_observation_stays_explicitly_incomplete():
    first, second = _chain(gap=True)
    assert second["decision_provenance"]["last_applied_observation_sequence"] > first["next_state"]["last_applied_observation_sequence"]
    episode = materialize_offline_strategy_episode([second, first])
    assert episode["status"] == "incomplete", episode
    assert episode["completeness"] == "intermediate_state_lineage_unavailable"
    assert episode["continuity_gaps"] == (1,)
    assert materialize_offline_strategy_dataset([episode])["reason"] == "episode_incomplete"


def test_duplicates_and_mixed_sessions_fail_closed():
    first, second = _chain()
    foreign = _run(_attack_case())
    assert materialize_offline_strategy_episode([first, foreign])["reason"] == "mixed_session"
    assert materialize_offline_strategy_episode([first, first])["reason"] == "duplicate_transition_id"
    bad = _editable(second)
    bad["executed_action"]["observation_id"] = first["executed_action"]["observation_id"]
    assert materialize_offline_strategy_episode([first, bad])["status"] == "rejected"
    one = materialize_offline_strategy_episode([first])
    assert materialize_offline_strategy_dataset([one, one])["reason"] == "duplicate_episode_id"
    two = materialize_offline_strategy_episode([first, second])
    assert materialize_offline_strategy_dataset([one, two])["reason"] == "duplicate_transition_across_episodes"
    other = materialize_offline_strategy_episode([second])
    assert materialize_offline_strategy_dataset([one, other])["reason"] == "session_not_isolated"


def test_duplicate_execution_and_conflicting_decision_provenance_fail_closed():
    first, second = _chain()
    duplicate_observation = _corrupted_record(second, lambda row: row["executed_action"].update(
        observation_id=first["executed_action"]["observation_id"],
    ))
    assert materialize_offline_strategy_episode([first, duplicate_observation])["reason"] == "duplicate_executed_observation"

    def same_decision(row):
        row["decision_provenance"] = _editable(first["decision_provenance"])
        row["decision_feature_row"]["provenance"] = _editable(first["decision_feature_row"]["provenance"])
        row["executed_action"]["turn_number"] = first["executed_action"]["turn_number"]

    conflicting = _corrupted_record(second, same_decision)
    assert materialize_offline_strategy_episode([first, conflicting])["reason"] == "conflicting_decision_provenance"


@pytest.mark.parametrize("path,value", [
    (("schema_version",), "foreign"),
    (("status",), "incomplete"),
    (("decision_provenance", "decision_owner", "side"), "opponent"),
    (("decision_provenance", "source_runtime_fingerprint"), "0" * 64),
    (("decision_provenance", "source_branch_fingerprint"), "0" * 64),
    (("executed_action", "candidate_id"), "attack:foreign"),
    (("next_state", "state_fingerprint"), "0" * 64),
    (("next_state", "observed_summary", "battle_terminal", "availability"), "available"),
])
def test_malformed_or_foreign_transition_rejected(path, value):
    record = _editable(_run(_attack_case()))
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert materialize_offline_strategy_episode([record])["status"] == "rejected"


def test_incomplete_transition_rejected():
    kwargs = _attack_case()
    kwargs["historical_binding"] = None
    assert materialize_offline_strategy_episode([_run(kwargs)])["reason"] == "transition_invalid_or_incomplete"


def test_temporal_overlap_and_broken_continuity_rejected():
    first, second = _chain()
    overlap = _corrupted_record(second, lambda row: row["decision_provenance"].update(
        last_applied_observation_sequence=first["next_state"]["last_applied_observation_sequence"] - 1,
    ))
    assert materialize_offline_strategy_episode([first, overlap])["reason"] == "overlapping_temporal_windows"

    def wrong_fingerprint(row):
        row["decision_provenance"]["source_runtime_fingerprint"] = "0" * 64
        row["decision_feature_row"]["provenance"]["source_runtime_fingerprint"] = "0" * 64

    broken = _corrupted_record(second, wrong_fingerprint)
    assert materialize_offline_strategy_episode([first, broken])["reason"] == "broken_state_continuity"
    foreign_owner = _corrupted_record(first, lambda row: row["next_state"]["observed_summary"]["decision_side_active_owner"]["value"].update(pokemon_id="foreign"))
    assert materialize_offline_strategy_episode([foreign_owner, second])["reason"] == "foreign_owner_lineage"


def test_dataset_rejects_nonmaterialized_episode():
    assert materialize_offline_strategy_dataset([{"schema_version": "offline-strategy-episode-v1", "status": "resolved"}])["reason"] == "episode_schema_invalid"
