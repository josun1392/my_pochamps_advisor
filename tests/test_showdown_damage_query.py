"""Conditional native damage does not become an exact action/KO authority."""
from copy import deepcopy
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_showdown_simulation import evaluate_native_damage_rolls, simulate_detached_showdown, resume_detached_showdown
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios


@pytest.fixture
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker: yield worker


def root(worker, scenario=None):
    scenario = scenario or fixture_scenarios()[1]
    scenario["choices"] = {"self": "move 3", "opponent": "move 3"}
    row = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=[scenario], bridge=worker)["scenarios"][0]
    assert row["status"] == "simulated", row
    return row["root_checkpoint"]


def query(worker, checkpoint, *, move="flamethrower", critical=False):
    return evaluate_native_damage_rolls(runtime_snapshot=fixture_snapshot(), checkpoint=checkpoint, side="self", move=move, critical=critical, bridge=worker)


def test_conditional_native_damage_rolls_preserve_root_and_sash_survival(worker):
    checkpoint = root(worker)
    original = deepcopy(checkpoint)
    result = query(worker, checkpoint)["scenarios"][0]
    assert result["status"] == "simulated", result
    damage = result["damage_rolls"]
    assert damage["schema_version"] == "showdown-native-damage-rolls-v1"
    assert len(damage["rolls"]) == 16 and min(damage["rolls"]) > 147
    assert "damage_application_and_survival" in damage["excludes"]
    assert damage["interpretation"] == "conditional_exact_damage_rolls_not_action_or_ko_probability"
    executed = resume_detached_showdown(runtime_snapshot=fixture_snapshot(), checkpoint=checkpoint,
        choices={"self": "move 1", "opponent": "move 2"}, bridge=worker)["scenarios"][0]
    assert executed["after"]["sides"]["opponent"]["pokemon"][0]["hp"] == 1
    assert checkpoint == original
    assert query(worker, checkpoint)["scenarios"][0]["damage_rolls"] == damage


@pytest.mark.parametrize("move", ["protect", "earthquake", "not-a-move"])
def test_unsupported_or_unlearned_native_damage_query_fails_closed(worker, move):
    assert query(worker, root(worker), move=move)["scenarios"][0]["reason"] == "unsupported_native_damage_query"


def test_conditional_query_rejects_stale_capture_and_counterfeit_checkpoint(worker):
    checkpoint = root(worker)
    changed = fixture_snapshot(hp=100)
    assert evaluate_native_damage_rolls(runtime_snapshot=changed, checkpoint=checkpoint, side="self", move="flamethrower",
        critical=False, bridge=worker)["status"] == "rejected"
    checkpoint["native_state"]["turn"] += 1
    assert query(worker, checkpoint)["status"] == "rejected"


def test_conditional_query_cannot_treat_multi_hit_as_one_hit(worker):
    scenario = fixture_scenarios()[1]
    scenario["teams"]["self"][0]["moves"] = ["Flamethrower", "Scale Shot", "Protect"]
    checkpoint = root(worker, scenario)
    assert query(worker, checkpoint, move="scale-shot")["scenarios"][0]["reason"] == "unsupported_native_damage_query"
