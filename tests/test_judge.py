import pytest

from aeo.judge import _extract_json


def test_extract_plain_json():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_fenced_json():
    assert _extract_json('```json\n{"ranking": ["x", "y"]}\n```') == {"ranking": ["x", "y"]}


def test_extract_json_with_prose_around():
    txt = 'Here is my verdict:\n{"verdicts": [{"n": 1, "stated": "asserts"}]}\nDone.'
    assert _extract_json(txt) == {"verdicts": [{"n": 1, "stated": "asserts"}]}


def test_extract_json_nested_braces():
    assert _extract_json('prefix {"a": {"b": 2}} suffix') == {"a": {"b": 2}}


def test_extract_json_raises_when_absent():
    with pytest.raises(ValueError):
        _extract_json("no json here at all")
