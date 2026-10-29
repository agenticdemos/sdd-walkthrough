#!/usr/bin/env bash
# Pre-flight for the live session (demo helper, not part of the sdd skill).
#   1. two worktrees, ../sdd-a and ../sdd-b, on fresh branches demo/live-a and
#      demo/live-b at stage/04-plan (any earlier rehearsal in them is discarded)
#   2. gh is logged in with the `project` scope
#   3. the board is reset to the demo-3 seed state
# Safe to re-run. Override the start point with STAGE=<ref> scripts/setup_demo.sh
set -euo pipefail

STAGE="${STAGE:-stage/04-plan}"
ROOT="$(git rev-parse --show-toplevel)"
PARENT="$(dirname "$ROOT")"
cd "$ROOT"

step() { printf '\n==> %s\n' "$*"; }

step "Start point: $STAGE"
if ! git rev-parse --verify --quiet "$STAGE^{commit}" >/dev/null; then
  echo "error: $STAGE not found (git fetch --tags?)" >&2
  exit 1
fi
git log -1 --format='    %h %s' "$STAGE"

step "Pruning worktree records whose directories are gone"
git worktree prune -v

for pair in sdd-a:demo/live-a sdd-b:demo/live-b; do
  dir="$PARENT/${pair%%:*}"
  branch="${pair#*:}"
  step "Worktree $dir on $branch at $STAGE"
  if git worktree list --porcelain | grep -qxF "worktree $dir"; then
    echo "    removing stale worktree $dir (discards any rehearsal changes in it)"
    git worktree remove --force "$dir"
  elif [ -e "$dir" ]; then
    echo "error: $dir exists but is not a worktree of this repo; move it aside first" >&2
    exit 1
  fi
  git worktree add -B "$branch" "$dir" "$STAGE"
  echo "    syncing the virtualenv in $dir"
  (cd "$dir" && uv sync --quiet) || echo "    warning: uv sync failed in $dir; the first uv run there will retry"
done

step "Worktrees now"
git worktree list

step "gh auth status (needs the project scope)"
if ! status="$(gh auth status 2>&1)"; then
  echo "$status"
  echo "error: gh is not logged in; run: gh auth login" >&2
  exit 1
fi
echo "$status" | sed 's/^/    /'
if ! grep -q "'project'" <<<"$status"; then
  echo "error: token lacks the project scope; run: gh auth refresh -s project" >&2
  exit 1
fi
echo "    project scope: ok"

step "Resetting the board to the demo-3 seed (board.py reset)"
python3 .claude/skills/sdd/scripts/board.py reset

step "Ready: terminal A in $PARENT/sdd-a, terminal B in $PARENT/sdd-b"
