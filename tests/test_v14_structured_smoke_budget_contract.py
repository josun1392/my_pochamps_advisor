import ast
from pathlib import Path


def test_v1415_contract_limits_the_fixed_fixture_sample_to_three_calls_without_repair_paths():
    source = Path("llm/advisor_client.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    structured = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_structured_ui_recommendation")
    calls = [node for node in ast.walk(structured) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "call_structured_recommendation_provider"]
    assert len(calls) == 1
    assert all("retry" not in ast.unparse(node).lower() and "fallback" not in ast.unparse(node).lower() for node in ast.walk(structured) if isinstance(node, ast.Call))
