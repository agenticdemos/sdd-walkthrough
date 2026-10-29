#!/usr/bin/env bash
# Demo 6 reset (demo helper, not part of the sdd skill): put the three planted PRs back.
#
#   scripts/reset_act6.sh               demo/trunk := act6/base (tag), then three PRs against
#                                       demo/trunk, labelled ready-to-land, for `make land`
#   scripts/reset_act6.sh --main        three PRs against main, no label (merge-queue run);
#                                       demo/trunk is left alone
#   scripts/reset_act6.sh --from REF    build on REF instead of act6/base (origin/main if the
#                                       tag is missing); REF must not hold a landed act6 PR
#
# Steps: fetch; build act6/tax-year-end-label, act6/sub-limit-flag and act6/glossary by
# `git am` of scripts/act6/0N-*.patch onto the base (in a temporary worktree, so your
# checkout is never touched, and nothing is pushed if a patch does not apply); close open
# PRs from act6/* branches; force-push demo/trunk and the three branches; open the PRs in
# order 1, 2, 3, about 2 s apart so createdAt keeps that order.
#
# Safe to re-run: every run ends in the same state, with three fresh open PRs.
set -euo pipefail

TARGET=demo/trunk
FROM=  # default: tag act6/base (main before any act6 PR landed), else origin/main
LABEL=ready-to-land
while [ $# -gt 0 ]; do
  case "$1" in
    --main) TARGET=main ;;
    --from) FROM="${2:?--from needs a ref}"; shift ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "usage: $0 [--main] [--from REF]" >&2; exit 2 ;;
  esac
  shift
done

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"
PATCHES="$HERE/act6"
cd "$ROOT"

step() { printf '\n==> %s\n' "$*"; }
run() { printf '$ %s\n' "$*"; "$@"; }

BRANCHES=(act6/tax-year-end-label act6/sub-limit-flag act6/glossary)
PATCH_FILES=(01-tax-year-end-label.patch 02-sub-limit-flag.patch 03-glossary.patch)
TITLES=("Tax year labelled by end year" "Sub-limit flag for the breach report" "Glossary")
BODIES=(
  "\`tax_year()\` now returns the year the tax year ends (2028 for 2027/28). Every caller and test is updated, and the allowance-ledger spec says how tax years are labelled. Planted PR 1 of 3 for demo 6."
  "New \`src/report/flags.py\`: \`sub_limit_applies(d)\` is true from tax year 2027 (start-year naming), with REQ-ALW-003 tests and a note in the breach-report spec. Planted PR 2 of 3 for demo 6."
  "Docs only: \`docs/glossary.md\`. Planted PR 3 of 3 for demo 6."
)

step "Checking prerequisites"
for f in "${PATCH_FILES[@]}"; do
  [ -f "$PATCHES/$f" ] || { echo "error: missing $PATCHES/$f" >&2; exit 1; }
done
run gh auth status >/dev/null
REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
echo "    repo $REPO; PRs will target $TARGET$([ "$TARGET" = main ] || echo ", labelled $LABEL")"

step "Fetching origin"
run git fetch --prune origin
if git ls-remote --exit-code --tags origin refs/tags/act6/base >/dev/null 2>&1; then
  run git fetch --quiet --force origin refs/tags/act6/base:refs/tags/act6/base
fi
if [ -z "$FROM" ]; then
  if git rev-parse -q --verify refs/tags/act6/base >/dev/null; then FROM=act6/base; else FROM=origin/main; fi
fi
BASE_SHA="$(git rev-parse --verify "$FROM^{commit}")"
echo "    base for the branches: $FROM = $(git log -1 --format='%h %s' "$BASE_SHA")"

