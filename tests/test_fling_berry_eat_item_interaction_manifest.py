import hashlib
import json
from pathlib import Path

from advisor.canonical_fling_berry_eat_item_interactions import (
    resolve_canonical_fling_berry_ability_interaction,
    resolve_canonical_fling_berry_item_identity,
    resolve_canonical_fling_berry_timing,
)
from scripts.extract_fling_berry_eat_item_interactions import (
    COMMIT,
    EXPECTED_ABILITIES_SHA256,
    extract,
)

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "data" / "vendor" / "pokemon_showdown" / COMMIT
ABILITIES = VENDOR / "abilities.ts"
MOVES = VENDOR / "moves.ts"
FLING = ROOT / "data" / "static" / "fling_item_effects.json"
MANIFEST = ROOT / "data" / "static" / "fling_berry_eat_item_interactions.json"


def test_pinned_abilities_hash_and_manifest_provenance_are_exact():
    assert hashlib.sha256(ABILITIES.read_bytes()).hexdigest() == EXPECTED_ABILITIES_SHA256
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = raw["source_provenance"]
    assert source["repository"] == "https://github.com/smogon/pokemon-showdown"
    assert source["commit_sha"] == COMMIT
    assert source["abilities"]["source_path"] == "data/abilities.ts"
    assert source["abilities"]["sha256"] == EXPECTED_ABILITIES_SHA256
    assert source["moves"]["source_path"] == "data/moves.ts"
    assert len(source["moves"]["sha256"]) == 64
    assert len(source["fling_manifest"]["sha256"]) == 64


def test_extraction_is_deterministic_and_binds_exact_28_fling_berries(tmp_path):
    current = json.loads(MANIFEST.read_text(encoding="utf-8"))
    output = tmp_path / "again.json"
    extract(abilities_ts=ABILITIES, moves_ts=MOVES, fling_manifest=FLING, output=output)
    regenerated = json.loads(output.read_text(encoding="utf-8"))
    assert regenerated == current
    assert len(current["berry_item_ids"]) == 28
    fling = json.loads(FLING.read_text(encoding="utf-8"))
    expected = sorted(row["item_id"] for row in fling["items"] if row["effect"]["kind"] == "berry_effect")
    assert current["berry_item_ids"] == expected
    assert resolve_canonical_fling_berry_item_identity("cheri-berry")["status"] == "resolved"
    assert resolve_canonical_fling_berry_item_identity("light-ball")["status"] == "not_applicable"


def test_source_derived_ability_families_are_classified_without_generic_ability_claims():
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert set(raw["interactions"]) == {
        "angershell", "asoneglastrier", "asonespectrier", "berserk",
        "cheekpouch", "cudchew", "harvest", "klutz", "neutralizinggas",
        "ripen", "unnerve",
    }
    assert "pickup" in raw["ability_scan"]["no_relevant_direct_hook_showdown_ids"]

    cheek = resolve_canonical_fling_berry_ability_interaction("cheek-pouch")
    assert cheek["classification"]["direct_target_eat_item_hook"] is True
    assert cheek["classification"]["roles"] == ["target_post_eat_item_consequence"]

    ripen = resolve_canonical_fling_berry_ability_interaction("ripen")
    assert ripen["classification"]["direct_target_eat_item_hook"] is True
    assert set(ripen["classification"]["roles"]) == {
        "berry_heal_modifier", "berry_boost_modifier",
        "target_post_eat_item_consequence", "try_eat_notification",
    }

    cud = resolve_canonical_fling_berry_ability_interaction("cud-chew")
    assert cud["classification"]["direct_target_eat_item_hook"] is True
    assert cud["classification"]["future_lifecycle_deferred"] is True

    unnerve = resolve_canonical_fling_berry_ability_interaction("unnerve")
    assert unnerve["classification"]["try_eat_only"] is True
    assert unnerve["classification"]["fling_direct_eat_path"] == "try_eat_hook_not_invoked_by_fling_direct_eat"

    klutz = resolve_canonical_fling_berry_ability_interaction("klutz")
    assert klutz["classification"]["direct_target_eat_item_hook"] is False
    assert klutz["classification"]["roles"] == ["source_item_suppression_external_to_eat_event"]

    gas = resolve_canonical_fling_berry_ability_interaction("neutralizing-gas")
    assert gas["classification"]["roles"] == ["generic_ability_suppression_external_to_eat_event"]

    pressure = resolve_canonical_fling_berry_ability_interaction("pressure")
    assert pressure["status"] == "resolved"
    assert pressure["classification"]["fling_direct_eat_path"] == "no_direct_target_eat_item_hook"

    unknown = resolve_canonical_fling_berry_ability_interaction("not-a-real-ability")
    assert unknown["status"] == "incomplete"


def test_fling_timing_contract_keeps_source_pre_hit_and_target_post_hit_distinct():
    timing = resolve_canonical_fling_berry_timing()
    assert timing["status"] == "resolved"
    assert timing["timing"] == {
        "source_pre_hit_cud_chew_dispatch": True,
        "source_pre_hit_requires_target_hit": False,
        "target_eat_after_successful_target_hit": True,
        "target_eat_item_after_successful_eat": True,
        "ordinary_held_berry_trigger_used": False,
    }
