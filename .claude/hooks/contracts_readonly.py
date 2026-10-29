#!/usr/bin/env python3
"""Claude Code hook: contracts/ is read-only unless the branch starts with contract/.

PreToolUse (Write, Edit, MultiEdit, NotebookEdit, Bash): exit 2 with the message on
stderr blocks the tool call, and Claude sees the message as the reason.
PostToolUse (--post, Bash): backstop for shell writes the pattern check missed; the
command already ran, so exit 2 tells Claude to revert it.

Stdlib only and Python 3.9 compatible: hooks run whatever python3 is on PATH.
Reads the branch from the git worktree that holds the target, so two worktrees on
different branches each get the right answer.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROTECTED = "contracts"
BRANCH_PREFIX = "contract/"
MSG = "contracts/ is read-only in implementation sessions — raise a contract-change issue"

FILE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
# Best effort: shell forms that WRITE to a path under contracts/.
T = r"""['"]?[^\s'";|&<>]*\bcontracts/"""
SHELL_WRITES = [
    r">>?\s*" + T,                                               # > contracts/x, >> ./contracts/x
    r"\btee\b[^|;&]*\s" + T,                                     # ... | tee [-a] contracts/x
    r"\b(?:sed|perl)\b[^|;&]*\s-i[^|;&]*\s" + T,                 # in-place edit
    r"\b(?:rm|touch|truncate|mkdir|rmdir)\b[^|;&]*\s" + T,       # create or delete
    r"\b(?:cp|mv|ln|install|rsync)\b[^|;&]*\s" + T + r"[^\s|;&]*\s*(?:$|[|;&])",  # destination
    r"\bmv\b[^|;&]*\s" + T,                                      # mv also removes its source
    r"\bgit\s+(?:checkout|restore|apply|mv|rm)\b[^|;&]*\s" + T,  # git rewrites the tree
]


def git(args, cwd):
    try:
        out = subprocess.run(["git"] + list(args), cwd=str(cwd), capture_output=True,
                             text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def on_contract_branch(cwd):
    return git(["branch", "--show-current"], cwd).startswith(BRANCH_PREFIX)


def block():
    print(MSG, file=sys.stderr)
    sys.exit(2)


def check_file_tool(tool_input, cwd):
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not raw:
        return
    path = Path(raw.replace("\\", "/"))
    if not path.is_absolute():
        path = Path(cwd) / path
    probe = path.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent  # Write may create new directories
    root = git(["rev-parse", "--show-toplevel"], probe)
    if not root:
        return
    try:  # resolve() so /tmp and /private/tmp (macOS) compare equal
        rel = path.resolve().relative_to(Path(root).resolve())
    except ValueError:
        return
    if rel.parts[:1] == (PROTECTED,) and not on_contract_branch(root):
        block()


def check_shell_pre(command, cwd):
    if PROTECTED + "/" not in command:
        return
    if any(re.search(p, command) for p in SHELL_WRITES) and not on_contract_branch(cwd):
        block()


def check_shell_post(cwd):
    root = git(["rev-parse", "--show-toplevel"], cwd)
    if not root or on_contract_branch(root):
        return
    dirty = git(["status", "--porcelain", "--", PROTECTED + "/"], root)
    if dirty:
        print(MSG + "\nA shell command changed " + PROTECTED + "/ on this branch:\n" + dirty +
              "\nRevert it (git checkout -- " + PROTECTED + "/ ; git clean -fd " + PROTECTED +
              "/) and open a contract-change issue instead.", file=sys.stderr)
        sys.exit(2)


def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    if "--post" in sys.argv[1:]:
        if tool in SHELL_TOOLS:
            check_shell_post(cwd)
    elif tool in FILE_TOOLS:
        check_file_tool(tool_input, cwd)
    elif tool in SHELL_TOOLS:
        check_shell_pre(tool_input.get("command", ""), cwd)
    sys.exit(0)


if __name__ == "__main__":
    main()
