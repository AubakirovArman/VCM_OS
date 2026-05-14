"""Tests for expanded tool ingestion."""
from vcm_os.memory.writer.tool_ingestor import ToolResultIngestor
from vcm_os.schemas import EventRecord


def _evt(content: str, tool_name: str) -> EventRecord:
    return EventRecord(
        event_id="t1",
        project_id="p1",
        session_id="s1",
        event_type="tool_call",
        payload={"content": content, "tool_name": tool_name},
        raw_text=content,
    )


def test_parse_docker_success():
    ingestor = ToolResultIngestor()
    objs = ingestor.ingest(_evt("Successfully built abc123def456", "docker_build"))
    assert any("Successfully built" in o.compressed_summary for o in objs)


def test_parse_docker_error():
    ingestor = ToolResultIngestor()
    objs = ingestor.ingest(_evt("Step 3/10 failed: gcc not found", "docker_build"))
    assert any(o.memory_type.value == "error" for o in objs)


def test_parse_terraform_plan():
    ingestor = ToolResultIngestor()
    text = "Plan: 3 to add, 1 to change, 0 to destroy."
    objs = ingestor.ingest(_evt(text, "terraform"))
    assert any("+3" in o.compressed_summary and "~1" in o.compressed_summary for o in objs)


def test_parse_kubectl_status():
    ingestor = ToolResultIngestor()
    text = "web-1 1/1 Running\napi-2 2/2 Running"
    objs = ingestor.ingest(_evt(text, "kubectl"))
    assert any("web-1:Running" in o.compressed_summary for o in objs)


def test_parse_kubectl_crash():
    ingestor = ToolResultIngestor()
    objs = ingestor.ingest(_evt("pod-x 0/1 CrashLoopBackOff", "kubectl"))
    assert any(o.memory_type.value == "error" for o in objs)


def test_parse_api_success():
    ingestor = ToolResultIngestor()
    objs = ingestor.ingest(_evt("HTTP/1.1 200 OK\n{}", "curl"))
    assert any("HTTP 200" in o.compressed_summary for o in objs)


def test_parse_api_error():
    ingestor = ToolResultIngestor()
    objs = ingestor.ingest(_evt("HTTP/1.1 500 Internal Server Error", "curl"))
    assert any(o.memory_type.value == "error" for o in objs)


def test_parse_security_scan():
    ingestor = ToolResultIngestor()
    text = "Found 2 high severity issues\n1 critical severity\nanother high severity"
    objs = ingestor.ingest(_evt(text, "bandit"))
    assert any("high:2" in o.compressed_summary for o in objs)


def test_parse_coverage():
    ingestor = ToolResultIngestor()
    objs = ingestor.ingest(_evt("Coverage: 87.5%", "coverage"))
    assert any("87.5%" in o.compressed_summary for o in objs)


def test_parse_coverage_low():
    ingestor = ToolResultIngestor()
    objs = ingestor.ingest(_evt("Coverage: 23.0%", "coverage"))
    assert any(o.memory_type.value == "error" for o in objs)


def test_parse_package_vuln():
    ingestor = ToolResultIngestor()
    objs = ingestor.ingest(_evt("Found 5 high severity vulnerabilities", "npm"))
    assert any(o.memory_type.value == "error" for o in objs)
