import pytest
from agent.tool_call_parser import extract_tool_call


def test_extract_simple_json():
    text = 'Here is the call: {"tool": "search", "input": "PCI DSS"}'
    result = extract_tool_call(text)
    assert result == {"tool": "search", "input": "PCI DSS"}


def test_extract_nested_json():
    text = 'Response: {"tool": "summarize", "input": {"topic": "firewalls", "depth": "high"}}'
    result = extract_tool_call(text)
    assert result == {
        "tool": "summarize",
        "input": {"topic": "firewalls", "depth": "high"},
    }


def test_multiple_json_blocks():
    text = """
        Irrelevant: {"ignore": "this"}
        {"tool": "scan", "input": {"target": "10.0.0.1", "port": 80}}
        Extra: {"post": "processing"}
    """
    result = extract_tool_call(text)
    assert result == {"ignore": "this"}  # Only the first JSON block should be parsed


def test_unbalanced_braces():
    text = 'Incomplete: {"tool": "lookup", "input": {"query": "encryption"'
    with pytest.raises(ValueError, match="Could not extract TOOL_CALL"):
        extract_tool_call(text)


def test_malformed_json():
    text = '{"tool": "list", "input": ["item1", item2"]}'  # Missing quote around item2
    with pytest.raises(ValueError, match="Could not extract TOOL_CALL"):
        extract_tool_call(text)


def test_no_json_present():
    text = "Nothing to see here."
    with pytest.raises(ValueError, match="Could not extract TOOL_CALL"):
        extract_tool_call(text)
