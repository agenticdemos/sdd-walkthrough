"""land.py: scripted queue against a real local git origin with mocked gh."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude/skills/sdd/scripts"))
import _sdd  # noqa: E402
import land  # noqa: E402

SDD_YAML = """\
base_branch: main
landing:
  label: ready-to-land
  ejected_label: ejected
  check: python3 check.py
board:
  repo: someorg/somerepo
"""
CHECK = """\
import pathlib, sys
if pathlib.Path("bad.txt").exists():
    print("FAILED tests/unit/test_flags.py::test_REQ_ALW_003_flag_from_2027 - AssertionError")
    sys.exit(1)
print("all green")
"""


def sh(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    empty = tmp_path / "gitconfig"
    empty.write_text("")
    for k, v in {"GIT_CONFIG_GLOBAL": str(empty), "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "t",
                 "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
                 "GIT_COMMITTER_EMAIL": "t@example.com"}.items():
        monkeypatch.setenv(k, v)
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    (work / "sdd.yaml").write_text(SDD_YAML)
    (work / "check.py").write_text(CHECK)
    sh(work, "add", ".")
    sh(work, "commit", "-qm", "base")
    sh(work, "remote", "add", "origin", str(origin))
    sh(work, "push", "-q", "origin", "main")
    for branch, fname, text in [("pr1", "a.txt", "one"), ("pr2", "bad.txt", "x"),
                                ("pr3", "c.txt", "three"), ("pr4", "a.txt", "clash")]:
        sh(work, "checkout", "-q", "-b", branch, "main")
        (work / fname).write_text(text)
        sh(work, "add", fname)
        sh(work, "commit", "-qm", branch)
        sh(work, "push", "-q", "origin", branch)
        sh(work, "checkout", "-q", "main")
    return work, origin


PRS = [  # deliberately out of order: land.py sorts by createdAt
    {"number": 2, "title": "Sub-limit flag", "headRefName": "act6/TASK-07-flag", "createdAt": "2026-01-02T00:00:00Z"},
    {"number": 1, "title": "TASK-01 · tax-year label", "headRefName": "pr1", "createdAt": "2026-01-01T00:00:00Z"},
    {"number": 4, "title": "clash", "headRefName": "pr4", "createdAt": "2026-01-04T00:00:00Z"},
    {"number": 3, "title": "Glossary", "headRefName": "pr3", "createdAt": "2026-01-03T00:00:00Z"},
]


def test_land_lands_green_and_ejects_red_and_conflicts(repo, monkeypatch):
    work, origin = repo
    sh(work, "push", "-q", "origin", "pr2:act6/TASK-07-flag")
    calls, moves = [], []

    def fake_gh(args, dry_run):
        calls.append(args)
        return json.dumps(PRS) if args[:2] == ["pr", "list"] else ""

    monkeypatch.setattr(_sdd, "gh", fake_gh)
    monkeypatch.setattr(land.board, "move", lambda cfg, task, status, **kw: moves.append((task, status, kw["pr"])))
    cfg = _sdd.load_config(work)
    landed, ejected, before, after = land.land(cfg, "main", dry=False)

    assert landed == [1, 3]
    assert [n for n, _ in ejected] == [2, 4]
    assert "test_REQ_ALW_003_flag_from_2027" in ejected[0][1] and ejected[1][1] == "rebase conflict"
    assert before != after and after == sh(origin, "rev-parse", "main")
    files = sh(origin, "ls-tree", "--name-only", "main").split()
    assert "a.txt" in files and "c.txt" in files and "bad.txt" not in files
    comment = next(c for c in calls if c[:3] == ["pr", "comment", "2"])
    assert "tests/unit/test_flags.py::test_REQ_ALW_003_flag_from_2027" in comment[-1]
    assert ["pr", "edit", "2", "--remove-label", "ready-to-land", "--add-label", "ejected"] in calls
    assert moves == [("TASK-01", "Done", 1), ("TASK-07", "In progress", 2)]  # PR 3/4 carry no TASK id
    assert sh(work, "rev-parse", "--abbrev-ref", "HEAD") == "main"


def test_land_dry_run_prints_queue_query(repo, capsys):
    work, _ = repo
    land.land(_sdd.load_config(work), "demo/trunk", dry=True)
    out = capsys.readouterr().out
    assert "$ gh pr list --base demo/trunk --label ready-to-land" in out
    assert "queue for demo/trunk: empty" in out


def test_failing_tests_parses_pytest_summary():
    out = "x\nFAILED tests/a.py::test_one - boom\nFAILED tests/b.py::test_two\nERROR other\n"
    assert land.failing_tests(out) == ["tests/a.py::test_one", "tests/b.py::test_two"]
