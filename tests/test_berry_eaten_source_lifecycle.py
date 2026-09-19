from advisor.canonical_berry_eaten_state import (
    POKEMON_SHA256,
    resolve_canonical_berry_eaten_lifecycle,
)


def test_pinned_berry_eaten_lifecycle_contract_is_exact():
    row = resolve_canonical_berry_eaten_lifecycle()
    assert row["status"] == "resolved"
    assert row["pokemon_sha256"] == POKEMON_SHA256 == "803d22124bef93566c4654e5a20a95f7dc7a8818e8b242a27b56bc6dc951b0df"
    assert row["initial_state"] == "known_false"
    assert row["generic_successful_eat_item_transition"] == "known_true"
    assert row["clear_volatile_resets"] is False
    assert row["faint_resets"] is False
    assert set(row["direct_writers"]) == {"fling", "bug-bite", "pluck", "cud-chew"}
    assert row["belch_selection_reader"] is True
    assert row["belch_execution_reader"] is True
