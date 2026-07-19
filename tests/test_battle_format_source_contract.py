import pytest
from llm.advisor_battle_state_context import normalize_user_confirmed_battle_format


def test_only_explicit_singles_or_doubles_are_trusted() -> None:
    assert normalize_user_confirmed_battle_format({"battle_format": "singles", "source": "user_confirmed_battle_format"})["battle_format"] == "singles"
    assert normalize_user_confirmed_battle_format({"battle_format": "doubles", "source": "user_confirmed_battle_format"})["battle_format"] == "doubles"
    with pytest.raises(ValueError): normalize_user_confirmed_battle_format({"battle_format": "single", "source": "user_confirmed_battle_format"})
    with pytest.raises(ValueError): normalize_user_confirmed_battle_format({"battle_format": "singles", "source": "inferred_from_team_size"})
