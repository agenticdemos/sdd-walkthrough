"""Checks from specs/cli-pretty/spec.md (spec-light: no numbered requirements)."""
import io
import json

from tools.pretty import main, pretty


def test_file_or_stdin_printed_indented_with_sorted_keys(tmp_path, capsys, monkeypatch):
    f = tmp_path / "in.json"
    f.write_text('{"b": 1, "a": {"d": 2, "c": 3}}')
    assert main([str(f)]) == 0
    from_file = capsys.readouterr().out
    assert from_file == '{\n  "a": {\n    "c": 3,\n    "d": 2\n  },\n  "b": 1\n}\n'
    monkeypatch.setattr("sys.stdin", io.StringIO(f.read_text()))
    assert main([]) == 0
    assert capsys.readouterr().out == from_file


def test_output_is_still_valid_json():
    doc = {"remaining_allowance_pence": 50000, "subscriber_id": "S-1"}
    assert json.loads(pretty(json.dumps(doc))) == doc


def test_invalid_json_exits_non_zero_with_one_line_error(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))
    assert main([]) == 1
    err = capsys.readouterr().err
    assert err.startswith("pretty: invalid JSON") and err.count("\n") == 1
