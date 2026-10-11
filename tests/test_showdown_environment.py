"""Real offline native training episodes; no provider or battle server."""
from copy import deepcopy
import os
from concurrent.futures import ThreadPoolExecutor
import random

import pytest
from advisor.showdown_environment import ShowdownEnvironment, ShowdownEnvironmentError
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_showdown_simulation import simulate_detached_showdown
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios


@pytest.fixture
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker:
        yield worker


def policy(observation, rng):
    legal = [i for i, allowed in enumerate(observation["action_mask"]) if allowed]
    moves = [i for i in legal if 6 <= i < 14]
    return rng.choice(moves or legal)


def joint(env, rng):
    observations = {s: env.observation(s) for s in ("self", "opponent")}
    return {s: policy(o, rng) for s, o in observations.items()}, observations["self"]["revision"]


def scrub(observation):
    observation = deepcopy(observation)
    observation.pop("episode_id")
    return observation


def test_reset_partial_information_isolation_and_request_masks(worker):
    scenario = fixture_scenarios()[0]
    original = deepcopy(scenario)
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(scenario)
        obs = env.observation("self")
        own = obs["state"]["self_side"]
        other = obs["state"]["opponent_side"]
        assert len(own["preview"]) == len(other["preview"]) == 6
        active = other["pokemon"][other["active_identity"]]
        assert active["known_item"] == active["current_ability"] == active["max_hp"] == {"knowledge": "unknown"}
        assert active["known_moves"] == [] and active["hp_fraction"] == 1
        assert obs["action_mask"][:10] == [0, 1, 1, 0, 0, 0, 1, 1, 1, 0]
        assert not any(obs["action_mask"][10:])
        assert all(key not in obs for key in ("native_state", "seed", "assumptions", "checkpoint", "queue"))
        obs["own_request"].clear()
        assert env.observation("self")["own_request"]
    assert scenario == original


def test_distinct_hidden_items_moves_stats_and_seeds_do_not_change_initial_policy_view(worker):
    with ShowdownEnvironment(worker=worker) as env:
        scenario = fixture_scenarios()[0]
        for team in scenario["teams"].values():
            for pokemon in team:
                pokemon["gender"] = "N" if pokemon["species"] == "Rotom-Wash" else "M"
        env.reset(scenario)
        baseline = scrub(env.observation("self"))
        changed = deepcopy(scenario)
        changed["teams"]["opponent"][0]["item"] = "Choice Scarf"
        changed["teams"]["opponent"][0]["moves"] = ["U-turn", "Iron Head"]
        changed["teams"]["opponent"][0]["evs"] = {"hp": 32, "atk": 32, "spd": 2}
        env.reset(changed, seed=[600, 500, 400, 300])
        assert scrub(env.observation("self")) == baseline


def test_faint_replacement_reward_and_wait_action(worker):
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(fixture_scenarios()[0])
        step = env.step({"self": 6, "opponent": 6}, revision=0)
        assert step["rewards"] == {"self": 0, "opponent": 0}
        own, other = env.observation("self"), env.observation("opponent")
        assert own["action_mask"][26] == 1 and sum(own["action_mask"]) == 1
        assert other["request_state"] == "switch" and sum(other["action_mask"]) == 2
        assert other["action_mask"][1] == other["action_mask"][2] == 1
        before = env.save()
        with pytest.raises(ShowdownEnvironmentError, match="masked_or_invalid_action"):
            env.step({"self": 6, "opponent": 1}, revision=step["revision"])
        assert env.save() == before
        env.step({"self": 26, "opponent": 1}, revision=step["revision"])
        assert env.observation("opponent")["request_state"] == "move"


