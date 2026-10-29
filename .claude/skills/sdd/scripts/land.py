#!/usr/bin/env python3
"""Scripted landing queue: land ready PRs onto BASE one at a time, oldest first.

For each open PR labelled sdd.yaml landing.label against BASE:
  rebase onto the base tip (conflict -> eject), run landing.check (streamed),
  green -> push branch, fast-forward BASE, push, board move Done;
  red   -> comment failing tests, label landing.ejected_label, board move In progress.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _sdd  # noqa: E402
import board  # noqa: E402


def git(root, *args, dry=False, check=True):
    print("$ git " + " ".join(args), flush=True)
    if dry:
        return ""
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(args)} failed:\n{r.stdout}{r.stderr}")
    return r.stdout.strip() if check else r


def run_check(root, cmd):
    """Run the check command, streaming its output; return (ok, output)."""
    print(f"$ {cmd}", flush=True)
    p = subprocess.Popen(cmd, shell=True, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines = []
    for line in p.stdout:
        print("  | " + line, end="", flush=True)
        lines.append(line)
    return p.wait() == 0, "".join(lines)


def failing_tests(output):
    return re.findall(r"^FAILED (\S+)", output, re.M)


def task_of(pr):
    m = re.search(r"TASK-\d\d", pr.get("title", "")) or re.search(r"TASK-\d\d", pr.get("headRefName", ""))
    return m.group(0) if m else None


def board_move(cfg, pr, status, dry):
    task = task_of(pr)
    if not task or "board" not in cfg:
        why = "no board in sdd.yaml" if task else f"no TASK id on PR #{pr['number']}"
        print(f"  ({why}; board unchanged)")
        return
    try:
        board.move(cfg, task, status, pr=pr["number"], dry=dry)
    except (SystemExit, _sdd.CommandError) as e:  # a board problem must not stop the queue
        print(f"  ! board move failed: {e}")


def eject(cfg, pr, reason, failed, dry):
    L = cfg["landing"]
    body = f"Ejected by the landing queue: {reason}."
    if failed:
        body += "\n\nFailing tests:\n" + "\n".join(f"- `{t}`" for t in failed)
    _sdd.gh(["pr", "comment", str(pr["number"]), "--body", body], dry)
    _sdd.gh(["pr", "edit", str(pr["number"]), "--remove-label", L["label"], "--add-label", L["ejected_label"]], dry)
    board_move(cfg, pr, "In progress", dry)


def land(cfg, base, dry, remote="origin"):
    root, L = Path(cfg["root"]), cfg["landing"]
    out = _sdd.gh(["pr", "list", "--base", base, "--label", L["label"], "--state", "open",
                   "--json", "number,title,headRefName,createdAt", "--limit", "100"], dry)
    prs = sorted(json.loads(out) if out.strip() else [], key=lambda p: p["createdAt"])
    print(f"queue for {base}: " + (", ".join(f"#{p['number']} {p['headRefName']}" for p in prs) or "empty"))
    if not prs:
        return [], [], "", ""
    if git(root, "status", "--porcelain", "--untracked-files=no", dry=dry):
        raise SystemExit("working tree has uncommitted changes; commit or stash before landing")
    start = git(root, "rev-parse", "--abbrev-ref", "HEAD", dry=dry)
    git(root, "fetch", remote, dry=dry)
    before = git(root, "rev-parse", f"{remote}/{base}", dry=dry)
    landed, ejected = [], []
    try:
        for pr in prs:
            n, branch = pr["number"], pr["headRefName"]
            print(f"\n== PR #{n} {branch}: rebase onto {base}")
            git(root, "checkout", "-B", branch, f"{remote}/{branch}", dry=dry)
            r = git(root, "rebase", f"{remote}/{base}", dry=dry, check=False)
            if not dry and r.returncode:
                git(root, "rebase", "--abort", check=False)
                print(f"   EJECT #{n}: rebase conflict")
                eject(cfg, pr, f"rebase onto `{base}` conflicts", [], dry)
                ejected.append((n, "rebase conflict"))
                continue
            ok, output = (True, "") if dry else run_check(root, L["check"])
            if ok:
                print(f"   GREEN #{n}: landing on {base}")
                git(root, "push", "--force-with-lease", remote, f"HEAD:{branch}", dry=dry)
                git(root, "push", remote, f"HEAD:{base}", dry=dry)  # fast-forward: HEAD sits on the base tip
                board_move(cfg, pr, "Done", dry)
                landed.append(n)
            else:
                failed = failing_tests(output)
                print(f"   RED #{n}: {', '.join(failed) or 'check failed'}")
                eject(cfg, pr, f"`{L['check']}` failed after rebase onto `{base}`", failed, dry)
                ejected.append((n, ", ".join(failed) or "check failed"))
    finally:
        if start and start != "HEAD":
            git(root, "checkout", start, dry=dry, check=False)
    after = git(root, "rev-parse", f"{remote}/{base}", dry=dry)
    return landed, ejected, before, after


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="branch to land onto (default: sdd.yaml base_branch)")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--dry-run", action="store_true", help="print gh/git commands, change nothing")
    a = ap.parse_args(argv)
    cfg = _sdd.load_config()
    base = a.base or cfg["base_branch"]
    landed, ejected, before, after = land(cfg, base, a.dry_run, a.remote)
    print("\n== landing summary")
    print(_sdd.table(["", "PRs"], [["landed", ", ".join(f"#{n}" for n in landed) or "none"],
                                   ["ejected", "; ".join(f"#{n} ({why})" for n, why in ejected) or "none"],
                                   [f"{base} before", before[:12] or "-"], [f"{base} after", after[:12] or "-"]]))
    return 0  # an ejection is the queue working, not the script failing


if __name__ == "__main__":
    sys.exit(main())
