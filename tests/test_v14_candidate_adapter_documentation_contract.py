from pathlib import Path


def test_v1421_repair_documentation_records_its_boundaries():
    text = Path("docs/spike_v14.2.1_deterministic_candidate_adapter_repair.md").read_text(encoding="utf-8")
    assert "metadata-only" in text
    assert "fabricate resolved zero minimum/maximum damage" in text
    assert "existing deterministic production\ncontext" in text
    assert "All ten dynamic families" in text
    assert "Environment alone may emit effective type" in text
    assert "Provider/UI orchestration is excluded" in text