@pytest.mark.parametrize("seed", [[1, 2, 3, 4], [13, 19, 23, 29], [0, 0, 0, 0]])
def test_complete_automated_battle_rewards_and_reset(worker, seed):
    with ShowdownEnvironment(worker=worker, max_decisions=256) as env:
        env.reset(fixture_scenarios()[0], seed=seed)
        rng, trace = random.Random(7), []
        while True:
            actions, revision = joint(env, rng)
            step = env.step(actions, revision=revision)
            trace.append(step)
            assert step["rewards"]["self"] == -step["rewards"]["opponent"]
            if step["terminated"] or step["truncated"]:
                break
        assert step["terminated"] and not step["truncated"]
        assert step["rewards"]["self"] == (1 if step["winner"] == "self" else -1 if step["winner"] == "opponent" else 0)
        assert not any(env.observation("self")["action_mask"])
        with pytest.raises(ShowdownEnvironmentError, match="episode_finished"):
            env.step(actions, revision=step["revision"])
        env.reset(fixture_scenarios()[0], seed=seed)
        rng = random.Random(7)
        again = []
        while len(again) < len(trace):
            actions, revision = joint(env, rng)
            again.append(env.step(actions, revision=revision))
        assert again == trace


def test_sparse_truncation_is_not_terminal_loss(worker):
    with ShowdownEnvironment(worker=worker, max_decisions=1) as env:
        env.reset(fixture_scenarios()[0])
        step = env.step({"self": 8, "opponent": 8}, revision=0)
        assert step["truncated"] and not step["terminated"] and step["winner"] is None
        assert step["rewards"] == {"self": 0, "opponent": 0}


def test_checkpoint_fork_native_rng_and_observation_continuity(worker):
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(fixture_scenarios()[1])
        env.step({"self": 7, "opponent": 6}, revision=0)
        saved, observed = env.save(), scrub(env.observation("self"))
        with env.fork() as fork:
            other = scrub(fork.observation("self"))
            other["revision"] = observed["revision"]
            other["events"] = observed["events"]  # restart re-emits the accumulated public history
            assert other == observed
            assert fork.save() == saved
            rng = random.Random(0)
            for _ in range(5):
                actions, revision = joint(env, rng)
                source = env.step(actions, revision=revision)
                branch = fork.step(actions, revision=fork.observation("self")["revision"])
                assert {k: v for k, v in source.items() if k != "revision"} == {k: v for k, v in branch.items() if k != "revision"}
                assert env.save() == fork.save()


def test_corrupted_checkpoint_and_stale_action_fail_closed(worker):
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(fixture_scenarios()[0])
        cp = env.save()
        cp["native_state"]["turn"] += 1
        with ShowdownEnvironment(worker=worker) as other:
            with pytest.raises(ShowdownEnvironmentError, match="integrity"):
                other.restart(cp)
        env.step({"self": 8, "opponent": 8}, revision=0)
        before = env.save()
        with pytest.raises(ShowdownEnvironmentError, match="stale_episode_revision"):
            env.step({"self": 8, "opponent": 8}, revision=0)
        assert env.save() == before


def test_process_loss_requires_explicit_saved_restart(worker):
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(fixture_scenarios()[0])
        cp = env.save()
        worker._process.kill()
        worker._process.wait()
        with pytest.raises(ShowdownEnvironmentError, match="process_lost"):
            env.observation("self")
        with pytest.raises(ShowdownEnvironmentError, match="restore_saved_checkpoint"):
            env.step({"self": 6, "opponent": 6}, revision=0)
        env.restart(cp)
        env.step({"self": 6, "opponent": 6}, revision=0)


@pytest.mark.parametrize("mutation", [
    lambda row: row["observations"]["self"].update(native_state={"opponent_hidden_item": "secret"}),
    lambda row: row["observations"]["self"]["own_request"]["side"].update(id="p2"),
    lambda row: row["rewards"].update(self=1, opponent=-1),
])
def test_unexpected_hidden_truth_private_owner_or_reward_fails_closed(worker, monkeypatch, mutation):
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(fixture_scenarios()[0])
        original_run = worker.run
        def changed(request):
            result = original_run(request)
            if request["requests"][0]["operation"] == "step":
                mutation(result["results"][0])
            return result
        monkeypatch.setattr(worker, "run", changed)
        with pytest.raises(ShowdownEnvironmentError, match="restore_saved_checkpoint"):
            env.step({"self": 8, "opponent": 8}, revision=0)
        with pytest.raises(ShowdownEnvironmentError):
            env.observation("self")
        assert env.resources["episodes"] == 0


