"""trace.py against a tiny fake repo (git init in tmp_path); never reads this repo's specs."""
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".claude/skills/sdd/scripts/trace.py"

REQS = """---
id: alpha
stop: evidentiary
covers: [src/alpha/]
verified_at: null
---
1. **REQ-ABC-001** (ubiquitous): The thing shall work.
2. **REQ-ABC-002** (event): WHEN asked, the thing shall answer.
3. **REQ-ABC-003** (optional feature, `status: deferred`): WHERE flexible, the thing shall bend.
"""


def make_repo(root: Path, tests: str, code: str = "X = 1  # REQ-ABC-001\n", design: str | None = None) -> Path:
    files = {
        "sdd.yaml": "specs_dir: specs\nreq_pattern: 'REQ-[A-Z]+-\\d{3}'\ntest_dirs: [tests]\ncode_dirs: [src]\n",
        "specs/alpha/requirements.md": REQS,
        "specs/light/spec.md": "---\nstop: spec-light\ncovers: [src/light.py]\nverified_at: null\n---\nThree checks.\n",
        "src/alpha/core.py": code,
        "tests/test_alpha.py": fake_tests(tests),
    }
    if design is not None:
        files["specs/alpha/design.md"] = design
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "seed\n\nSpec-REQ: REQ-ABC-001"], check=True)
    return root


def fake_tests(text: str) -> str:
    """Fake-repo test source; spelt with TESTX so this repo's own trace never reads it as a REQ test."""
    return text.replace("TESTX", "test_REQ")


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True)


BOTH = "def TESTX_ABC_001_works():\n    pass\n\ndef TESTX_ABC_002_answers():\n    pass\n"


def test_passes_when_every_active_req_has_a_test(tmp_path):
    r = run(make_repo(tmp_path, BOTH))
    assert r.returncode == 0, r.stdout
    assert "PASS" in r.stdout
    assert "REQ-ABC-003" in r.stdout and "deferred" in r.stdout  # listed, not failed
    assert "light" in r.stderr and "skipped" in r.stderr  # spec-light has no numbered REQs


def test_fails_when_active_req_has_no_test(tmp_path):
    r = run(make_repo(tmp_path, "def TESTX_ABC_001_works():\n    pass\n"))
    assert r.returncode == 1
    assert "REQ-ABC-002 is active but has no test" in r.stdout


def test_fails_when_test_or_anchor_names_unknown_req(tmp_path):
    tests = BOTH + "def TESTX_ABC_009_ghost():\n    pass\n"
    r = run(make_repo(tmp_path, tests, code="Y = 2  # REQ-ZZZ-001\n"))
    assert r.returncode == 1
    assert "test names REQ-ABC-009" in r.stdout
    assert "anchor names REQ-ZZZ-001" in r.stdout


def test_design_mode(tmp_path):
    root = make_repo(tmp_path, BOTH, design="| REQ | component |\n| REQ-ABC-001 | core |\n")
    r = run(root, "--design")
    assert r.returncode == 1 and "REQ-ABC-002" in r.stdout and "not in design.md" in r.stdout
    (root / "specs/alpha/design.md").write_text("REQ-ABC-001 core\nREQ-ABC-002 core\n")
    r = run(root, "--design")
    assert r.returncode == 0, r.stdout  # deferred REQ-ABC-003 is not required


def test_matrix_mode(tmp_path):
    root = make_repo(tmp_path, BOTH)
    r = run(root, "--matrix", "--out", "out/trace.md")
    assert r.returncode == 0
    md = (root / "out/trace.md").read_text()
    assert md.startswith("| REQ | status | code anchors | tests |")
    assert "| REQ-ABC-001 | active | `src/alpha/core.py:1` | `tests/test_alpha.py::test_REQ_ABC_001_works` |" in md
    assert "| REQ-ABC-003 | deferred | none | none |" in md
