"""dial.py against a tiny fake repo; gate commands are stand-in python one-liners."""
import shlex
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".claude/skills/sdd/scripts/dial.py"
PY = shlex.quote(sys.executable)


def spec(stop: str) -> str:
    return f"---\nstop: {stop}\ncovers: [src/]\nverified_at: null\n---\nBody\n"


def make_repo(root: Path, stops: dict[str, str], gates: dict[str, str]) -> Path:
    lines = ["specs_dir: specs", "gates:"] + [f"  {g}: {cmd}" for g, cmd in gates.items()]
    (root / "sdd.yaml").write_text("\n".join(lines) + "\n")
    for name, stop in stops.items():
        (root / "specs" / name).mkdir(parents=True)
        (root / "specs" / name / "requirements.md").write_text(spec(stop))
    return root


def ok(name: str) -> str:
    return f"{PY} -c \"print('{name} ran')\""


def bad(name: str) -> str:
    return f"{PY} -c \"import sys; print('{name} ran'); sys.exit(3)\""


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True)


def test_table_lists_each_spec_stop_and_gates(tmp_path):
    root = make_repo(tmp_path, {"alpha": "evidentiary", "beta": "contract-driven", "gamma": "spec-light"}, {})
    r = run(root)
    assert r.returncode == 0
    rows = {line.split()[0]: line.split()[1:] for line in r.stdout.splitlines()
            if line.split() and line.split()[0] in ("alpha", "beta", "gamma")}
    assert rows["alpha"] == ["evidentiary", "yes", "yes", "fail", "yes", "yes", "yes"]
    assert rows["beta"] == ["contract-driven", "yes", "yes", "fail", "yes", "—", "—"]
    assert rows["gamma"] == ["spec-light", "yes", "—", "warn", "—", "—", "—"]
    assert "make check runs: unit, trace, fresh, contract, mutation, evidence" in r.stdout


def test_check_runs_only_required_gates_in_order(tmp_path):
    gates = {g: ok(g) for g in ("unit", "trace", "fresh", "contract", "mutation", "evidence")}
    root = make_repo(tmp_path, {"beta": "contract-driven"}, gates)
    r = run(root, "--check")
    assert r.returncode == 0, r.stdout
    order = [line.split()[0] for line in r.stdout.splitlines() if line.endswith(" ran")]
    assert order == ["unit", "trace", "fresh", "contract"]
    assert "mutation ran" not in r.stdout and "PASS: every required gate passed" in r.stdout


def test_check_fails_when_a_required_gate_fails(tmp_path):
    root = make_repo(tmp_path, {"alpha": "evidentiary"},
                     {"unit": ok("unit"), "trace": bad("trace"), "fresh": ok("fresh"),
                      "contract": ok("contract"), "mutation": ok("mutation"), "evidence": ok("evidence")})
    r = run(root, "--check")
    assert r.returncode == 1
    assert "evidence ran" in r.stdout  # keeps going so the summary is complete
    assert "FAIL: required gate(s) failed: trace" in r.stdout


def test_freshness_is_warn_only_when_every_spec_needing_it_is_spec_light(tmp_path):
    root = make_repo(tmp_path, {"gamma": "spec-light"}, {"unit": ok("unit"), "fresh": bad("fresh")})
    r = run(root, "--check")
    assert r.returncode == 0, r.stdout
    assert "WARN" in r.stdout
    (root / "specs" / "delta").mkdir()
    (root / "specs" / "delta" / "requirements.md").write_text(spec("spec-driven"))
    r = run(root, "--check")
    assert r.returncode == 1  # spec-driven makes freshness a hard gate, and trace has no command
    assert "fresh" in r.stdout.split("FAIL: required gate(s) failed:")[1]


def test_no_specs_means_nothing_required(tmp_path):
    root = make_repo(tmp_path, {}, {"unit": bad("unit")})
    assert run(root).returncode == 0
    assert run(root, "--check").returncode == 0