def test_response_revision_mismatch_destroys_worker_and_observations(worker, monkeypatch):
    from advisor.showdown_bridge import ShowdownBridgeError
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(fixture_scenarios()[0])
        original_validate = worker._validate_response
        def changed(request, response):
            response["results"][0]["revision"] += 1
            return original_validate(request, response)
        monkeypatch.setattr(worker, "_validate_response", changed)
        with pytest.raises(ShowdownBridgeError, match="revision_mismatch"):
            env.step({"self": 8, "opponent": 8}, revision=0)
        assert not worker.is_alive
        with pytest.raises(ShowdownEnvironmentError):
            env.observation("self")


@pytest.mark.parametrize("reason", ["native_execution_failed_restore_saved_checkpoint",
    "native_request_retry_limit_restore_saved_checkpoint", "native_environment_failed"])
def test_destroyed_native_episode_never_returns_cached_policy_view(worker, monkeypatch, reason):
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(fixture_scenarios()[0])
        saved = env.save()
        original_run = worker.run
        def failed(request):
            if request["requests"][0]["operation"] == "step":
                return {"results": [{"status": "rejected", "owner": env._owner, "reason": reason}],
                        "resources": {"episodes": 1, "rss_bytes": 0, "heap_used_bytes": 0}}
            return original_run(request)
        monkeypatch.setattr(worker, "run", failed)
        with pytest.raises(ShowdownEnvironmentError, match=reason):
            env.step({"self": 8, "opponent": 8}, revision=0)
        with pytest.raises(ShowdownEnvironmentError):
            env.observation("self")
        assert env.resources["episodes"] == 0
        env.restart(saved)
        assert env.observation("self")["revision"] == 0


def test_native_execution_exception_destroys_only_failed_episode(worker):
    import json
    import subprocess
    from pathlib import Path
    script = """
const {loadEngine}=require('./tools/showdown_bridge/engine.cjs');
const {createEnvironmentService}=require('./tools/showdown_bridge/environment.cjs');
const engine=loadEngine(process.argv[1]);
const run=createEnvironmentService(engine);
const scenario=JSON.parse(require('fs').readFileSync(0,'utf8'));
const owners=['a'.repeat(32),'b'.repeat(32)];
const call=requests=>run({schema_version:'showdown-environment-v1',format_id:'gen9championsbssregmc',requests});
call(owners.map(owner=>({operation:'reset',owner,scenario,max_decisions:512})));
const commit=engine.Battle.prototype.commitChoices;
engine.Battle.prototype.commitChoices=function(){throw new Error('injected engine failure')};
const failed=call([{operation:'step',owner:owners[0],revision:0,actions:{self:8,opponent:8}}]);
engine.Battle.prototype.commitChoices=commit;
const intact=call([{operation:'step',owner:owners[1],revision:0,actions:{self:8,opponent:8}}]);
const closed=call([{operation:'close',owner:owners[1],revision:1}]);
process.stdout.write(JSON.stringify({failed,intact,closed}));
"""
    result = subprocess.run(["node", "-e", script, str(worker.checkout)],
        cwd=Path(__file__).resolve().parents[1], input=json.dumps(fixture_scenarios()[0]),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=10)
    rows = json.loads(result.stdout)
    assert rows["failed"]["results"][0]["reason"] == "native_execution_failed_restore_saved_checkpoint"
    assert rows["failed"]["resources"]["episodes"] == 1
    assert rows["intact"]["results"][0]["decisions"] == 1
    assert rows["closed"]["resources"]["episodes"] == 0


