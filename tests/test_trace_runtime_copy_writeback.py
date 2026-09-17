from llm.advisor_trace_runtime_copy_support import resolve_trace_runtime_copy_support


def test_trace_runtime_copy_support_allows_bounded_passive_ability():
    result = resolve_trace_runtime_copy_support("water-absorb")
    assert result["status"] == "resolved"
    assert "type_immunity" in result["supporting_categories"]


def test_trace_runtime_copy_support_blocks_immediate_entry_followup_families():
    for ability in ("intimidate", "download", "drizzle", "electric-surge", "neutralizing-gas"):
        result = resolve_trace_runtime_copy_support(ability)
        assert result["status"] == "unsupported", (ability, result)
        assert result["reason"] == "trace_copied_ability_followup_unsupported"


def test_trace_runtime_copy_support_blocks_additional_current_authority_requirement():
    result = resolve_trace_runtime_copy_support("levitate")
    assert result == {
        "status": "unsupported",
        "reason": "trace_copied_ability_additional_current_authority_required",
        "copied_ability": "levitate",
    }


def test_trace_runtime_copy_support_rejects_invalid_identity():
    assert resolve_trace_runtime_copy_support(None)["status"] == "rejected"
    assert resolve_trace_runtime_copy_support("")["status"] == "rejected"
