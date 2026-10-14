from copy import deepcopy
import os
from types import SimpleNamespace
import pytest

pytest.importorskip("poke_env")
from advisor.learned_failure_opponent import PublicFailureAwareOpponent, VERSION, established_failures
from advisor.learned_baselines import VisibleBaseline
from advisor.showdown_environment import ShowdownEnvironment
from scripts.verify_showdown_integration import fixture_scenarios


def failure_fixture(kind):
    s = fixture_scenarios()[0]
    for team in s["teams"].values():
        for p in team:
            p["gender"] = "N" if p["species"] == "Rotom-Wash" else "M"
    if kind == "heal":
        p = {"species": "Toxapex", "ability": "Merciless", "moves": ["Recover", "Haze"]}
    elif kind == "fling":
        p = {"species": "Drampa", "ability": "Cloud Nine", "moves": ["Fling", "Sunny Day"]}
    else:
        p = {"species": "Whimsicott", "ability": "Infiltrator", "moves": ["Snore", "Grassy Terrain"]}
    s["teams"]["self"][0] = {**p, "item": "", "level": 50, "gender": "M", "nature": "Hardy", "evs": {"hp": 32, "atk": 32, "spd": 2}}
    return s


def run_native_sanity(checkout, kind, aware, seed=(1, 2, 3, 4)):
    s = failure_fixture(kind);s["seed"] = list(seed)
    player = PublicFailureAwareOpponent(21) if aware else VisibleBaseline("max_power", 21)
    rows = []
    with ShowdownEnvironment(checkout) as env:
        env.reset(s)
        for _ in range(4):
            view = env.observation("self", include_history=True)
            before = deepcopy(view);action = player.act(view)
            assert view == before and view["action_mask"][action]
            transition = env.step({"self": action, "opponent": 7}, revision=view["revision"])
            events = env.observation("self", include_history=True)["public_history"][len(view["public_history"]):]
            rows.append({"action": action, "choice": view["choices"][action], "guards": established_failures(view),
                         "failures": sum(l.startswith("|-fail|p1") for l in events), "events": events,
                         "rejected": transition["action_rejected"]})
    return rows


@pytest.mark.parametrize("kind", ["snore", "heal", "fling"])
def test_native_public_failures_change_only_new_opponent(kind):
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:pytest.skip("pinned native engine required")
    original = run_native_sanity(checkout, kind, False)
    aware = run_native_sanity(checkout, kind, True)
    assert [r["action"] for r in original] == [6, 6, 6, 6]
    assert [r["action"] for r in aware] == [6, 6, 7, 7]
    assert len([r for r in aware if r["action"]==6 and r["failures"]]) < len([r for r in original if r["action"]==6 and r["failures"]])
    assert not any(r["rejected"] for r in original + aware)


def public_view(move="Snore", fail="generic", repeats=2):
    actor="p1a: own"
    history=[]
    for _ in range(repeats):
        history += [f"|move|{actor}|{move}|p2a: other", f"|-fail|{actor}" + (f"|{fail}" if fail != "generic" else "")]
    return {"state":{"self_side":{"active_identity":actor,"pokemon":{actor:{"hp_fraction":1,"condition":None,"known_item":None,"current_ability":"thickfat"}}}},"public_history":history}


def test_insufficient_or_changed_public_evidence_never_blocks():
    assert established_failures(public_view(repeats=1)) == {}
    for field,value in [("condition","slp"),("current_ability","comatose"),("current_ability",{"knowledge":"unknown"}),("condition",{"knowledge":"unknown"})]:
        v=public_view();v["state"]["self_side"]["pokemon"]["p1a: own"][field]=value
        assert established_failures(v)=={}
    v=public_view("Recover","heal");v["state"]["self_side"]["pokemon"]["p1a: own"]["hp_fraction"]=.5
    assert established_failures(v)=={}
    v=public_view("Fling");v["state"]["self_side"]["pokemon"]["p1a: own"]["known_item"]={"knowledge":"unknown"}
    assert established_failures(v)=={}
    for history in [["|move|p1a: own|Focus Blast|p2a: other|[miss]","|-miss|p1a: own|p2a: other"]*2,
                    ["|move|p1a: own|Thunderbolt|p2a: other","|-immune|p2a: other"]*2]:
        v=public_view();v["public_history"]=history
        assert established_failures(v)=={}
    v=public_view();v["public_history"] += ["|switch|p1a: own|Snorlax, L50|100/100"]
    assert established_failures(v)=={}
    v=public_view();v["public_history"] += ["|-damage|p1a: own|50/100"]
    assert established_failures(v)  # Damage does not make awake Snore usable.
    v=public_view("Recover","heal");v["public_history"] += ["|-damage|p1a: own|50/100", "|-heal|p1a: own|100/100"]
    assert established_failures(v)=={}  # Stale full-HP failures are invalidated.
    assert established_failures(public_view("Sleep Talk"))
    v=public_view("Fling");v["state"]["self_side"]["pokemon"]["p1a: own"]["known_item"]="blazikenite"
    assert established_failures(v)


