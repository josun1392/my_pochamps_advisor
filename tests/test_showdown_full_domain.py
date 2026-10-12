"""Native legal-domain witnesses, reserved partitions and public compatibility."""

from copy import deepcopy
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("poke_env")
pytest.importorskip("sb3_contrib")
from advisor.learned_full_domain import (
    DOMAIN,
    CURRICULUM,
    generate_teams,
    load_inventory,
)
from advisor.learned_native_curriculum import _full_bank
from advisor.learned_scenarios import scenario
from advisor.learned_action_encoder import make_encoder
from advisor.showdown_environment import ShowdownEnvironment
from scripts.verify_showdown_full_domain import witness_case
from scripts.train_showdown_autonomous import validate_config

ROOT = Path(__file__).resolve().parents[1]
CATALOG = DOMAIN / "catalog.json"


@pytest.fixture(scope="module")
def checkout():
    value = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not value:
        pytest.skip("external pinned checkout required")
    return value


def test_domain_authority_form_scope_and_integrity():
    inventory = load_inventory()
    assert len(inventory["base_species"]) == 231
    assert not inventory["random_source"]["missing_bases"]
    assert len(inventory["random_source"]["missing_forms"]) == 54
    assert {p["kind"] for p in inventory["species"].values()} == {
        "selectable",
        "mega",
        "ability_transformation",
    }
    assert (
        "ogerpon" not in inventory["species"]
        and "ogerpontealtera" not in inventory["species"]
    )
    assert (
        inventory["excluded_species"]["ogerpontealtera"]["stage"]
        == "no_legal_start_set"
    )
    assert "squawkabillyyellow" in inventory["species"]
    assert "Sheer Force" in inventory["species"]["squawkabillyyellow"]["abilities"]
    for entry in inventory["species"].values():
        assert len(entry["team_witness_sha256"]) == 64
        assert set(entry["moves"]) == set().union(
            *map(set, entry["moves_by_ability"].values())
        )
    manifest = json.loads((DOMAIN / "manifest.json").read_text())
    assert (
        sha256(gzip.decompress((DOMAIN / "inventory.json.gz").read_bytes())).hexdigest()
        == manifest["content_sha256"]
    )
    assert (
        sha256((DOMAIN / "public_dex.json").read_bytes()).hexdigest()
        == manifest["public_dex_sha256"]
    )


def test_species_forms_and_complete_teams_disjoint_from_historical_finals():
    bank = _full_bank()
    pools = bank["partition_species"]
    assert sorted(map(len, pools.values())) == [12, 12, 39, 168]
    assert set().union(*map(set, pools.values())) == set(
        load_inventory()["base_species"]
    )
    assert all(
        not set(a) & set(b)
        for k, a in pools.items()
        for other_key, b in pools.items()
        if k != other_key
    )
    prior = json.loads(
        (ROOT / "models/showdown_native_curriculum_v6/manifest.json").read_text()
    )
    fresh = json.loads(
        (ROOT / "models/showdown_native_fresh17/manifest.json").read_text()
    )
    assert set(prior["unseen_base_species"]) == set(pools["unseen"])
    assert set(fresh["unseen_base_species"]) <= set(pools["unseen"])
    hashes = [
        sha256(json.dumps(t, sort_keys=True).encode()).hexdigest()
        for teams in bank["teams"].values()
        for t in teams
    ]
    assert len(set(hashes)) == len(hashes)
    original = scenario("train", 9151, version=CURRICULUM)
    altered = deepcopy(original)
    altered["teams"]["self"][0]["item"] = "invalid"
    assert scenario("train", 9151, version=CURRICULUM) == original
    assert scenario("test", 9151, version=CURRICULUM) != original


