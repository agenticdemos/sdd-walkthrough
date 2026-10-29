# The board and the landing queue

## Where status lives

Status gets lost in the chat (gone when the session ends), the agent's todo list (visible to one person), a TASKS.md in git (every parallel branch edits it, so it conflicts on every merge) and stand-up (rebuilt from memory once a day). Track progress outside the agent session and outside the repo.

| What | Where |
| --- | --- |
| Intent | Requirements and design, in git, changed by PR |
| Interfaces | Contracts, in git, versioned |
| Progress | Status, owner, blockers, in the tracker |
| Evidence | CI artefacts, linked from the tracker |
| Decisions | ADRs in git, or a decision log |

Agents read the tracker before starting a task and update it when they finish. Once the tasks are on the board, `tasks.yaml` is the import source only: never edit it to record progress.

## The board

GitHub Issues and a GitHub Project, named in `sdd.yaml` under `board:`.

- One feature issue per spec groups the sub-issues; one sub-issue per task. Use real sub-issues, not task lists in the body.
- Every card cites REQs, a code area, a gate and an owner, and status lives on the board rather than in a file.
- Fields: **Status** (Todo, In progress, In review, Landing, Done), **REQs**, **Dial stop**, **Gate** (G0–G3; gates are shown as a field on the board) and **Owner**. The values come from `board.statuses`, `board.gates` and `board.owners`.
- Labels: `feature`, `task`, `ready-to-land`, `ejected`, `drift`, `contract-change`.
- In Jira: an epic, sub-tasks and custom fields.

## Moving cards

Agents move the cards themselves with the `gh` command-line tool, through `board.py move`:

| When | Move to | Command |
| --- | --- | --- |
| You claim a task | In progress | `board.py move TASK-07 "In progress"` |
| You open its PR | In review | `board.py move TASK-07 "In review" --pr 42` |
| The PR joins the queue (labelled `ready-to-land`) | Landing | `board.py move TASK-07 Landing --pr 42` |
| It lands | Done, with evidence linked | `board.py move TASK-07 Done --evidence <url>` |
| It is ejected | In progress | `board.py move TASK-07 "In progress" --pr 42` |

`move` also comments on the issue with the PR or evidence link. `land.py` makes the Done and ejected moves itself.

Other commands (all as `python3 .claude/skills/sdd/scripts/board.py …`):

- `bootstrap` creates the labels, the Project and its fields, the feature issue and one sub-issue per task in `tasks.yaml`, and sets every field. It is safe to re-run: it matches on the task id in the issue title.
- `reset` puts every card back to the `board.seed` statuses in `sdd.yaml`.
- `--dry-run` prints the `gh` commands without running them.

## Landing

Two PRs can pass separately and fail together. Textual conflicts are easy to spot; behavioural ones merge without complaint. The fix is to rebase and re-test each change on the latest base, in order, before it lands. At agent volumes this has to be automated.

Each PR in the queue goes through:

1. **Rebase** onto the latest base, which already includes everything ahead of it in the queue.
2. **Full checks:** unit, contract, trace and freshness checks, plus mutation where the stop requires it (`landing.check` in `sdd.yaml`).
3. **Green: land.** The base is fast-forwarded, the card moves to Done with evidence linked, and the next PR starts.
4. **Red: eject.** The PR is returned to the owner with the failure, to be fixed and re-queued, and the rest of the queue carries on. The ejected PR has the failing test in a comment and the `ejected` label.

The queue is the only path to the base branch. Nothing is merged around the queue, even when something is urgent: the queue only protects main if it is the only route.

### Two ways to run the queue

**Scripted queue:** `python3 .claude/skills/sdd/scripts/land.py --base <branch> [--dry-run]` (or `make land BASE=<branch>`). It takes PRs labelled `ready-to-land`, oldest first; rebases, runs the checks, then lands or ejects; handles one PR at a time and prints each step; and works on any repo and any GitHub plan. It ends with a summary: landed, ejected, base SHA before and after.

**GitHub merge queue:** a branch ruleset that requires a merge queue. It tests each PR combined with the PRs ahead of it, and can group entries and test them in parallel. Workflows must also trigger on `merge_group`, as well as `pull_request`, or the required check never reports. It is available on public organisation repos, or private ones on GitHub Enterprise Cloud.

When a PR is ejected, read the failure, explain the root cause briefly, and propose a fix on that PR's branch. Do not push or merge unless asked.
