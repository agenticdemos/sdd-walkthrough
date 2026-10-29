#!/usr/bin/env python3
"""Design<->code freshness, computed from git.

  fresh.py               classify every spec: fresh | drifting | stale | unverified
  fresh.py --stamp SPEC  set SPEC's verified_at to HEAD (only after the spec was checked against the code)

drifting:   files in `covers` changed since `verified_at` and the spec's own files did not.
stale:      drifting (or unverified) AND a REQ-named test for that spec fails.
unverified: verified_at is null; treated as drifting.
Enforcement follows the stop: warn for spec-light, fail above it.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _sdd  # noqa: E402

VERIFIED_RE = re.compile(r"^(verified_at:[ \t]*)([^#\n]*?)([ \t]*#.*)?$", re.M)


def spec_changed(config: dict, spec: dict, since: str) -> bool:
    """True if the spec's files changed since `since`, ignoring verified_at stamp lines."""
    diff = _sdd.git("diff", "-U0", f"{since}..HEAD", "--", _sdd.rel(spec["dir"], config), root=config["root"])
    for line in diff.splitlines():
        if line.startswith(("+++", "---")) or not line.startswith(("+", "-")):
            continue
        if not line[1:].lstrip().startswith("verified_at:"):
            return True
    return False


def req_tests_fail(config: dict, spec: dict) -> bool:
    """Run the spec's REQ-named tests; True if any fail."""
    req_file = spec["dir"] / "requirements.md"
    areas = sorted({rid.split("-")[1] for rid, _ in _sdd.reqs(req_file, config["req_pattern"])})
    if not areas:
        return False
    expr = " or ".join(f"test_REQ_{a}" for a in areas)
    cmd = shlex.split(os.environ.get("SDD_PYTEST", "uv run pytest")) + ["-q", "-k", expr, *config["test_dirs"]]
    print(f"fresh: {spec['id']} is drifting; running its REQ tests: $ {shlex.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=config["root"], capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
    print(f"fresh:   -> exit {r.returncode}: {tail}")
    return r.returncode not in (0, 5)  # 5 = no tests collected


def classify(config: dict, spec: dict) -> tuple[str, str, str]:
    """(status, covered files changed, spec changed)."""
    va = spec["verified_at"]
    if va is None:
        status = "unverified"
        covered, changed = "?", "?"
    else:
        try:
            _sdd.git("rev-parse", "--verify", f"{va}^{{commit}}", root=config["root"])
        except _sdd.CommandError:
            print(f"fresh: {spec['id']}: verified_at {va} is not a commit here; treating as unverified")
            va = None
        if va is None:
            status, covered, changed = "unverified", "?", "?"
        else:
            files = _sdd.git("diff", "--name-only", f"{va}..HEAD", "--", *spec["covers"],
                             root=config["root"]).split() if spec["covers"] else []
            spec_moved = spec_changed(config, spec, va)
            covered, changed = str(len(files)), "yes" if spec_moved else "no"
            status = "drifting" if files and not spec_moved else "fresh"
    if status != "fresh" and req_tests_fail(config, spec):
        status = "stale"
    return status, covered, changed


def check(config: dict) -> int:
    all_specs = _sdd.specs(config)
    print(f"fresh: comparing each spec's verified_at with HEAD over its covers ({len(all_specs)} spec(s))")
    rows, failed = [], []
    for spec in all_specs:
        status, covered, changed = classify(config, spec)
        level = _sdd.GATES_BY_STOP.get(spec["stop"], {}).get("fresh", "fail")
        if status == "fresh":
            result = "ok"
        elif level == "warn":
            result = "WARN"
        elif level == "fail":
            result = "FAIL"
            failed.append(spec["id"])
        else:
            result = "ignored"
        rows.append([spec["id"], spec["stop"], spec["verified_at"] or "null", covered, changed, status, result])
    if rows:
        print(_sdd.table(["spec", "stop", "verified_at", "covered files changed", "spec changed",
                          "status", "result"], rows))
    else:
        print("fresh: no specs found")
    if failed:
        print(f"\nFAIL: not fresh at a stop that enforces freshness: {', '.join(failed)}")
        return 1
    print("\nPASS: no spec above spec-light is drifting or stale")
    return 0


def stamp(config: dict, spec_id: str) -> int:
    match = [s for s in _sdd.specs(config) if s["id"] == spec_id]
    if not match:
        print(f"fresh: no spec with id {spec_id!r}")
        return 1
    spec = match[0]
    sha = _sdd.git("rev-parse", "--short", "HEAD", root=config["root"])
    value = f'"{sha}"' if re.fullmatch(r"[\d_]+|\d+e\d+", sha) else sha  # keep YAML from reading it as a number
    text = spec["path"].read_text()
    m = re.match(r"---[ \t]*\n(.*?\n)---", text, re.S)
    if not m:
        print(f"fresh: {spec['path']} has no front matter")
        return 1
    fm = m.group(1)
    if VERIFIED_RE.search(fm):
        fm = VERIFIED_RE.sub(lambda g: g.group(1) + value + (g.group(3) or ""), fm, count=1)
    else:
        fm += f"verified_at: {value}\n"
    spec["path"].write_text(text[:m.start(1)] + fm + text[m.end(1):])
    print(f"fresh: stamped {spec_id} verified_at: {sha} (HEAD) in {_sdd.rel(spec['path'], config)}")
    print("fresh: commit this only after a human or the reviewer subagent checked the spec against the code")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stamp", metavar="SPEC", help="rewrite SPEC's verified_at to HEAD's short sha")
    args = ap.parse_args(argv)
    config = _sdd.load_config()
    return stamp(config, args.stamp) if args.stamp else check(config)


if __name__ == "__main__":
    sys.exit(main())