def test_shared_process_restart_invalidates_other_episode_policy_cache(worker):
    with ShowdownEnvironment(worker=worker) as a, ShowdownEnvironment(worker=worker) as b:
        a.reset(fixture_scenarios()[0])
        b.reset(fixture_scenarios()[0])
        saved = a.save()
        worker.close()
        a.restart(saved)
        with pytest.raises(ShowdownEnvironmentError, match="process_lost"):
            b.observation("self")


def test_bounded_training_readiness_smoke(worker):
    from scripts.verify_showdown_training import verify
    report = verify(worker.checkout, episodes=8, workers=2, lanes=2)
    assert report["terminal_episodes"] == 8 and report["truncated"] == 0
    assert report["requests_by_phase"]["switch"] > 0
    assert report["processes_closed"] == report["checkpoint_restart_checked_workers"] == 2


def test_training_steps_match_existing_native_resume_state_at_every_boundary(worker):
    from llm.advisor_showdown_simulation import resume_detached_showdown
    snapshot, scenario = fixture_snapshot(), fixture_scenarios()[1]
    result = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)
    checkpoint = result["scenarios"][0]["root_checkpoint"]
    original = deepcopy(snapshot)
    with ShowdownEnvironment(worker=worker) as env:
        env.from_native_checkpoint(checkpoint)
        rng = random.Random(17)
        for _ in range(16):
            actions, revision = joint(env, rng)
            choices = {side: env.observation(side)["choices"][action] for side, action in actions.items()}
            result = resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=checkpoint, choices=choices, bridge=worker)
            assert result["status"] == "simulated", result
            checkpoint = result["scenarios"][0]["checkpoint"]
            transition = env.step(actions, revision=revision)
            expected = deepcopy(checkpoint["native_state"])
            expected["log"] = ["|t:|0" if line.startswith("|t:|") else line for line in expected["log"]]
            assert env.save()["native_state"] == expected
            if transition["terminated"]:
                break
    assert snapshot == original


def test_shared_worker_batch_processes_success_after_independent_failure(worker):
    with ShowdownEnvironment(worker=worker) as a, ShowdownEnvironment(worker=worker) as b:
        a.reset(fixture_scenarios()[0])
        b.reset(fixture_scenarios()[0])
        rows = ShowdownEnvironment.batch_step([(a, {"self": 0, "opponent": 6}, 0), (b, {"self": 6, "opponent": 6}, 0)])
        assert isinstance(rows[0], ShowdownEnvironmentError)
        assert rows[1]["decisions"] == 1
        assert a.observation("self")["revision"] == 0
        assert b.observation("self")["revision"] == 1


def test_concurrent_episodes_do_not_share_state(worker):
    def play(index):
        with ShowdownEnvironment(worker=worker) as env:
            env.reset(fixture_scenarios()[index % 4])
            env.step({"self": 6, "opponent": 6}, revision=0)
            return env.observation("self")
    with ThreadPoolExecutor(4) as pool:
        views = list(pool.map(play, range(8)))
    assert len({v["episode_id"] for v in views}) == 8
    assert worker._process.poll() is None


def test_imports_existing_detached_pivot_checkpoint_without_truth_writes(worker):
    snapshot, scenario = fixture_snapshot(), fixture_scenarios()[0]
    original = deepcopy(snapshot)
    result = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)
    checkpoint = result["scenarios"][0]["checkpoint"]
    with ShowdownEnvironment(worker=worker) as env:
        env.from_native_checkpoint(checkpoint)
        assert env.observation("self")["action_mask"][26] == 1
        env.step({"self": 26, "opponent": 1}, revision=0)
    assert snapshot == original


