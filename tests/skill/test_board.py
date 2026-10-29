"""board.py: bootstrap / move / reset against a fake repo with dry-run or mocked gh."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude/skills/sdd/scripts"))
import _sdd  # noqa: E402
import board  # noqa: E402

SDD_YAML = """\
specs_dir: specs
base_branch: main
req_pattern: 'REQ-[A-Z]+-\\d{3}'
board:
  repo: someorg/somerepo
  owner: someorg
  project: Demo board
  tasks: specs/demo/tasks.yaml
  statuses: [Todo, In progress, In review, Landing, Done]
  owners: [person-a, person-b]
  gates: [G0, G1, G2, G3]
  seed:
    TASK-01: Done
    TASK-02: In progress
"""
SPEC = """---
stop: evidentiary
covers: [src/demo/]
verified_at: null
owner: person-a
---
# Demo
- REQ-DEM-001: The system shall add.
- REQ-DEM-002: The system shall subtract.
"""
TASKS = """\
tasks:
  - id: TASK-01
    title: Adder
    reqs: [REQ-DEM-001]
    design: "§1 adder"
    area: src/demo/add.py
    done: adds two numbers
    owner: person-a
    gate: G1
  - id: TASK-02
    title: Subtractor
    reqs: [REQ-DEM-002]
    design: "§2 subtractor"
    area: src/demo/sub.py
    done: subtracts
    owner: person-a, person-b
    gate: after G1
"""
FIELDS = {"fields": [
    {"id": "F_STATUS", "name": "Status", "type": "ProjectV2SingleSelectField",
     "options": [{"id": f"S_{s}", "name": s} for s in ["Todo", "In progress", "In review", "Landing", "Done"]]},
    {"id": "F_REQS", "name": "REQs", "type": "ProjectV2Field"},
    {"id": "F_GATE", "name": "Gate", "type": "ProjectV2SingleSelectField",
     "options": [{"id": f"G_{g}", "name": g} for g in ["G0", "G1", "G2", "G3"]]},
]}


@pytest.fixture
def cfg(tmp_path):
    (tmp_path / "sdd.yaml").write_text(SDD_YAML)
    (tmp_path / "specs/demo").mkdir(parents=True)
    (tmp_path / "specs/demo/requirements.md").write_text(SPEC)
    (tmp_path / "specs/demo/tasks.yaml").write_text(TASKS)
    return _sdd.load_config(tmp_path)


class FakeGh:
    def __init__(self, fields=FIELDS, issues=()):
        self.calls, self.fields, self.issues, self.next = [], fields, list(issues), 100

    def __call__(self, args, dry_run):
        assert not dry_run
        self.calls.append(args)
        a = args[:2]
        if a == ["project", "list"]:
            return json.dumps({"projects": [{"number": 7, "id": "PVT_1", "title": "Demo board"}]})
        if a == ["project", "field-list"]:
            return json.dumps(self.fields)
        if a == ["issue", "list"]:
            return json.dumps(self.issues)
        if a == ["issue", "create"]:
            self.next += 1
            return f"https://github.com/someorg/somerepo/issues/{self.next}"
        if a == ["project", "item-add"]:
            return json.dumps({"id": "PVTI_x"})
        if args[0] == "api" and args[1].endswith("/sub_issues"):
            return "[]"
        if args[0] == "api" and "--jq" in args:
            return "555"
        return ""

    def find(self, *prefix):
        return [c for c in self.calls if c[:len(prefix)] == list(prefix)]


def test_bootstrap_dry_run_prints_every_gh_command(cfg, capsys):
    board.bootstrap(cfg, dry=True)
    out = capsys.readouterr().out
    for label in ["feature", "task", "ready-to-land", "ejected", "drift", "contract-change"]:
        assert f"$ gh label create {label} --repo someorg/somerepo" in out
    assert "--force" in out
    assert "TASK-01 · Adder" in out and "TASK-02 · Subtractor" in out
    assert "/sub_issues' -F 'sub_issue_id=" in out
    assert "--single-select-option-id '<In progress>'" in out  # seed status for TASK-02
    assert "--single-select-option-id '<G1>'" in out           # 'after G1' -> G1


def test_bootstrap_is_idempotent_and_creates_only_missing(cfg):
    existing = [{"number": 1, "title": "demo · feature", "url": "https://github.com/someorg/somerepo/issues/1"},
                {"number": 2, "title": "TASK-01 · Adder", "url": "https://github.com/someorg/somerepo/issues/2"}]
    default_status = {"fields": [{"id": "F_STATUS", "name": "Status", "type": "ProjectV2SingleSelectField",
                                  "options": [{"id": "a", "name": "Todo"}, {"id": "b", "name": "In Progress"},
                                              {"id": "c", "name": "Done"}]}]}
    gh = FakeGh(fields=default_status, issues=existing)
    _sdd.gh, saved = gh, _sdd.gh
    try:
        board.bootstrap(cfg, dry=False)
    finally:
        _sdd.gh = saved
    created = [c[c.index("--title") + 1] for c in gh.find("issue", "create")]
    assert created == ["TASK-02 · Subtractor"]          # feature and TASK-01 already exist
    assert not gh.find("project", "create")             # project exists
    made = [c[c.index("--name") + 1] for c in gh.find("project", "field-create")]
    assert made == ["REQs", "Dial stop", "Gate", "Owner"]
    gql = gh.find("api", "graphql")
    assert gql and '"In progress"' in gql[0][-1] and 'id: "a"' in gql[0][-1]
    posts = gh.find("api", "-X", "POST")
    assert len(posts) == 2 and posts[0][3].endswith("/issues/1/sub_issues") and "sub_issue_id=555" in posts[0]


def test_move_sets_status_and_comments(cfg, monkeypatch):
    gh = FakeGh(issues=[{"number": 9, "title": "TASK-02 · Subtractor", "url": "https://x/9"}])
    monkeypatch.setattr(_sdd, "gh", gh)
    board.move(cfg, "TASK-02", "Done", pr="12", evidence="https://ci/run/1")
    edit = gh.find("project", "item-edit")
    assert edit and edit[0][-2:] == ["--single-select-option-id", "S_Done"]
    comment = gh.find("issue", "comment")[0]
    assert comment[2] == "9" and "PR #12" in comment[-1] and "https://ci/run/1" in comment[-1]


def test_move_rejects_unknown_status(cfg, monkeypatch):
    monkeypatch.setattr(_sdd, "gh", FakeGh())
    with pytest.raises(SystemExit):
        board.move(cfg, "TASK-01", "Shipped")


def test_reset_restores_seed(cfg, monkeypatch):
    gh = FakeGh(issues=[{"number": 2, "title": "TASK-01 · Adder", "url": "u2"},
                        {"number": 3, "title": "TASK-02 · Subtractor", "url": "u3"}])
    monkeypatch.setattr(_sdd, "gh", gh)
    board.reset(cfg, dry=False)
    opts = [c[-1] for c in gh.find("project", "item-edit")]
    assert opts == ["S_Done", "S_In progress"]
    assert not gh.find("issue", "comment")
