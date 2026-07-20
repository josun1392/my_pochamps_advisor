import pytest

from llm.advisor_candidate_contract import adapt_ui_move_slots


def test_ui_move_slots_preserve_order_empty_slots_duplicates_and_ignore_selected_index():
    slots = [{"move_id": "tackle"}, None, {"move_id": "tackle"}, {"move_id": "protect"}]
    assert adapt_ui_move_slots(selected_moves=slots) == ("tackle", None, "tackle", "protect")


@pytest.mark.parametrize("slots", ["tackle", [{"move_id": "a"}] * 5, [{"name_en": "missing-id"}]])
def test_malformed_slot_containers_fail_closed(slots):
    with pytest.raises(ValueError):
        adapt_ui_move_slots(selected_moves=slots)