def test_pivot_queue_is_hidden_and_preserved_across_fork(worker):
    scenario = fixture_scenarios()[1]
    scenario["teams"]["self"][0], scenario["teams"]["self"][2] = scenario["teams"]["self"][2], scenario["teams"]["self"][0]
    scenario["teams"]["self"][0]["moves"] = ["Volt Switch", "Protect"]
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(scenario)
        env.step({"self": 6, "opponent": 7}, revision=0)
        observation = env.observation("self")
        opposing = observation["state"]["opponent_side"]
        assert opposing["pokemon"][opposing["active_identity"]]["known_moves"] == []
        assert observation["request_state"] == "switch"
        assert observation["action_mask"][1] == 1
        saved = env.save()
        assert saved["native_state"]["queue"]  # privileged only
        with env.fork() as branch:
            env.step({"self": 1, "opponent": 26}, revision=1)
            branch.step({"self": 1, "opponent": 26}, revision=0)
            assert env.save() == branch.save()
            observation = env.observation("self")
            opposing = observation["state"]["opponent_side"]
            assert opposing["pokemon"][opposing["active_identity"]]["known_moves"] == ["swordsdance"]
            assert opposing["pokemon"][opposing["active_identity"]]["stat_stages"]["atk"] == 2


def test_mega_and_weather_requests_reuse_native_mechanics(worker):
    scenario = fixture_scenarios()[0]
    scenario["teams"]["self"][0]["item"] = "Charizardite X"
    scenario["preview"]["self"] = [1, 4, 2]
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(scenario)
        assert env.observation("self")["action_mask"][10] == 1
        env.step({"self": 10, "opponent": 8}, revision=0)
        own = env.observation("self")["own_request"]["side"]["pokemon"][0]
        assert "Charizard-Mega-X" in own["details"] and own["ability"] == "toughclaws"
        opponent_view = env.observation("opponent")["state"]["opponent_side"]
        assert opponent_view["pokemon"][opponent_view["active_identity"]]["known_item"] == "charizarditex"
        env.step({"self": 1, "opponent": 7}, revision=1)
        assert env.observation("self")["state"]["field"]["weather"] == "sandstorm"
        assert any("Sand Stream" in line for line in env.observation("self")["events"])


def test_burn_residual_and_native_public_status(worker):
    scenario = fixture_scenarios()[0]
    scenario["teams"]["self"][0]["moves"] = ["Will-O-Wisp", "Protect"]
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(scenario)
        env.step({"self": 6, "opponent": 7}, revision=0)
        other = env.observation("self")["state"]["opponent_side"]
        active = other["pokemon"][other["active_identity"]]
        assert active["condition"] == "brn"
        assert active["status_counter"] == {"knowledge": "unknown"}
        assert any("[from] brn" in line for line in env.observation("self")["events"])


def test_native_uncertain_shadow_tag_rejection_refreshes_mask_without_action_or_reward(worker):
    scenario = fixture_scenarios()[0]
    scenario["teams"]["self"][0] = deepcopy(scenario["teams"]["opponent"][0])
    scenario["teams"]["opponent"][0] = {"species": "Gengar", "ability": "Cursed Body", "item": "Gengarite",
        "level": 50, "moves": ["Shadow Ball", "Protect"], "nature": "Timid", "evs": {"spa": 32, "spe": 32, "hp": 2}}
    scenario["teams"]["opponent"][5] = deepcopy(fixture_scenarios()[0]["teams"]["opponent"][0])
    with ShowdownEnvironment(worker=worker) as env:
        env.reset(scenario)
        env.step({"self": 8, "opponent": 11}, revision=0)
        before = env.observation("self")
        assert before["own_request"]["active"][0]["maybeTrapped"] and before["action_mask"][1]
        saved = env.save()
        rejected = env.step({"self": 1, "opponent": 7}, revision=1)
        assert rejected["action_rejected"] and rejected["decisions"] == 1
        assert rejected["rewards"] == {"self": 0, "opponent": 0}
        refreshed = env.observation("self")
        assert refreshed["turn"] == before["turn"]
        assert refreshed["own_request"]["active"][0]["trapped"] and not any(refreshed["action_mask"][:6])
        assert refreshed["own_request"]["active"][0]["moves"] == before["own_request"]["active"][0]["moves"]
        with env.fork() as branch:
            result = env.step({"self": 6, "opponent": 7}, revision=2)
            other = branch.step({"self": 6, "opponent": 7}, revision=0)
            assert result["decisions"] == other["decisions"] == 2 and not result["action_rejected"]
            assert env.save() == branch.save()
        env.restart(saved)
        assert env.observation("self")["action_mask"][1]