def test_full_domain_generation_reproducibility_and_native_failure(checkout):
    constraints = [
        {"form": "squawkabillyyellow", "ability": "Sheer Force"},
        {
            "form": "toxtricitylowkey",
            "moves": ["Thunderbolt", "Protect"],
            "nature": "Modest",
            "evs": {"hp": 2, "atk": 0, "def": 0, "spa": 32, "spd": 0, "spe": 32},
        },
        {"form": "vivillonfancy"},
        {"form": "alcremierainbowswirl"},
    ]
    kwargs = {"seed": [1, 3, 5, 7], "count": 4, "constraints": constraints}
    first = generate_teams(checkout, **kwargs)
    assert first == generate_teams(checkout, **kwargs)
    assert first["teams"][0][0]["ability"] == "Sheer Force"
    assert first["teams"][1][0]["moves"] == ["thunderbolt", "protect"]
    assert first["teams"][1][0]["evs"]["spa"] == 32
    with ShowdownEnvironment(checkout) as env:
        for team in first["teams"]:
            case = witness_case(load_inventory(), "squawkabillyyellow")
            case["teams"]["self"] = team
            env.reset(case)
            observation = env.observation("self", include_history=True)
            for version in range(1, 5):
                encoder = make_encoder(
                    CATALOG, f"showdown-learned-observation-v{version}"
                )
                encoded = encoder.encode(observation)
                assert np.isfinite(encoded).all()
                stripped = deepcopy(observation)
                stripped.pop("projection_coverage")
                assert np.array_equal(encoded, encoder.encode(stripped))
    for invalid in [
        {"form": "ogerpontealtera"},
        {"form": "squawkabillyyellow", "ability": "Levitate"},
        {"form": "squawkabillyyellow", "move": "Spore"},
        {"move": "Spore"},
        {"form": "toxtricitylowkey", "item": None},
        {"form": "toxtricitylowkey", "evs": {"hp": 32}},
    ]:
        with pytest.raises(ValueError, match="native_full_domain_generation_failed"):
            generate_teams(checkout, seed=[1, 2, 3, 4], constraints=[invalid])
    with pytest.raises(ValueError, match="bounded_generation"):
        generate_teams(checkout, seed=[True, 2, 3, 4])


def test_new_mega_native_checkpoint_and_public_unknown(checkout):
    case = witness_case(load_inventory(), "eelektrossmega")
    with ShowdownEnvironment(checkout) as env:
        env.reset(case)
        before = env.observation("self", include_history=True)
        other = before["state"]["opponent_side"]
        active = other["pokemon"][other["active_identity"]]
        assert active["known_item"] == {"knowledge": "unknown"}
        assert not active["known_moves"]
        action = next(i for i in range(10, 14) if before["action_mask"][i])
        env.step({"self": action, "opponent": 6}, revision=before["revision"])
        assert any(
            "Eelektross-Mega" in line
            for line in env.observation("self", include_history=True)["public_history"]
        )
        saved = env.save()
        with env.fork() as fork:
            assert fork.save()["digest"] == saved["digest"]
        assert case == witness_case(load_inventory(), "eelektrossmega")


def test_training_launcher_accepts_full_domain_and_keeps_short_budget():
    config = json.loads(
        (ROOT / "config/learning/full_domain_smoke_cpu.json").read_text()
    )
    validate_config(config)
    assert config["experiments"][0]["steps"] == 2048
    assert config["cpu_percent"] == 50 and config["envs"] == 8


@pytest.mark.parametrize(
    "target,move",
    [
        ("castformsunny", "Sunny Day"),
        ("aegislashblade", "Iron Head"),
        ("morpekohangry", "Protect"),
    ],
)
def test_native_temporary_form_survives_base_form_own_request(checkout, target, move):
    case = witness_case(load_inventory(), target, move)
    with ShowdownEnvironment(checkout) as env:
        env.reset(case)
        env.step(
            {"self": 6, "opponent": 6}, revision=env.observation("self")["revision"]
        )
        observation = env.observation("self", include_history=True)
        own = observation["state"]["self_side"]
        row = own["pokemon"][own["active_identity"]]
        from advisor.learned_encoder import identifier

        assert identifier(row["details"]) == target
        assert identifier(row["request_details"]) == identifier(
            case["teams"]["self"][0]["species"]
        )


