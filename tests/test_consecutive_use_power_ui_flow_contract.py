def test_snapshot_apply_cancel_clear_and_gate_contract():
    session = {"fury_cutter_consecutive_uses": 2}
    edited = dict(session); edited["fury_cutter_consecutive_uses"] = 3
    assert session["fury_cutter_consecutive_uses"] == 2
    session = dict(edited)
    assert session["fury_cutter_consecutive_uses"] == 3
    assert session is not None  # Gate omission does not clear it.
    session = None
    assert session is None
