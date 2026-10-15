"""Public recipient/actor distinction from real Heal Pulse failure traces."""
from copy import deepcopy
import os
import pytest
from advisor.learned_public_metrics import PublicDecisionMetrics, public_heal_failure_attribution


@pytest.mark.parametrize("role,other", [("p1","p2"),("p2","p1")])
def test_external_heal_failure_does_not_label_recipient_action(role,other):
    # Actual pinned-native sequence: Will-O-Wisp selected, foe Heal Pulse fails.
    history=[f"|move|{role}a: slot-5|Will-O-Wisp|{other}a: slot-5",
             f"|-status|{other}a: slot-5|brn",
             f"|move|{other}a: slot-5|Heal Pulse|{role}a: slot-5",
             f"|-fail|{role}a: slot-5|heal"]
    r=public_heal_failure_attribution(history,role)
    assert r["recipient_heal_failure_events"]==r["external_heal_failure_events_received"]==1
    assert r["own_executed_recovery_move_failures"]==r["unattributed_heal_failure_events"]==0
    metrics=PublicDecisionMetrics();metrics.outcome({"side":"self" if role=="p1" else "opponent"},history)
    assert metrics.counts["native_heal_fail"]==1  # Historical counter semantics retained.
    assert metrics.counts["own_executed_recovery_move_failures"]==0


def test_only_immediate_executed_moves_are_attributed_and_no_residual_guess():
    direct=["|move|p1a: X|Roost||[still]","|-fail|p1a: X|heal"]
    assert public_heal_failure_attribution(direct)["own_executed_recovery_move_failures"]==1
    called=["|move|p1a: X|Rest|p1a: X|[from] move: Sleep Talk","|-fail|p1a: X|heal"]
    assert public_heal_failure_attribution(called)["own_executed_recovery_move_failures"]==1
    for prefix in (["|upkeep"],["|turn|2"],["|-activate|p1a: X|ability: Unknown"],
                   ["|move|p1a: X|Thunderbolt|p2a: Y"]):
        r=public_heal_failure_attribution(direct[:1]+prefix+direct[1:])
        assert r["unattributed_heal_failure_events"]==1 and r["own_executed_recovery_move_failures"]==0
    with pytest.raises(ValueError):public_heal_failure_attribution(direct,"self")


@pytest.mark.parametrize("role", ["p1","p2"])
def test_native_own_roost_and_opponent_heal_pulse_keep_actor_separate(role):
    checkout=os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:pytest.skip("pinned native checkout required")
    from scripts.verify_showdown_integration import fixture_scenarios
    from advisor.showdown_environment import ShowdownEnvironment
    from scripts.evaluate_showdown_policy import native_heal_failures
    s=deepcopy(fixture_scenarios()[0])
    s["teams"]["self"][0]["moves"]=["Roost","Protect"]
    s["teams"]["opponent"][0].update(species="Slowbro",ability="Oblivious",moves=["Heal Pulse","Protect"],item="")
    if role=="p2":s["teams"]["self"],s["teams"]["opponent"]=s["teams"]["opponent"],s["teams"]["self"]
    owner="self" if role=="p1" else "opponent"
    with ShowdownEnvironment(checkout) as env:
        env.reset(s);view=env.observation(owner,include_history=True)
        before=len(view["public_history"])
        result=env.step({"self":6,"opponent":6},revision=view["revision"])
        events=env.observation(owner,include_history=True)["public_history"][before:]
        assert not result["action_rejected"] and result["rewards"][owner]==0
        r=public_heal_failure_attribution(events,role)
        assert native_heal_failures(events,role)[0]==r["recipient_heal_failure_events"]==2
        assert r["own_executed_recovery_move_failures"]==1
        assert r["external_heal_failure_events_received"]==1
        assert r["unattributed_heal_failure_events"]==0