step "Building the three branches in a temporary worktree (nothing pushed yet)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/reset-act6.XXXXXX")"
WT="$TMP/wt"
cleanup() {
  git -C "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || true
  git -C "$ROOT" worktree prune >/dev/null 2>&1 || true
  rm -rf "$TMP"
}
trap cleanup EXIT
run git worktree add --quiet --detach "$WT" "$BASE_SHA"
SHAS=()
for i in 0 1 2; do
  printf '    %s <- %s\n' "${BRANCHES[$i]}" "${PATCH_FILES[$i]}"
  git -C "$WT" checkout --quiet --detach "$BASE_SHA"
  if ! git -C "$WT" am --quiet --3way "$PATCHES/${PATCH_FILES[$i]}" \
     || [ "$(git -C "$WT" rev-parse HEAD^)" != "$BASE_SHA" ]; then
    git -C "$WT" am --abort >/dev/null 2>&1 || true
    echo "error: ${PATCH_FILES[$i]} does not apply as a new commit on $(git log -1 --format=%h "$BASE_SHA")." >&2
    echo "       If main already holds a landed act6 PR, re-run with --from <a commit before it>." >&2
    exit 1
  fi
  SHAS+=("$(git -C "$WT" rev-parse HEAD)")
done

step "Closing open PRs from act6/* branches"
OPEN="$(gh pr list --repo "$REPO" --state open --limit 100 --json number,headRefName \
          --jq '.[] | select(.headRefName | startswith("act6/")) | .number')"
if [ -z "$OPEN" ]; then
  echo "    none open"
else
  for n in $OPEN; do
    run gh pr close "$n" --repo "$REPO" --comment "Closed by scripts/reset_act6.sh; a fresh PR replaces it."
  done
fi

if [ "$TARGET" = demo/trunk ]; then
  step "Resetting demo/trunk to $FROM ($(git log -1 --format='%h' "$BASE_SHA"))"
  run git push --force-with-lease=refs/heads/demo/trunk origin "$BASE_SHA:refs/heads/demo/trunk"
  git branch -f demo/trunk "$BASE_SHA" 2>/dev/null \
    || echo "    (local demo/trunk is checked out somewhere; left as is, origin/demo/trunk is what land.py reads)"
else
  step "Target is main: demo/trunk left as it is"
fi

for i in 0 1 2; do
  b="${BRANCHES[$i]}"
  sha="${SHAS[$i]}"
  step "Force-pushing $b ($(git log -1 --format='%h %s' "$sha"))"
  run git push --force-with-lease="refs/heads/$b" origin "$sha:refs/heads/$b"
  git branch -f "$b" "$sha" 2>/dev/null \
    || echo "    (local $b is checked out somewhere; left as is, origin/$b is what land.py reads)"
done

if [ "$TARGET" = demo/trunk ]; then
  step "Making sure the $LABEL and ejected labels exist"
  HAVE="$(gh label list --repo "$REPO" --limit 200 --json name --jq '.[].name')"
  for l in "$LABEL" ejected; do
    if printf '%s\n' "$HAVE" | grep -qxF "$l"; then
      echo "    $l: present"
    else
      run gh label create "$l" --repo "$REPO" --color "$([ "$l" = ejected ] && echo B60205 || echo 0E8A16)"
    fi
  done
fi

for i in 0 1 2; do
  step "Opening PR $((i + 1)): ${TITLES[$i]}"
  args=(pr create --repo "$REPO" --base "$TARGET" --head "${BRANCHES[$i]}" --title "${TITLES[$i]}" --body "${BODIES[$i]}")
  [ "$TARGET" = main ] || args+=(--label "$LABEL")
  run gh "${args[@]}"
  [ "$i" = 2 ] || sleep 2
done

step "Open PRs against $TARGET, oldest first (record these numbers in DEMO.md)"
gh pr list --repo "$REPO" --base "$TARGET" --state open --limit 100 \
  --json number,title,headRefName,createdAt,labels \
  --jq 'sort_by(.createdAt) | .[] | select(.headRefName | startswith("act6/"))
        | "    #\(.number)  \(.headRefName)  \(.title)  [\([.labels[].name] | join(","))]"'

if [ "$TARGET" = demo/trunk ]; then
  printf '\nReady: make land BASE=demo/trunk\n'
else
  printf '\nReady: add the three PRs to the merge queue on main, in order.\n'
fi