@pytest.mark.parametrize("hp", ["20/100y", "20/100r", "50/100g", "50/100y"])
def test_champions_hp_colour_does_not_crash_or_become_exact_hp(hp):
    from advisor.showdown_observation import project_policy_observation
    raw = {"schema_version": "showdown-policy-observation-v1", "side": "self", "own_request": {},
           "visible_active_health": [{"identity": "p2a: opponent", "condition": hp}]}
    result = project_policy_observation(raw, [])
    active = result["state"]["opponent_side"]["pokemon"]["p2a: opponent"]
    assert active["current_hp"] == active["max_hp"] == {"knowledge": "unknown"}
    assert active["hp_display"] == hp


def test_detached_checkpoint_hp_overlay_visible_without_native_truth_leak(worker):
    snapshot = fixture_snapshot(opponent_hp=100)
    original = deepcopy(snapshot)
    result = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[fixture_scenarios()[0]], bridge=worker)
    with ShowdownEnvironment(worker=worker) as env:
        env.from_native_checkpoint(result["scenarios"][0]["root_checkpoint"])
        other = env.observation("self")["state"]["opponent_side"]
        active = other["pokemon"][other["active_identity"]]
        assert active["hp_display"] == "68/100"
        assert active["current_hp"] == active["max_hp"] == {"knowledge": "unknown"}
    assert snapshot == original


def test_native_destiny_bond_double_faint_uses_native_winner_not_hp_tie(worker):
    from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
    from scripts.verify_showdown_integration import snapshot_from_state
    state = create_unknown_bootstrap_battle_state("native-draw", "gengar", "gengar",
        battle_format={"battle_format": "singles", "source": "user_confirmed_battle_format"})["state"]
    scenario = fixture_scenarios()[0]
    scenario["teams"]["self"][0] = {"species": "Gengar", "ability": "Cursed Body", "level": 50,
        "moves": ["Destiny Bond"], "nature": "Timid", "evs": {"spa": 32, "spe": 32, "hp": 2}}
    scenario["teams"]["self"][5] = deepcopy(fixture_scenarios()[0]["teams"]["self"][0])
    scenario["teams"]["opponent"][0] = {"species": "Gengar", "ability": "Cursed Body", "level": 50,
        "moves": ["Night Shade"], "nature": "Quiet", "evs": {"spa": 32, "hp": 32, "def": 2}}
    scenario["teams"]["opponent"][5] = deepcopy(fixture_scenarios()[0]["teams"]["opponent"][0])
    scenario["hypothetical_active_hp"] = {"self": 50, "opponent": 50}
    scenario["initial_conditioning"] = [{"effect": "faint", "target": side, "slot_index": slot}
        for side in ("self", "opponent") for slot in (1, 2)]
    result = simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=[scenario], bridge=worker)
    assert result["status"] == "simulated", result.get("scenarios", result)
    assert result["scenarios"][0]["after"]["ended"]
    with ShowdownEnvironment(worker=worker) as env:
        step = env.from_native_checkpoint(result["scenarios"][0]["checkpoint"])
        assert step["terminated"] and not step["truncated"] and step["winner"] == "opponent"
        assert step["rewards"] == {"self": -1, "opponent": 1}


