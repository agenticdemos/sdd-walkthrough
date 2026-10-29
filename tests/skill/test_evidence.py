"""evidence.py: writes all six files for a spec at a sha (commands and gh mocked)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude/skills/sdd/scripts"))
import _sdd  # noqa: E402
import evidence  # noqa: E402

SDD_YAML = """\
specs_dir: specs
req_pattern: 'REQ-[A-Z]+-\\d{3}'
test_dirs: [tests]
evidence_dir: evidence
gates:
  mutation: make mutate
mutation:
  waivers: mutation-waivers.yaml
  approvers: [person-a, person-b]
"""
SPEC = """---
stop: evidentiary
covers: [src/demo/]
owner: person-a
---
- REQ-DEM-001: When asked, the system shall add.
  approver: [product owner]
- REQ-DEM-002: The system shall subtract.
- REQ-DEM-003: The system shall divide. status: deferred
"""
JUNIT = """<?xml version="1.0"?><testsuites><testsuite name="pytest">
<testcase classname="t" name="test_REQ_DEM_001_adds"/>
<testcase classname="t" name="test_REQ_DEM_001_adds_zero"/>
<testcase classname="t" name="test_REQ_DEM_002_subtracts"><failure message="boom"/></testcase>
</testsuite></testsuites>"""
PR = {"number": 5, "author": {"login": "presenter"}, "mergedAt": "2026-10-29T10:00:00Z",
      "body": "Contract v1\n\n- [x] person-a approves\n- [ ] person-b approves\n- [x] mallory approves\n",
      "reviews": [{"author": {"login": "bot"}, "state": "COMMENTED", "submittedAt": "2026-10-29T09:00:00Z"}]}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "sdd.yaml").write_text(SDD_YAML)
    (tmp_path / "specs/demo").mkdir(parents=True)
    (tmp_path / "specs/demo/requirements.md").write_text(SPEC)
    (tmp_path / "mutation-waivers.yaml").write_text("waivers: []\n")
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run([*git, "add", "."], cwd=tmp_path, check=True)
    subprocess.run([*git, "commit", "-qm", "spec"], cwd=tmp_path, check=True)
    ran = []

    def fake_run(cmd, cwd):
        ran.append(cmd)
        if isinstance(cmd, list) and any(str(c).startswith("--junitxml=") for c in cmd):
            Path(next(c for c in cmd if c.startswith("--junitxml="))[11:]).write_text(JUNIT)
            return 1, "1 failed, 2 passed"
        if isinstance(cmd, list) and "--matrix" in cmd:
            return 0, "| REQ | code | tests |\n|---|---|---|\n"
        return 0, "mutants: 12 killed, 0 survived\n"

    monkeypatch.setattr(evidence, "run", fake_run)
    return tmp_path, ran


def test_writes_six_files_and_ties_reqs(repo, monkeypatch):
    root, ran = repo
    monkeypatch.setattr(_sdd, "gh", lambda args, dry_run: json.dumps(PR))
    sha = _sdd.git("rev-parse", "HEAD", root=root)
    out = evidence.build(_sdd.load_config(root), "demo", pr="5")
    assert out == root / "evidence" / "demo" / sha
    assert sorted(p.name for p in out.iterdir()) == sorted(
        ["spec.md", "trace.md", "junit.xml", "mutation.txt", "review.json", "README.md"])
    spec = (out / "spec.md").read_text()
    assert "sha256: `" in spec and "approver: [product owner]" in spec and "REQ-DEM-002" in spec
    review = json.loads((out / "review.json").read_text())
    assert review["pr"] == 5 and review["author"] == "presenter"
    assert review["role_approvals"] == ["person-a"]  # unticked and non-role lines ignored
    assert review["github_reviews"][0]["state"] == "COMMENTED"
    readme = (out / "README.md").read_text()
    assert "| REQ-DEM-001 | active | 2/2 passed |" in readme
    assert "| REQ-DEM-002 | active | 0/1 passed |" in readme
    assert "| REQ-DEM-003 | deferred | deferred |" in readme
    assert "12 killed" in (out / "mutation.txt").read_text() and "waivers: []" in (out / "mutation.txt").read_text()
    assert "make mutate" in ran


def test_no_pr_records_null(repo, monkeypatch):
    root, _ = repo
    monkeypatch.setattr(_sdd, "gh", lambda *a: pytest.fail("gh must not be called without --pr"))
    out = evidence.build(_sdd.load_config(root), "demo", sha="abc123")
    assert json.loads((out / "review.json").read_text()) == {"pr": None}
    assert out.name == "abc123"


def test_unknown_spec_exits(repo):
    root, _ = repo
    with pytest.raises(SystemExit):
        evidence.build(_sdd.load_config(root), "nope")
