from fractions import Fraction

from llm.advisor_detached_rock_slide_multi_recipient_immediate_move_pair import _pending_recipient_flinched
from llm.advisor_detached_rock_slide_multi_recipient_predictive_graph_materialization import _recipient_flinch_branches


OWNER_A = {"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "a"}
OWNER_B = {"session_id": "s", "side": "opponent", "slot_index": 1, "pokemon_id": "b"}
AUTHORITY = {"applicable": True, "capability": {"probability": {"numerator": 30, "denominator": 100}}, "target_substitute_authority": {"status": "known", "state": "known_inactive"}, "provenance": "rock_slide_recipient_local_catalogued_flinch_authority_v1"}


def _event(*, fainted=False):
    return {"probability": Fraction(1, 8), "outcome": "hit", "hit_state": "hit", "critical_state": "non_critical", "damage_roll": {"roll_index": 0}, "fainted": fainted}


def _row(owner, state, fainted=False):
    flinch = {"state": state}
    if state == "flinched": flinch["hypothetical_target_flinch"] = {"schema_version": "detached-hypothetical-immediate-flinch-v1", "state": "flinched", "provenance": "rock_slide_recipient_successful_damage_roll_secondary_v1"}
    return {"recipient": {"owner": owner}, "fainted": fainted, "flinch": flinch}


def test_surviving_recipient_hit_branches_exactly_and_ko_never_flinches():
    branches = _recipient_flinch_branches(_event(), AUTHORITY)
    assert [row["flinch"]["state"] for row in branches] == ["not_flinched", "flinched"]
    assert sum((row["probability"] for row in branches), Fraction()) == Fraction(1, 8)
    assert branches[1]["probability"] == Fraction(3, 80)
    assert _recipient_flinch_branches(_event(fainted=True), AUTHORITY)[0]["flinch"]["state"] == "not_flinched"


def test_only_exact_pending_recipient_flinch_cancels_and_other_recipient_is_local():
    pending = OWNER_A
    source = {"ordered_recipient_outcomes": (_row(OWNER_A, "flinched"), _row(OWNER_B, "not_flinched"))}
    assert _pending_recipient_flinched(source, pending) is True
    other = {"ordered_recipient_outcomes": (_row(OWNER_A, "not_flinched"), _row(OWNER_B, "flinched"))}
    assert _pending_recipient_flinched(other, pending) is False
    ko = {"ordered_recipient_outcomes": (_row(OWNER_A, "flinched", fainted=True), _row(OWNER_B, "not_flinched"))}
    assert _pending_recipient_flinched(ko, pending) is False


def test_missing_or_foreign_flinch_provenance_is_not_a_pending_cancellation():
    invalid = {"ordered_recipient_outcomes": ({"recipient": {"owner": OWNER_A}, "fainted": False, "flinch": {"state": "flinched", "hypothetical_target_flinch": {"provenance": "foreign"}}}, _row(OWNER_B, "not_flinched"))}
    assert _pending_recipient_flinched(invalid, OWNER_A) is False
