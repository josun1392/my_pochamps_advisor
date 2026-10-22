"""Saved public-request fixtures and monitor state only; no PPO or native runs."""
from copy import deepcopy
import json
import pytest

from advisor.learned_training_operations import (
    ProgressRetryMonitor, RetryMonitor, PROGRESS_RETRY_VERSION,
)


def retry(revision, decision=50, case=96123462, episode="saved-native-episode"):
    mask = [0] * 35
    mask[7] = mask[8] = 1
    after = list(mask)
    after[7] = 0
    return {"episode_id": episode, "episode_case": case,
        "revision_before": revision, "revision_after": revision + 1, "native_decisions": decision,
        "before": {"opponent": {"action_index": 7, "action_mask": mask,
            "phase": "move", "maybeDisabled": True, "trapped": None}},
        "after": {"opponent": {"action_index": 7, "action_mask": after,
            "phase": "move", "maybeDisabled": True, "trapped": None}}}


def test_actual_incident_pattern_advances_twelve_points_not_one_stall():
    records = [retry(50 + i * 2, 50 + i) for i in range(12)]
    unchanged = deepcopy(records)
    assert RetryMonitor().inspect(records, [], 32768)[0]["reason"] == "eight_retries_same_episode"
    monitor = ProgressRetryMonitor()
    assert monitor.inspect(records, [], 32768) == []
    entry = next(iter(monitor.pending.values()))
    assert entry["total_rejections"] == 12
    assert entry["consecutive_rejections"] == entry["max_consecutive_rejections"] == 1
    assert entry["accepted_progress_resets"] == 11
    assert records == unchanged


def test_true_unresolved_point_still_stops_at_eight():
    monitor = ProgressRetryMonitor()
    assert not monitor.inspect([retry(50 + i) for i in range(7)], [], 32768)
    alerts = monitor.inspect([retry(57)], [], 32768)
    assert alerts == [{"reason": "eight_retries_without_native_progress",
        "episode": "saved-native-episode:96123462", "native_decisions": 50,
        "count": 8, "episode_total": 8}]


def test_public_request_updates_do_not_fake_accepted_progress():
    records = [retry(50 + i) for i in range(8)]
    for i, record in enumerate(records):
        record["after"]["opponent"].update(trapped=bool(i % 2), maybeTrapped=True)
        record["after"]["opponent"]["action_mask"][8] = i % 2
    assert ProgressRetryMonitor().inspect(records, [], 32768)[0]["reason"] == "eight_retries_without_native_progress"


def test_automatic_wait_loop_rejections_remain_counted_with_authoritative_masks():
    records = [retry(50 + i) for i in range(8)]
    wait_mask = [0] * 35
    wait_mask[26] = 1
    for record in records:
        record["before"]["self"] = {"action_index": 26, "action_mask": list(wait_mask), "wait": True}
    alerts = ProgressRetryMonitor().inspect(records, [], 32768)
    assert [row["reason"] for row in alerts] == ["eight_retries_without_native_progress"]


def test_real_progress_resets_run_but_keeps_total_and_maximum():
    monitor = ProgressRetryMonitor()
    assert not monitor.inspect([retry(i) for i in range(7)], [], 32768)
    assert not monitor.inspect([retry(7, 51)], [], 32768)
    entry = next(iter(monitor.pending.values()))
    assert entry["consecutive_rejections"] == 1 and entry["total_rejections"] == 8
    assert entry["max_consecutive_rejections"] == 7
    assert not monitor.inspect([retry(i, 51) for i in range(8, 14)], [], 32768)
    assert monitor.inspect([retry(14, 51)], [], 32768)[0]["episode_total"] == 15


def test_serialization_and_dedup_preserve_true_stall_across_checkpoints():
    monitor = ProgressRetryMonitor()
    assert not monitor.inspect([retry(i) for i in range(5)], [], 32768)
    restored = ProgressRetryMonitor(json.loads(json.dumps(monitor.pending)))
    assert not restored.inspect([retry(4), retry(5), retry(6)], [], 32768)
    assert restored.inspect([retry(7)], [], 32768)[0]["count"] == 8
    assert next(iter(restored.pending.values()))["total_rejections"] == 8


def test_ended_episode_keeps_explicit_totals_without_pending_stall():
    monitor = ProgressRetryMonitor()
    episodes = [{"episode_identity": {"case_index": 96123462}}]
    assert not monitor.inspect([retry(i, i) for i in range(12)], episodes, 32768)
    assert not monitor.pending
    statistics = monitor.statistics()
    entry = next(iter(statistics["ended_this_checkpoint"].values()))
    assert entry["total_rejections"] == 12 and entry["consecutive_rejections"] == 0
    statistics["ended_this_checkpoint"].clear()
    assert monitor.statistics()["ended_this_checkpoint"]


