def test_counter_snapshot_copy_cancel_and_clear_contract():
    session = {"rage_fist_hits_received": 2}
    opened = dict(session)
    opened["rage_fist_hits_received"] = 3
    assert session["rage_fist_hits_received"] == 2  # Cancel preserves the snapshot.
    session = dict(opened)  # Apply uses a defensive copy.
    session = None  # Clear removes only the session snapshot.
    assert session is None
