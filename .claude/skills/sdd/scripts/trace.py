#!/usr/bin/env python3
"""Requirement traceability: REQ ids <-> REQ-named tests <-> `# REQ-...` code anchors.

  trace.py            fail if an active REQ has no test, or a test/anchor names an unknown REQ
  trace.py --design   fail if an active REQ is missing from its spec's design.md
  trace.py --matrix   print (or --out FILE) a markdown REQ -> anchors -> tests matrix

Deferred REQs (`status: deferred`) are listed, never failed. Specs with no numbered REQs
(spec-light) are skipped. Paths come from sdd.yaml: specs_dir, test_dirs, code_dirs, req_pattern.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _sdd  # noqa: E402

TEST_RE = re.compile(r"def\s+(test_REQ_([A-Z]+)_(\d{3})\w*)")


def collect(config: dict) -> dict:
    """Gather REQs, tests, anchors and commit trailers into one structure."""
    pattern = config["req_pattern"]
    known: dict[str, dict] = {}
    for spec in _sdd.specs(config):
        rows = _sdd.reqs(spec["dir"] / "requirements.md", pattern)
        if not rows:
            print(f"trace: {spec['id']} ({spec['stop']}) has no numbered REQs: skipped", file=sys.stderr)
            continue
        for rid, status in rows:
            known[rid] = {"spec": spec, "status": status}
    tests: dict[str, list[str]] = {}
    for f in _sdd.walk(config, config["test_dirs"]):
        if f.suffix != ".py":
            continue
        for m in TEST_RE.finditer(f.read_text(errors="replace")):
            tests.setdefault(f"REQ-{m.group(2)}-{m.group(3)}", []).append(f"{_sdd.rel(f, config)}::{m.group(1)}")
    anchors: dict[str, list[str]] = {}
    for f in _sdd.walk(config, config["code_dirs"]):
        for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            if "#" in line:
                for rid in re.findall(pattern, line.split("#", 1)[1]):
                    anchors.setdefault(rid, []).append(f"{_sdd.rel(f, config)}:{n}")
    trailers: dict[str, int] = {}
    try:
        log = _sdd.git("log", "--format=%B", root=config["root"])
    except _sdd.CommandError:
        log = ""
    for line in log.splitlines():
        if line.strip().startswith("Spec-REQ:"):
            for rid in re.findall(pattern, line):
                trailers[rid] = trailers.get(rid, 0) + 1
    return {"known": known, "tests": tests, "anchors": anchors, "trailers": trailers}


def run_trace(config: dict) -> int:
    print(f"trace: reading REQs from {config['specs_dir']}/*/requirements.md, "
          f"tests from {', '.join(config['test_dirs'])}, anchors from {', '.join(config['code_dirs'])}")
    data = collect(config)
    known, tests, anchors, trailers = data["known"], data["tests"], data["anchors"], data["trailers"]
    rows, problems = [], []
    for rid, info in known.items():
        n_tests = len(tests.get(rid, []))
        if info["status"] == "deferred":
            result = "deferred (listed, not checked)"
        elif n_tests:
            result = "ok"
        else:
            result = "FAIL: no test"
            problems.append(f"{rid} is active but has no test named test_{rid.replace('-', '_')}_*")
        rows.append([rid, info["spec"]["id"], info["status"], n_tests, len(anchors.get(rid, [])),
                     trailers.get(rid, 0), result])
    for kind, found in (("test", tests), ("anchor", anchors)):
        for rid in sorted(set(found) - set(known)):
            problems.append(f"{kind} names {rid}, which no requirements.md defines: {found[rid][0]}")
    for rid in sorted(set(trailers) - set(known)):
        print(f"trace: warning: Spec-REQ trailer names unknown {rid}")
    if rows:
        print(_sdd.table(["REQ", "spec", "status", "tests", "anchors", "commits", "result"], rows))
    else:
        print("trace: no numbered REQs found")
    for p in problems:
        print(f"FAIL: {p}")
    print(f"\ntrace: {len(known)} REQ(s), {len(problems)} problem(s): {'FAIL' if problems else 'PASS'}")
    return 1 if problems else 0


def run_design(config: dict) -> int:
    print("trace --design: every active REQ must appear in its spec's design.md "
          "(or, for a spec with no design.md of its own, in another spec's design.md)")
    all_specs = _sdd.specs(config)
    designs = {s["id"]: (s["dir"] / "design.md").read_text() for s in all_specs if (s["dir"] / "design.md").is_file()}
    rows, missing = [], 0
    for spec in all_specs:
        rows_for = _sdd.reqs(spec["dir"] / "requirements.md", config["req_pattern"])
        if not rows_for:
            continue
        own = designs.get(spec["id"])
        for rid, status in rows_for:
            where = [sid for sid, text in designs.items() if rid in text]
            if status == "deferred":
                ok = "deferred (not required)"
            elif own is not None:
                ok = "mapped" if rid in own else "FAIL: not in design.md"
            else:
                ok = f"mapped in {where[0]}/design.md" if where else "FAIL: in no design.md"
            missing += ok.startswith("FAIL")
            rows.append([rid, spec["id"], status, ok])
    print(_sdd.table(["REQ", "spec", "status", "design"], rows) if rows else "trace: no numbered REQs found")
    print(f"\ntrace --design: {missing} unmapped: {'FAIL' if missing else 'PASS'}")
    return 1 if missing else 0


def build_matrix(config: dict) -> str:
    data = collect(config)
    lines = ["| REQ | status | code anchors | tests |", "| --- | --- | --- | --- |"]
    for rid, info in data["known"].items():
        anchors = "<br>".join(f"`{a}`" for a in data["anchors"].get(rid, [])) or "none"
        tests = "<br>".join(f"`{t}`" for t in data["tests"].get(rid, [])) or "none"
        lines.append(f"| {rid} | {info['status']} | {anchors} | {tests} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", action="store_true", help="check every active REQ is in design.md")
    ap.add_argument("--matrix", action="store_true", help="write the REQ -> anchors -> tests matrix")
    ap.add_argument("--out", help="with --matrix: write the markdown here instead of stdout")
    args = ap.parse_args(argv)
    config = _sdd.load_config()
    if args.design:
        return run_design(config)
    if args.matrix:
        md = build_matrix(config)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(md)
            print(f"trace --matrix: wrote {args.out}")
        else:
            print(md, end="")
        return 0
    return run_trace(config)


if __name__ == "__main__":
    sys.exit(main())