def test_episode_identity_does_not_merge_unrelated_rejections():
    rows = [retry(i) for i in range(7)] + [retry(0, episode="other-native-episode")]
    monitor = ProgressRetryMonitor()
    assert not monitor.inspect(rows, [], 32768)
    assert len(monitor.pending) == 2


def test_accepted_progress_without_another_failure_resets_at_checkpoint():
    monitor = ProgressRetryMonitor()
    assert not monitor.inspect([retry(i) for i in range(5)], [], 32768)
    cursor = {"episode_identity": {"case_index": 96123462},
              "native_progress": {"episode_id": "saved-native-episode", "native_decisions": 51}}
    assert not monitor.inspect([], [], 32768, progress=[cursor])
    entry = next(iter(monitor.pending.values()))
    assert entry["consecutive_rejections"] == 0 and entry["total_rejections"] == 5
    assert not monitor.inspect([retry(6, 51)], [], 32768)
    assert entry["consecutive_rejections"] == 1


def test_progress_of_another_native_episode_does_not_clear_a_stall():
    monitor = ProgressRetryMonitor()
    monitor.inspect([retry(i) for i in range(7)], [], 32768)
    cursor = {"episode_identity": {"case_index": 96123462},
              "native_progress": {"episode_id": "other-native-episode", "native_decisions": 99}}
    assert not monitor.inspect([], [], 32768, progress=[cursor])
    assert monitor.inspect([retry(7)], [], 32768)[0]["reason"] == "eight_retries_without_native_progress"


def test_native_progress_cursor_is_coordinator_only_read_only():
    from types import SimpleNamespace
    from advisor.learned_gym import ShowdownLearningEnv
    owner = SimpleNamespace(_episode_identity={"case_index": 7}, index=8,
        current={"revision": 10, "request_state": "move", "episode_id": "native-owner"},
        _rejected_choices=3, native=SimpleNamespace(_transition={"decisions": 7}))
    cursor = ShowdownLearningEnv.episode_cursor(owner)
    assert cursor["native_progress"] == {"episode_id": "native-owner", "native_decisions": 7}
    assert "native_progress" not in owner.current
    assert owner.native._transition == {"decisions": 7}


@pytest.mark.parametrize("decision", [None, -1, 1.5, True])
def test_missing_or_invalid_native_progress_fails_closed(decision):
    with pytest.raises(ValueError, match="progress_evidence"):
        ProgressRetryMonitor().inspect([retry(0, decision)], [], 32768)


def test_legacy_pending_cannot_silently_become_new_progress_state():
    with pytest.raises(ValueError, match="state_version"):
        ProgressRetryMonitor({"old": {"case": 1, "revisions": [1, 2, 3]}})
    assert PROGRESS_RETRY_VERSION == "native-decision-progress-retries-v1"


@pytest.mark.parametrize("revision,decision,reason", [(4, 49, "regressed"), (2, 50, "out_of_order"), (3, 51, "duplicate_revision")])
def test_inconsistent_or_regressed_evidence_fails_closed(revision, decision, reason):
    monitor = ProgressRetryMonitor()
    monitor.inspect([retry(3, 50)], [], 32768)
    with pytest.raises(ValueError, match=reason):
        monitor.inspect([retry(revision, decision)], [], 32768)


def test_mask_and_interval_rate_guards_are_preserved():
    assert not ProgressRetryMonitor().inspect([retry(0)], [], 100)
    assert ProgressRetryMonitor().inspect([retry(0), retry(1, 51)], [], 100)[0]["reason"] == "interval_retry_rate_above_one_percent"
    row = retry(0)
    row["before"]["opponent"]["action_mask"][7] = 0
    assert ProgressRetryMonitor().inspect([row], [], 32768)[0]["reason"] == "mask_illegal_retry_choice"


def test_explicit_retry_contract_validation_and_no_legacy_default_change():
    from scripts.train_showdown_autonomous import validate_config
    from tests.test_team_scale_study import configs
    # Unknown monitor contracts fail before other trainer config validation.
    with pytest.raises(ValueError, match="unsupported_retry_monitor_version"):
        validate_config({"retry_monitor_version": "unversioned"})
    assert "retry_monitor_version" not in configs()[0][1]
