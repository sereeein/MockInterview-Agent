from mockinterview.agent.client import build_cached_system, parse_json_response


def test_build_cached_system_concatenates_parts():
    out = build_cached_system(["你是面试官", "rubric: ..."])
    assert isinstance(out, str)
    assert "你是面试官" in out
    assert "rubric: ..." in out


def test_parse_json_response_extracts_json_block():
    fake = '```json\n{"a": 1}\n```'
    assert parse_json_response(fake) == {"a": 1}


def test_parse_json_response_handles_raw_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}
