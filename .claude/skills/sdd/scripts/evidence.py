#!/usr/bin/env python3
"""Evidence pack: write <evidence_dir>/<SPEC>/<sha>/ for one spec at one commit.

  spec.md     requirements at that sha, its sha256 and approver lines
  trace.md    trace.py --matrix
  junit.xml   test results (pytest --junitxml over sdd.yaml test_dirs)
  mutation.txt  sdd.yaml gates.mutation output plus the waivers file
  review.json   gh pr view (role approvals from '- [x] <role> approves' lines)
  README.md   one page tying each REQ to the files above
"""
import argparse, hashlib, json, re, shutil, subprocess, sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _sdd  # noqa: E402

HERE = Path(__file__).resolve().parent


def run(cmd, cwd):
    """Run a command (list or shell string); return (exit code, combined output)."""
    print(f"$ {cmd if isinstance(cmd, str) else ' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def spec_text(cfg, spec, sha):
    rel = _sdd.rel(spec["path"], cfg)
    try:
        return rel, _sdd.git("show", f"{sha}:{rel}", root=cfg["root"]) + "\n"
    except _sdd.CommandError:
        print(f"  {rel} not in git at {sha}; using the working tree")
        return rel, Path(spec["path"]).read_text()


def review(pr, approvers, dry):
    if not pr:
        return {"pr": None}
    out = _sdd.gh(["pr", "view", str(pr), "--json", "number,author,reviews,body,mergedAt"], dry)
    if not out:
        return {"pr": int(pr), "note": "dry run: gh not called"}
    d = json.loads(out)
    roles = re.findall(r"^\s*- \[[xX]\] (\S+) approves", d.get("body") or "", re.M)
    return {"pr": d["number"], "author": (d.get("author") or {}).get("login"), "merged_at": d.get("mergedAt"),
            "role_approvals": [r for r in roles if not approvers or r in approvers],
            "github_reviews": [{"reviewer": (r.get("author") or {}).get("login"), "state": r.get("state"),
                                "submitted_at": r.get("submittedAt")} for r in d.get("reviews") or []]}


def junit_results(path):
    """{testcase name: passed?} from a junit file (empty if missing or unreadable)."""
    try:
        cases = ET.parse(path).getroot().iter("testcase")
    except (ET.ParseError, OSError):
        return {}
    return {c.get("name", ""): not any(c.find(t) is not None for t in ("failure", "error", "skipped")) for c in cases}


def build(cfg, spec_id, sha=None, pr=None, dry=False):
    root = Path(cfg["root"])
    spec = next((s for s in _sdd.specs(cfg) if s["id"] == spec_id), None)
    if spec is None:
        raise SystemExit(f"no spec {spec_id!r} under {cfg['specs_dir']}/")
    sha = sha or _sdd.git("rev-parse", "HEAD", root=root)
    out = root / cfg["evidence_dir"] / spec_id / sha
    out.mkdir(parents=True, exist_ok=True)
    print(f"evidence pack for {spec_id} @ {sha[:12]} -> {_sdd.rel(out, cfg)}")

    rel, text = spec_text(cfg, spec, sha)
    digest = hashlib.sha256(text.encode()).hexdigest()
    approvers = [ln.strip() for ln in text.splitlines() if re.search(r"\bapprover:", ln)]
    (out / "spec.md").write_text(f"# {spec_id} requirements @ {sha}\n\n- file: `{rel}`\n- sha256: `{digest}`\n"
                                 + "".join(f"- {a}\n" for a in approvers or ["approver: (none recorded)"])
                                 + "\n---\n\n" + text)
    print("  wrote spec.md")

    code, matrix = run([sys.executable, str(HERE / "trace.py"), "--matrix"], root)
    (out / "trace.md").write_text(matrix if code == 0 else f"trace.py --matrix exited {code}\n\n{matrix}")
    print(f"  wrote trace.md (exit {code})")

    junit = out / "junit.xml"
    runner = ["uv", "run", "pytest"] if shutil.which("uv") else [sys.executable, "-m", "pytest"]
    code, _ = run([*runner, *cfg["test_dirs"], "-q", f"--junitxml={junit}"], root)
    print(f"  wrote junit.xml (pytest exit {code})")

    mcmd = cfg.get("gates", {}).get("mutation")
    mut = run(mcmd, root) if mcmd else (0, "no gates.mutation command in sdd.yaml\n")
    waivers = root / cfg.get("mutation", {}).get("waivers", "mutation-waivers.yaml")
    wtext = waivers.read_text() if waivers.is_file() else "(no waivers file)\n"
    (out / "mutation.txt").write_text(f"$ {mcmd}\nexit {mut[0]}\n\n{mut[1]}\n--- waivers: {_sdd.rel(waivers, cfg)}\n{wtext}")
    print(f"  wrote mutation.txt (exit {mut[0]})")

    rv = review(pr, cfg.get("mutation", {}).get("approvers", []), dry)
    (out / "review.json").write_text(json.dumps(rv, indent=2) + "\n")
    print(f"  wrote review.json (pr {rv['pr']})")

    results = junit_results(junit)
    rows = []
    for rid, status in _sdd.reqs(Path(spec["path"]), cfg["req_pattern"]):
        tag = rid.replace("-", "_")
        mine = [ok for name, ok in results.items() if tag in name]
        tests = f"{sum(mine)}/{len(mine)} passed" if mine else ("deferred" if status == "deferred" else "NO TESTS")
        rows.append([rid, status, tests, f"[spec.md](spec.md) · [trace.md](trace.md) · [junit.xml](junit.xml)"])
    approvals = ", ".join(rv.get("role_approvals", [])) or "none recorded"
    readme = (f"# Evidence: {spec_id} @ `{sha[:12]}`\n\nSpec `{rel}` (sha256 `{digest[:16]}…`), dial stop "
              f"**{spec['stop']}**. Mutation exit {mut[0]} (see [mutation.txt](mutation.txt)); review: PR "
              f"{rv['pr'] or '—'}, role approvals: {approvals} ([review.json](review.json)).\n\n"
              + "| REQ | status | tests | evidence |\n|---|---|---|---|\n"
              + "".join(f"| {' | '.join(r)} |\n" for r in rows))
    (out / "README.md").write_text(readme)
    print("  wrote README.md")
    print(_sdd.table(["REQ", "status", "tests"], [r[:3] for r in rows]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="spec id (its directory name under specs_dir)")
    ap.add_argument("--sha", help="commit to record (default HEAD)")
    ap.add_argument("--pr", help="PR number whose review to record")
    ap.add_argument("--dry-run", action="store_true", help="print gh commands without calling GitHub")
    a = ap.parse_args(argv)
    build(_sdd.load_config(), a.spec, a.sha, a.pr, a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
