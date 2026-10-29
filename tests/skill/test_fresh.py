"""fresh.py against a tiny fake git repo: fresh, drifting, stale, unverified, warn, --stamp."""
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".claude/skills/sdd/scripts/fresh.py"
GIT_ID = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *GIT_ID, *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def write(root: Path, name: str, text: str) -> None:
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(text)


def commit(root: Path, msg: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-qm", msg)


def make_repo(root: Path, alpha_stop: str = "evidentiary") -> Path:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    write(root, "sdd.yaml", "specs_dir: specs\nreq_pattern: 'REQ-[A-Z]+-\\d{3}'\ntest_dirs: [tests]\n")
    write(root, "specs/alpha/requirements.md",
          f"---\nid: alpha\nstop: {alpha_stop}\ncovers: [src/alpha/]\n"
          "verified_at: null         # stamped at docs stage\n---\n1. **REQ-ABC-001**: The thing shall work.\n")
    write(root, "specs/light/spec.md", "---\nstop: spec-light\ncovers: [tools/x.py]\nverified_at: null\n---\nok\n")
    write(root, "src/alpha/core.py", "VALUE = 1\n")
    write(root, "tools/x.py", "print('x')\n")
    write(root, "tests/test_alpha.py",
          "import pathlib\n\ndef test_" "REQ_ABC_001_works():\n"
          "    assert 'VALUE = 1' in (pathlib.Path(__file__).parents[1] / 'src/alpha/core.py').read_text()\n")
    commit(root, "seed")
    return root


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "SDD_PYTEST": f"{sys.executable} -m pytest -p no:cacheprovider"}
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True, env=env)


def stamp_all(root: Path) -> None:
    for spec_id in ("alpha", "light"):
        assert run(root, "--stamp", spec_id).returncode == 0
    commit(root, "stamp")


def status_of(out: str, spec_id: str) -> list[str]:
    return next(line.split() for line in out.splitlines() if line.startswith(spec_id + " "))


def test_unverified_fails_above_spec_light(tmp_path):
    r = run(make_repo(tmp_path))
    assert r.returncode == 1
    assert status_of(r.stdout, "alpha")[-2:] == ["unverified", "FAIL"]
    assert status_of(r.stdout, "light")[-2:] == ["unverified", "WARN"]


def test_stamp_rewrites_verified_at_and_keeps_comment(tmp_path):
    root = make_repo(tmp_path)
    head = git(root, "rev-parse", "--short", "HEAD")
    r = run(root, "--stamp", "alpha")
    assert r.returncode == 0 and head in r.stdout
    text = (root / "specs/alpha/requirements.md").read_text()
    assert f"verified_at: {head}" in text and "# stamped at docs stage" in text
    assert run(root, "--stamp", "nope").returncode == 1


def test_all_fresh_after_stamp(tmp_path):
    root = make_repo(tmp_path)
    stamp_all(root)
    r = run(root)
    assert r.returncode == 0, r.stdout
    assert status_of(r.stdout, "alpha")[-2:] == ["fresh", "ok"]
    assert status_of(r.stdout, "light")[-2:] == ["fresh", "ok"]


def test_code_change_without_spec_change_is_drifting(tmp_path):
    root = make_repo(tmp_path)
    stamp_all(root)
    write(root, "src/alpha/core.py", "VALUE = 1\nOTHER = 2\n")
    write(root, "tools/x.py", "print('y')\n")
    commit(root, "code only")
    r = run(root)
    assert r.returncode == 1
    assert status_of(r.stdout, "alpha")[-2:] == ["drifting", "FAIL"]
    assert status_of(r.stdout, "light")[-2:] == ["drifting", "WARN"]


def test_spec_updated_with_code_is_fresh(tmp_path):
    root = make_repo(tmp_path)
    stamp_all(root)
    write(root, "src/alpha/core.py", "VALUE = 1\nOTHER = 2\n")
    with (root / "specs/alpha/requirements.md").open("a") as f:
        f.write("2. **REQ-ABC-002**: The thing shall also do OTHER.\n")
    commit(root, "code and spec")
    assert status_of(run(root).stdout, "alpha")[-2] == "fresh"


def test_failing_req_test_on_drifting_spec_is_stale(tmp_path):
    root = make_repo(tmp_path)
    stamp_all(root)
    write(root, "src/alpha/core.py", "VALUE = 2\n")
    commit(root, "break it")
    r = run(root)
    assert r.returncode == 1
    assert "running its REQ tests" in r.stdout
    assert status_of(r.stdout, "alpha")[-2:] == ["stale", "FAIL"]


def test_spec_light_drift_only_warns(tmp_path):
    root = make_repo(tmp_path, alpha_stop="spec-light")
    stamp_all(root)
    write(root, "src/alpha/core.py", "VALUE = 1\nOTHER = 2\n")
    commit(root, "code only")
    r = run(root)
    assert r.returncode == 0, r.stdout
    assert status_of(r.stdout, "alpha")[-2:] == ["drifting", "WARN"]
