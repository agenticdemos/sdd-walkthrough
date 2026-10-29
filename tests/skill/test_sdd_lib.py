"""The sdd skill's shared library: YAML subset parser, front matter, specs, REQs, table."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude/skills/sdd/scripts"))
import _sdd  # noqa: E402

CONFIG = """\
specs_dir: specs
req_pattern: 'REQ-[A-Z]+-\\d{3}'
test_dirs: [tests]
code_dirs: [src, tools]
gates:                         # gate name -> command
  unit: uv run pytest tests/unit -q
  evidence: "python3 x.py demo"
mutation:
  targets: [src/rules/]
  approvers: [person-a, person-b]
board:
  seed:
    TASK-01: Done
    TASK-05: In review
tasks:
  - id: TASK-01
    title: Tax-year function   # comment
    reqs: [REQ-ABC-001, REQ-ABC-002]
    order: 1
    done: null
  - id: TASK-02
    title: "Overall: limit"
    reqs: []
paths:
  /things/{id}:
    get:
      parameters:
        - name: id
          in: path
      responses:
        '200':
          $ref: '#/components/x'
empty:
flag: true
ratio: 1.5
list_same_indent:
- a
- b
"""


def test_subset_parser_matches_pyyaml():
    yaml = pytest.importorskip("yaml")
    assert _sdd.parse_yaml_subset(CONFIG) == yaml.safe_load(CONFIG)


def test_subset_parser_values():
    data = _sdd.parse_yaml_subset(CONFIG)
    assert data["req_pattern"] == r"REQ-[A-Z]+-\d{3}"
    assert data["gates"]["unit"] == "uv run pytest tests/unit -q"
    assert data["tasks"][0] == {"id": "TASK-01", "title": "Tax-year function",
                                "reqs": ["REQ-ABC-001", "REQ-ABC-002"], "order": 1, "done": None}
    assert data["tasks"][1]["title"] == "Overall: limit"
    assert data["paths"]["/things/{id}"]["get"]["responses"]["200"]["$ref"] == "#/components/x"
    assert data["empty"] is None and data["flag"] is True and data["ratio"] == 1.5
    assert data["list_same_indent"] == ["a", "b"]


def test_load_config_walks_up_and_sets_root(tmp_path, monkeypatch):
    (tmp_path / "sdd.yaml").write_text(CONFIG)
    (tmp_path / "a" / "b").mkdir(parents=True)
    monkeypatch.chdir(tmp_path / "a" / "b")
    config = _sdd.load_config()
    assert config["root"] == tmp_path.resolve()
    assert config["code_dirs"] == ["src", "tools"]
    assert config["evidence_dir"] == "evidence"  # default filled in


def test_load_config_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        _sdd.load_config(tmp_path)


def test_front_matter_specs_and_reqs(tmp_path):
    (tmp_path / "sdd.yaml").write_text("specs_dir: specs\n")
    alpha = tmp_path / "specs" / "alpha"
    alpha.mkdir(parents=True)
    (alpha / "requirements.md").write_text(
        "---\nid: alpha\nstop: evidentiary   # dial\ncovers: [src/alpha/, contracts/a.yaml]\n"
        "verified_at: null\nowner: person-a\n---\n# Alpha\n\n"
        "1. **REQ-ABC-001** (ubiquitous): The thing shall work.\n"
        "   evidence: REQ-ABC-001 tests\n"
        "2. **REQ-ABC-002** (event): WHEN x, the thing shall y (see REQ-ABC-001).\n"
        "3. **REQ-ABC-003** (optional feature, `status: deferred`): WHERE z, ...\n")
    light = tmp_path / "specs" / "light"
    light.mkdir()
    (light / "spec.md").write_text("---\nstop: spec-light\ncovers: [tools/x.py]\nverified_at: 1234567\n---\nText\n")
    (tmp_path / "specs" / "notes.md").write_text("not a spec dir\n")

    fm, body = _sdd.front_matter(alpha / "requirements.md")
    assert fm["stop"] == "evidentiary" and body.startswith("# Alpha")

    found = _sdd.specs(_sdd.load_config(tmp_path))
    assert [s["id"] for s in found] == ["alpha", "light"]
    assert found[0]["covers"] == ["src/alpha/", "contracts/a.yaml"]
    assert found[0]["verified_at"] is None and found[0]["owner"] == "person-a"
    assert found[1]["verified_at"] == "1234567" and found[1]["path"].name == "spec.md"
    assert found[1]["dir"] == light

    assert _sdd.reqs(alpha / "requirements.md", r"REQ-[A-Z]+-\d{3}") == [
        ("REQ-ABC-001", "active"), ("REQ-ABC-002", "active"), ("REQ-ABC-003", "deferred")]
    assert _sdd.reqs(light / "requirements.md", r"REQ-[A-Z]+-\d{3}") == []


def test_table_aligns_columns():
    out = _sdd.table(["spec", "stop"], [["alpha", "evidentiary"], ["b", "x"]]).splitlines()
    assert out[0] == "spec   stop"
    assert out[1] == "-----  -----------"
    assert out[2] == "alpha  evidentiary"


def test_gates_by_stop_matches_dial_table():
    assert list(_sdd.GATES_BY_STOP) == _sdd.STOPS
    assert _sdd.GATES_BY_STOP["spec-light"]["fresh"] == "warn"
    assert _sdd.GATES_BY_STOP["spec-driven"]["trace"] == "yes"
    assert _sdd.GATES_BY_STOP["spec-driven"]["contract"] == "—"
    assert _sdd.GATES_BY_STOP["contract-driven"]["contract"] == "yes"
    assert _sdd.GATES_BY_STOP["contract-driven"]["mutation"] == "—"
    assert all(v in ("yes", "fail") for v in _sdd.GATES_BY_STOP["evidentiary"].values())


def test_git_and_gh_dry_run(tmp_path, capsys):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    assert _sdd.git("rev-parse", "--is-inside-work-tree", root=tmp_path) == "true"
    with pytest.raises(_sdd.CommandError):
        _sdd.git("rev-parse", "--verify", "nope^{commit}", root=tmp_path)
    assert _sdd.gh(["issue", "create", "--title", "Two words"], dry_run=True) == ""
    assert "$ gh issue create --title 'Two words'" in capsys.readouterr().out
