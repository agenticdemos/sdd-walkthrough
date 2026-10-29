#!/usr/bin/env python3
"""The criticality dial, made executable.

  dial.py           one-screen table: every spec, its stop, and the gates that apply
  dial.py --check   run every gate the strictest spec requires (this is `make check`)

Gate levels come from each spec's front matter `stop:`; gate commands come from sdd.yaml `gates:`.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _sdd  # noqa: E402

RANK = {_sdd._N: 0, "warn": 1, "yes": 2, "fail": 2}


def required_gates(all_specs: list[dict]) -> dict[str, str]:
    """Union of gates over all specs; the strictest level wins.

    A gate is "warn" only if every spec that needs it asks for warn (e.g. freshness on spec-light)."""
    need: dict[str, str] = {g: _sdd._N for g in _sdd.GATES}
    for spec in all_specs:
        levels = _sdd.GATES_BY_STOP.get(spec["stop"])
        if levels is None:
            raise SystemExit(f"dial: spec {spec['id']} has unknown stop {spec['stop']!r}; "
                             f"expected one of {', '.join(_sdd.STOPS)}")
        for gate, level in levels.items():
            if RANK[level] > RANK[need[gate]]:
                need[gate] = level
    return need


def show(config: dict, all_specs: list[dict]) -> int:
    print(f"dial: reading spec front matter under {config['specs_dir']}/")
    if not all_specs:
        print("dial: no specs found yet: no gates are mandatory")
        return 0
    rows = [[s["id"], s["stop"], *[_sdd.GATES_BY_STOP.get(s["stop"], {}).get(g, "?")
                                  for g in _sdd.GATES]] for s in all_specs]
    print(_sdd.table(["spec", "stop", *_sdd.GATES], rows))
    need = required_gates(all_specs)
    run = [g + (" (warn only)" if need[g] == "warn" else "") for g in _sdd.GATES if need[g] != _sdd._N]
    print(f"\nmake check runs: {', '.join(run) or 'nothing'}")
    return 0


def check(config: dict, all_specs: list[dict]) -> int:
    need = required_gates(all_specs)
    gates = config.get("gates") or {}
    results = []
    for gate in _sdd.GATES:
        level = need[gate]
        if level == _sdd._N:
            results.append([gate, "not required", "SKIP", ""])
            continue
        cmd = gates.get(gate)
        if not cmd:
            outcome = "WARN" if level == "warn" else "FAIL"
            results.append([gate, level, outcome, "no command configured in sdd.yaml gates"])
            continue
        print(f"\n=== gate: {gate} ({'warn only' if level == 'warn' else 'required'}) ===", flush=True)
        print(f"$ {cmd}", flush=True)
        code = subprocess.run(cmd, shell=True, cwd=config["root"]).returncode
        outcome = "PASS" if code == 0 else ("WARN" if level == "warn" else "FAIL")
        results.append([gate, level, outcome, f"exit {code}"])
    print("\n=== make check summary ===")
    print(_sdd.table(["gate", "level", "result", "detail"], results))
    failed = [r[0] for r in results if r[2] == "FAIL"]
    if failed:
        print(f"\nFAIL: required gate(s) failed: {', '.join(failed)}")
        return 1
    print("\nPASS: every required gate passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="run every gate the dial requires")
    args = ap.parse_args(argv)
    config = _sdd.load_config()
    all_specs = _sdd.specs(config)
    if args.check:
        print(f"dial: {len(all_specs)} spec(s); strictest stop decides which gates run")
        return check(config, all_specs)
    return show(config, all_specs)


if __name__ == "__main__":
    sys.exit(main())