def test_no_opponent_unknown_information_consulted():
    v=public_view();v["state"]["opponent_side"]={"hidden_test":"A"}
    expected=established_failures(v);v["state"]["opponent_side"]={"hidden_test":"B"}
    assert established_failures(v)==expected


def test_frozen_base_only_overridden_after_established_failures():
    v=public_view(repeats=0)
    v.update(episode_id="public",revision=0,request_state="move",side="self",
             own_request={"active":[{"moves":[{"id":"snore"},{"id":"grassyterrain"}]}]},
             action_mask=[0]*35,choices=[None]*35)
    for i in (6,7):v["action_mask"][i]=1;v["choices"][i]=f"move {i-5}"
    frozen=SimpleNamespace(act=lambda _:6,model_id="immutable-frozen")
    player=PublicFailureAwareOpponent(base=frozen)
    before=deepcopy(v);assert player.act(v)==6 and before==v
    v["public_history"]=public_view()["public_history"];v["revision"]=1
    before=deepcopy(v);assert player.act(v)==7 and before==v
    assert frozen.act(v)==6 and "immutable-frozen" in player.model_id
    v["action_mask"][7]=0;v["choices"][7]=None;v["revision"]=2
    assert player.act(v)==6  # Never invent a legal fallback or alter the native mask.


def test_trainer_new_identifier_is_opt_in():
    from scripts.train_showdown_autonomous import validate_config
    c={"schema_version":"showdown-autonomous-training-v1","max_runtime_seconds":60,
       "experiments":[{"seed":1,"steps":1024,"opponents":[VERSION]}]}
    validate_config(c)
    with pytest.raises(ValueError,match="invalid_baseline"):VisibleBaseline(VERSION)


def test_wait_loop_retries_are_counted_without_info_or_reward_change():
    from advisor.learned_gym import ShowdownLearningEnv
    # Focused adapter path: primary action -> wait retry -> completed continuation.
    env=object.__new__(ShowdownLearningEnv)
    view={"episode_id":"owned","revision":0,"side":"self","request_state":"move",
          "own_request":{},"action_mask":[0]*35,"choices":[None]*35,"public_history":[],"state":{}}
    view["action_mask"][6]=1;view["choices"][6]="move 1"
    env.current=deepcopy(view);env._episode_identity={"case_index":12};env._rejected_choices=0
    env.retry_diagnostics=[];env.collect_tactical_metrics=False;env.opponent=SimpleNamespace(act=lambda _:26)
    env.encoder=SimpleNamespace(encode=lambda _: [0.0]);env.completed=[];env.opponent_kind="max_power"
    cursor=[0]
    def step(actions,revision):
        cursor[0]+=1;env.current["revision"]=cursor[0]
        env.current["action_mask"]=[0]*35;env.current["action_mask"][26]=1;env.current["choices"]=[None]*35;env.current["choices"][26]=""
        return {"revision":cursor[0],"decisions":1 if cursor[0]<3 else 2,"terminated":cursor[0]==3,
                "truncated":False,"winner":"self" if cursor[0]==3 else None,"rewards":{"self":1 if cursor[0]==3 else 0,"opponent":-1 if cursor[0]==3 else 0},"action_rejected":cursor[0]==2}
    env.native=SimpleNamespace(step=step,observation=lambda *a,**k:deepcopy(env.current))
    _,reward,ended,truncated,info=env.step(6)
    assert ended and not truncated and reward==1
    assert env._rejected_choices==1 and len(env.retry_diagnostics)==1
    assert env.completed[0]["native_rejected_choices"]==1
    assert "before" not in info and "opponent" not in info


def test_native_simple_beam_reveals_real_ability_outside_frozen_v2_catalog():
    checkout=os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:pytest.skip("pinned native engine required")
    from pathlib import Path
    from advisor.learned_public_categories import RequestIdentityCategoricalEncoder
    s=fixture_scenarios()[0]
    s["teams"]["self"][0]={"species":"Audino","ability":"Klutz","moves":["Simple Beam","Thunder"],
        "gender":"M","level":50,"nature":"Hardy","evs":{"hp":32,"spa":32,"spd":2}}
    encoder=RequestIdentityCategoricalEncoder(Path(__file__).resolve().parents[1]/"models/showdown_mc_domain_v1/catalog.json")
    with ShowdownEnvironment(checkout) as env:
        env.reset(s);view=env.observation("self",include_history=True)
        encoder.encode(view)
        result=env.step({"self":6,"opponent":7},revision=view["revision"])
        assert not result["action_rejected"]
        after=env.observation("self",include_history=True)
        opponent=after["state"]["opponent_side"]
        assert opponent["pokemon"][opponent["active_identity"]]["current_ability"]=="simple"
        assert "simple" not in encoder.tokens["abilities"]
        with pytest.raises(ValueError,match="unsupported_known_public_abilities"):encoder.encode(after)