def test_visible_trapped_mask_and_native_struggle_from_exhausted_pp(worker):
    scenario = fixture_scenarios()[0]
    scenario["teams"]["self"][0]["moves"] = ["Flamethrower"]
    scenario["conditioning"] = [{"target": "self", "effect": "volatile", "id": "ingrain"}]
    result = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=[scenario], bridge=worker)
    assert result["status"] == "simulated", result
    with ShowdownEnvironment(worker=worker) as env:
        env.from_native_checkpoint(result["scenarios"][0]["root_checkpoint"])
        assert not any(env.observation("self")["action_mask"][:6])
    # Exhausted PP is authoritative observation, reconciled by the existing adapter.
    from scripts.verify_showdown_integration import snapshot_from_state
    state = fixture_snapshot()["state"]
    moves = ["flamethrower", "air-slash", "protect", "dragon-pulse"]
    scenario["teams"]["self"][0]["moves"] = moves
    scenario.pop("conditioning")
    native = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=[scenario], bridge=worker)
    limits = [m["max_pp"] for m in native["scenarios"][0]["before"]["sides"]["self"]["pokemon"][0]["moves"]]
    state["self_side"]["pokemon"][0]["known_move_ids"] = moves
    state["self_side"]["pokemon"][0]["current_opponent_response_set"] = {"moveset_completeness": "complete", "move_ids": moves,
        "provenance": {"event_kind": "current_opponent_response_set_observed", "trust": "user_confirmed_observation", "turn_number": 1, "source_sequence": 1},
        "move_pp_slots": [{"slot_index": i, "move_id": move, "current_pp": 0, "max_pp": maximum}
            for i, (move, maximum) in enumerate(zip(moves, limits))]}
    result = simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=[scenario], bridge=worker)
    assert result["status"] == "simulated", result.get("scenarios", result)
    with ShowdownEnvironment(worker=worker) as env:
        env.from_native_checkpoint(result["scenarios"][0]["root_checkpoint"])
        request = env.observation("self")["own_request"]
        assert request["active"][0]["moves"][0]["id"] == "struggle"
        assert env.observation("self")["action_mask"][6] == 1


def test_explicit_native_tie_has_zero_terminal_reward(worker):
    import json
    import subprocess
    from llm.advisor_showdown_simulation import _checkpoint_fingerprint
    result = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=[fixture_scenarios()[0]], bridge=worker)
    checkpoint = result["scenarios"][0]["root_checkpoint"]
    # Reuse the actual native terminal transition, not a fabricated winner field.
    script = "const fs=require('fs');const {Battle}=require(process.argv[1]+'/dist/sim');const cp=JSON.parse(fs.readFileSync(0,'utf8'));const b=Battle.fromJSON(cp.native_state);b.restart(()=>{});b.tie();cp.native_state=b.toJSON();b.destroy();process.stdout.write(JSON.stringify(cp));"
    native = subprocess.run(["node", "-e", script, str(worker.checkout)], input=json.dumps(checkpoint),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=10)
    checkpoint = json.loads(native.stdout)
    checkpoint.pop("checkpoint_fingerprint")
    checkpoint["checkpoint_fingerprint"] = _checkpoint_fingerprint(checkpoint)
    with ShowdownEnvironment(worker=worker) as env:
        step = env.from_native_checkpoint(checkpoint)
        assert step["terminated"] and not step["truncated"] and step["winner"] is None
        assert step["rewards"] == {"self": 0, "opponent": 0}


@pytest.mark.parametrize("mutate", [lambda s: s["teams"]["self"][0].update(item="Heavy-Duty Boots"),
    lambda s: s["preview"]["self"].append(4), lambda s: s.update(history=[s["choices"]]),
    lambda s: s.update(seed=[True, 2, 3, 4])])
def test_native_legality_and_reset_boundary_fail_closed(worker, mutate):
    scenario = fixture_scenarios()[0]
    mutate(scenario)
    with ShowdownEnvironment(worker=worker) as env:
        with pytest.raises(ShowdownEnvironmentError):
            env.reset(scenario)