def test_full_catalog_covers_virtual_forms_and_fails_closed():
    encoder = make_encoder(CATALOG, "showdown-learned-observation-v3")
    assert encoder._species("Furfrou-Pharaoh, L50")["types"] == ["Normal"]
    assert encoder._species("Florges-Blue, L50")["base_stats"]["spd"] > 0
    with pytest.raises(ValueError, match="species_outside_full_domain"):
        encoder._species("Invented-Pokemon, L50")


def test_training_identity_detects_changed_bank_and_legacy_config_is_stable(
    tmp_path, monkeypatch
):
    from advisor import learned_full_domain as domain
    from scripts.train_showdown_autonomous import training_config_fingerprint

    config = json.loads(
        (ROOT / "config/learning/full_domain_smoke_cpu.json").read_text()
    )
    original, identity = training_config_fingerprint(config)
    assert identity["bank_sha256"] and identity["adapter_source_sha256"]
    legacy = {**config, "curriculum_version": "showdown-learning-curriculum-v6"}
    assert training_config_fingerprint(legacy) == (
        sha256(json.dumps(legacy, sort_keys=True).encode()).hexdigest(),
        None,
    )
    changed = tmp_path / "bank"
    changed.mkdir()
    bank = json.loads(gzip.decompress((domain.BANK / "teams.json.gz").read_bytes()))
    bank["teams"]["train"][0][0]["nature"] = "Adamant"
    raw = json.dumps(bank, sort_keys=True, separators=(",", ":")).encode()
    packed = gzip.compress(raw, mtime=0)
    (changed / "teams.json.gz").write_bytes(packed)
    manifest = json.loads((domain.BANK / "manifest.json").read_text())
    manifest.update(
        bank_sha256=sha256(packed).hexdigest(), content_sha256=sha256(raw).hexdigest()
    )
    (changed / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(domain, "BANK", changed)
    replacement, _ = training_config_fingerprint(config)
    assert replacement != original


def test_unmodeled_public_state_events_are_explicit_not_deleted(checkout):
    case = witness_case(load_inventory(), "aegislashblade", "King's Shield")
    with ShowdownEnvironment(checkout) as env:
        env.reset(case)
        env.step(
            {"self": 6, "opponent": 6}, revision=env.observation("self")["revision"]
        )
        observation = env.observation("self", include_history=True)
        assert (
            "-singleturn"
            in observation["projection_coverage"]["preserved_unmodeled_state_events"]
        )
        assert any("|-singleturn|" in line for line in observation["public_history"])
        assert not {"seed", "teams", "native_state", "checkpoint"} & observation.keys()


def test_native_illusion_reveal_rebinds_moves_without_false_teammate_facts(checkout):
    inventory = load_inventory()
    case = witness_case(inventory, "charizard")
    case["teams"]["self"][0]["moves"] = ["Protect", "Flamethrower"]
    case["teams"]["self"][0].update(
        nature="Timid",
        evs={"hp": 2, "atk": 0, "def": 0, "spa": 32, "spd": 0, "spe": 32},
    )
    blast = deepcopy(case["teams"]["opponent"][0])
    others = case["teams"]["opponent"][1:]
    zoroark = deepcopy(inventory["species"]["zoroark"]["witness"])
    zoroark["moves"] = ["Dark Pulse"]
    case["teams"]["opponent"] = [zoroark, others[0], blast, *others[1:4]]
    with ShowdownEnvironment(checkout) as env:
        env.reset(case)
        env.step(
            {"self": 6, "opponent": 6}, revision=env.observation("self")["revision"]
        )
        before = env.observation("self", include_history=True)
        side = before["state"]["opponent_side"]
        apparent = side["active_identity"]
        assert side["pokemon"][apparent]["details"].startswith("Blastoise")
        assert (
            side["pokemon"][apparent]["identity_scope"]
            == "public_apparent_identity_unconfirmed"
        )
        assert side["pokemon"][apparent]["known_moves"] == ["darkpulse"]
        env.step({"self": 7, "opponent": 6}, revision=before["revision"])
        after = env.observation("self", include_history=True)
        side = after["state"]["opponent_side"]
        actor = side["pokemon"][side["active_identity"]]
        assert actor["details"].startswith("Zoroark")
        assert actor["known_moves"] == ["darkpulse"]
        assert apparent not in side["pokemon"]
        assert after["state"]["state_version"] == "showdown-policy-state-v2"
        assert before["state"]["opponent_side"]["active_identity"] == apparent


def test_confirmed_illusion_preserves_prior_real_teammate_observations():
    from advisor.showdown_observation import project_policy_observation

    native = {
        "schema_version": "showdown-policy-observation-v1",
        "side": "self",
        "own_request": {},
    }
    history = [
        "|start",
        "|poke|p2|Zoroark, L50",
        "|poke|p2|Blastoise, L50",
        "|switch|p2a: slot-2|Blastoise, L50|80/100",
        "|-item|p2a: slot-2|Leftovers",
        "|move|p2a: slot-2|Surf|p1a: slot-0",
        "|switch|p2a: slot-1|Abomasnow, L50|100/100",
        "|switch|p2a: slot-2|Blastoise, L50|100/100",
        "|move|p2a: slot-2|Dark Pulse|p1a: slot-0",
        "|replace|p2a: slot-0|Zoroark, L50|70/100",
    ]
    state = project_policy_observation(native, history)["state"]["opponent_side"]
    assert state["pokemon"]["p2a: slot-2"]["known_item"] == "leftovers"
    assert state["pokemon"]["p2a: slot-2"]["known_moves"] == ["surf"]
    actual = state["pokemon"]["p2a: slot-0"]
    assert actual["known_moves"] == ["darkpulse"]
    assert actual["known_item"] == {"knowledge": "unknown"}
    assert history[-1].startswith("|replace|")


def test_native_revival_blessing_requests_fainted_slot_and_checkpoint_continuity(
    checkout,
):
    inventory = load_inventory()
    case = witness_case(inventory, "pikachu")
    case["teams"]["self"][0].update(
        moves=["Protect"],
        item="",
        nature="Timid",
        evs={"hp": 0, "atk": 0, "def": 0, "spa": 32, "spd": 2, "spe": 32},
    )
    case["teams"]["self"][1] = deepcopy(inventory["species"]["pawmot"]["witness"])
    case["teams"]["self"][1]["moves"] = ["Revival Blessing", "Protect"]
    case["teams"]["self"][1].update(
        nature="Jolly",
        item="Focus Sash",
        evs={"hp": 32, "atk": 0, "def": 2, "spa": 0, "spd": 0, "spe": 32},
    )
    case["teams"]["opponent"][0] = deepcopy(inventory["species"]["garchomp"]["witness"])
    case["teams"]["opponent"][0].update(
        moves=["Earthquake"],
        nature="Adamant",
        evs={"hp": 2, "atk": 32, "def": 0, "spa": 0, "spd": 0, "spe": 32},
    )
    with ShowdownEnvironment(checkout) as env:
        env.reset(case)
        env.step(
            {"self": 6, "opponent": 6}, revision=env.observation("self")["revision"]
        )
        env.step(
            {"self": 6, "opponent": 6}, revision=env.observation("self")["revision"]
        )
        own = env.observation("self")
        assert own["request_state"] == "switch"
        slot = next(
            i
            for i, p in enumerate(own["own_request"]["side"]["pokemon"])
            if p["details"].startswith("Pawmot")
        )
        env.step({"self": slot, "opponent": 26}, revision=own["revision"])
        own = env.observation("self")
        env.step({"self": 6, "opponent": 6}, revision=own["revision"])
        own = env.observation("self")
        assert own["request_state"] == "switch"
        slots = own["own_request"]["side"]["pokemon"]
        fainted = [i for i, p in enumerate(slots) if p["condition"].endswith(" fnt")]
        assert fainted and [i for i, m in enumerate(own["action_mask"]) if m] == fainted
        with env.fork() as fork:
            action = {"self": fainted[0], "opponent": 26}
            env.step(action, revision=own["revision"])
            fork.step(action, revision=fork.observation("self")["revision"])
            assert env.save()["digest"] == fork.save()["digest"]
        assert any(
            p["details"].startswith("Pikachu") and not p["condition"].endswith(" fnt")
            for p in env.observation("self")["own_request"]["side"]["pokemon"]
        )
