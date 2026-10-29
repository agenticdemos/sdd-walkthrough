#!/usr/bin/env python3
"""Mutation gate: run mutmut, list survivors, fail on any survivor without a valid waiver.

Paths come from sdd.yaml (mutation.targets, mutation.waivers, mutation.approvers); mutmut's own
config (which files to mutate) lives in setup.cfg [mutmut]. A waiver counts only when its
reviewed_by is a role in mutation.approvers. The gate is enforced when a spec covering the
targets is at the evidentiary stop; otherwise survivors are reported as advisory.
Standard library plus the mutmut CLI (via `uv run`).
"""
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sdd import load_config, parse_yaml, specs, table  # noqa: E402

NOT_KILLED = {"survived", "no tests", "suspicious", "timeout"}


def run(cmd: list[str], root: Path) -> subprocess.CompletedProcess:
    print("$ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=root, capture_output=True, text=True)


def in_targets(mutant: str, targets: list[str]) -> bool:
    module = mutant.split(".x_")[0].replace(".", "/") if ".x_" in mutant else mutant.replace(".", "/")
    return any(module.startswith(t.removeprefix("src/").rstrip("/")) for t in targets)


def main() -> int:
    cfg = load_config()
    root, mut = cfg["root"], cfg.get("mutation", {}) or {}
    targets = list(mut.get("targets", []))
    approvers = set(mut.get("approvers", []))
    print(f"mutation targets (sdd.yaml): {', '.join(targets)}")

    covering = [s for s in specs(cfg) if any(t.startswith(c) for c in s.get("covers") or [] for t in targets)]
    enforce = any(s.get("stop") == "evidentiary" for s in covering)
    print("specs covering targets: " + (", ".join(f"{s['id']} ({s['stop']})" for s in covering) or "none"))
    print("gate: " + ("ENFORCED (evidentiary)" if enforce else "advisory (no evidentiary spec)"))

    # mutmut caches results per mutant and does not re-test when only tests change, so a new
    # killing test would be ignored. Start clean every time; the rules area runs in seconds.
    if (root / "mutants").exists():
        print("clearing mutmut cache: mutants/")
        shutil.rmtree(root / "mutants")

    started = time.monotonic()
    proc = run(["uv", "run", "mutmut", "run"], root)
    elapsed = time.monotonic() - started
    if proc.returncode != 0:
        print(proc.stdout[-2000:] + proc.stderr[-2000:])
        print(f"mutmut run failed (exit {proc.returncode})")
        return 1
    summary = proc.stdout.replace("\r", "\n").strip().splitlines()
    print(f"mutmut run finished in {elapsed:.1f}s; last status: {summary[-2] if len(summary) > 1 else ''}")

    results = run(["uv", "run", "mutmut", "results"], root)
    survivors = []
    for line in results.stdout.splitlines():
        m = re.match(r"\s*(\S+): (.+)$", line)
        if m and m.group(2).strip() in NOT_KILLED and in_targets(m.group(1), targets):
            survivors.append((m.group(1), m.group(2).strip()))

    path = root / mut.get("waivers", "mutation-waivers.yaml")
    data = parse_yaml(path.read_text()) if path.is_file() else {}
    waivers = {w.get("mutant"): w for w in (data or {}).get("waivers") or [] if isinstance(w, dict)}
    print(f"waivers: {path.relative_to(root)} ({len(waivers)} listed); approvers: {', '.join(sorted(approvers))}")

    rows, unwaived = [], 0
    for mutant, status in survivors:
        w = waivers.get(mutant)
        reviewer = (w or {}).get("reviewed_by") or ""
        if not w:
            verdict = "UNWAIVED"
        elif reviewer not in approvers:
            verdict = f"UNWAIVED (reviewed_by {reviewer or 'empty'} is not an approver)"
        else:
            verdict = f"waived by {reviewer}: {w.get('reason', '')}"
        unwaived += verdict.startswith("UNWAIVED")
        rows.append([mutant, status, verdict])
    if rows:
        print(table(["mutant", "status", "waiver"], rows))
        print("inspect one with: uv run mutmut show <mutant>")
    print(f"{len(survivors)} survivor(s), {unwaived} unwaived, mutmut wall time {elapsed:.1f}s")
    if unwaived and enforce:
        print("FAIL: unwaived survivors. Kill them with a test or record a reviewed waiver; never change src/.")
        return 1
    print("no unwaived survivors" if not unwaived else "advisory only: survivors not enforced at this stop")
    return 0


if __name__ == "__main__":
    sys.exit(main())
