from copy import deepcopy

from advisor.hit_modifier_capabilities import resolve_hit_modifier_capabilities


def _move(category="physical"): return {"move_id": "tackle", "category": category}
def _authority(status="known", value="hustle", applicability="applicable"):
    row={"status":status}
    if status == "known": row.update(value=value, applicability={"status":applicability})
    return {"attacker_ability":row}


def test_hustle_physical_is_supported_and_applicable_with_lossless_factor():
    result=resolve_hit_modifier_capabilities(move=_move(),source_authority=_authority())
    effect=result["ledger"][0]["effect"]
    assert result["status"]=="resolved" and result["ledger"][0]["state"]=="applicable"
    assert effect == {"kind":"accuracy_multiplier_q12","numerator":3277,"denominator":4096,"ordering":"before_accuracy_evasion_stages"}


def test_explicit_neutral_requires_exact_absence_or_catalog_condition():
    absent=resolve_hit_modifier_capabilities(move=_move(),source_authority=_authority(status="known_absent"))
    special=resolve_hit_modifier_capabilities(move=_move("special"),source_authority=_authority())
    assert absent["ledger"][0]["state"]=="known_neutral"
    assert special["ledger"][0]["state"]=="known_neutral"


def test_missing_and_unknown_applicability_fail_closed_without_neutral_fabrication():
    missing=resolve_hit_modifier_capabilities(move=_move(),source_authority={"attacker_ability":{"status":"unknown"}})
    unknown=resolve_hit_modifier_capabilities(move=_move(),source_authority=_authority(applicability="unknown"))
    assert missing["status"]==unknown["status"]=="incomplete"
    assert all(row["state"] != "known_neutral" for row in (*missing["ledger"],*unknown["ledger"]))


def test_known_uncataloged_ability_is_unsupported_and_irrelevant_slots_do_not_block():
    unsupported=resolve_hit_modifier_capabilities(move=_move(),source_authority=_authority(value="compound-eyes"))
    irrelevant=resolve_hit_modifier_capabilities(move=_move("special"),source_authority={**_authority(),"target_item":{"status":"unknown"},"weather":{"status":"unknown"}})
    assert unsupported["status"]=="unsupported" and unsupported["ledger"][0]["source_value"]=="compound-eyes"
    assert irrelevant["status"]=="resolved" and irrelevant["required_source_slots"] == ("attacker_ability",)


def test_output_is_detached_and_input_is_not_mutated():
    source=_authority(); original=deepcopy(source)
    result=resolve_hit_modifier_capabilities(move=_move(),source_authority=source)
    result["ledger"][0]["effect"]["numerator"]=0
    assert source == original
