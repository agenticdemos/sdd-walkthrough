# DEMO.md: presenter run-sheet

Session: 29 Oct 2026, 11:00, 60 minutes. Deck: *Spec-Driven Development, End to End*, 33 visible slides, plus 7 hidden backup slides (34–40). The summary slide (33) comes at about 0:56, which leaves about four minutes for overruns and questions.

- **Slide numbers and clock times** come from the deck's speaker notes ("Target time about H:MM"). They match the brief's table. Where the deck and the brief name different fallbacks, the demo section says so.
- **Demo numbers and act numbers are different schemes.** The demo numbers 1–6 follow the kick-off slides. The branch names use the older act numbers: `demo/act4-drift` is freshness (shown at the demo 5 review), `demo/act5-fix` is the demo 5 fallback, and `act6/*` with `scripts/reset_act6.sh` is demo 6.
- **Shell commands inside a Claude session:** prefix them with `!` (for example `!make trace`), or leave the session with `/exit` first.
- **The prompts below are copied character for character from the slides**, including the curly apostrophes (’) and the en dash (–). Copy the whole fenced block.

## At a glance

| Demo | Kick-off (clock) | Terminal · start | Runs during | Review (clock) | Fallback |
|---|---|---|---|---|---|
| 1 · Requirements | 8 (0:10) | A · `git switch --detach stage/00-brief` | Design, design review | 11 (0:17) | `git switch --detach stage/01-requirements` |
| 2 · Design and review | 12 (0:19) | A · `git switch -c contract/v1` | Decomposition, visibility | 15 (0:24) | `git switch --detach stage/02-design` |
| 3 · Tasks and board | 16 (0:26) | A · same branch | Parallel work, gates | 20 (0:33) | `make board-reset` |
| 4 · Parallel | 21 (0:35) | A · `cd ../sdd-a`, B · `cd ../sdd-b` (both at `demo/parallel-start`: G1 passed) | Testing, evidence, mutation testing, demo 5 kick-off, freshness | 27 (0:45) | `demo/a-provider`, `demo/b-consumer` |
| 5 · Mutation and evidence | 25 (0:42) | C · `git switch --detach stage/06-testing` | Freshness, demo 4 review | 28 (0:47), then `make fresh` on `demo/act4-drift` | `demo/act5-fix` |
| 6 · Landing | 30 (0:51) | C · `scripts/reset_act6.sh` | How the queue works | 32 (0:54) | Merge-queue run in the browser; recorded queue log under `docs/demo/` |

**Order on the clock:** 1 go → 1 review → 2 go → 2 review → 3 go → 3 review → 4 go → 5 go → 4 review → 5 review, then freshness → 6 go → 6 review → summary.

## Pre-flight (15 minutes before)

- [ ] `gh auth status` shows you are logged in with `project` in the token scopes. If it is missing, run `gh auth refresh -s project`.
- [ ] In the repo root, update `main` and the tags: `git switch main && git pull --ff-only && git fetch origin --tags`.
- [ ] `make check` is green on `main`.
- [ ] Delete the branches that rehearsals leave behind: `git branch -D contract/v1 demo/live-requirements`. Demo 2's `git switch -c` fails if `contract/v1` already exists.
- [ ] Clear rehearsal output, so that no live result looks prebuilt: `rm -rf evidence/allowance-ledger mutants`.
- [ ] Close any PRs and issues left from demo 4 rehearsals. List them with `gh pr list` and `gh issue list --label contract-change`. Close each with `gh pr close <n> --delete-branch` or `gh issue close <n>`.
- [ ] Run `scripts/setup_demo.sh`. It creates the worktrees `../sdd-a` and `../sdd-b` at `demo/parallel-start` (G1: `stage/04-plan` plus contract v1.0.0 frozen and the ledger without TASK-07), resets the board to the slide 20 state and checks `gh auth status`.
- [ ] Open three terminals with a large font:
  - A in the repo root, on `main`, with `git status` clean.
  - B in `../sdd-b`.
  - C in the repo root, kept spare.
- [ ] Open three browser tabs:
  - the GitHub Project `SDD walkthrough`, filtered to this repo;
  - the merge-queue run on `main` (the three act6 PRs, with PR 2 removed);
  - the repo's pull-request list.
- [ ] Open `claude` once in the repo root and accept the workspace-trust prompt. Until you do, interactive sessions do not run project hooks, so the contracts guard would not fire in demo 4.
- [ ] Claude permission mode: set it explicitly (Shift+Tab) to **accept edits**. Rehearsal 1 used `acceptEdits`. Recent versions start in auto mode by default.

---

## Demo 1 · Requirements

**Kick-off:** slide 8 `d1-go`, at 0:10. **Review:** slide 11, at 0:17. **Runs during:** slides 9–10 (design, design review). **Slide expects:** two to four minutes to write.

**Start (terminal A, repo root):**

```sh
git status                          # must be clean
git switch --detach stage/00-brief
claude
```

**Prompt:**

```text
Use the sdd skill. Read docs/brief.md. First tell me which stop on the dial this feature belongs at, and why, in three lines. Then list every ambiguity you would otherwise have to guess, as numbered questions, and wait for my answers. After I answer, write the requirements in EARS as the skill describes, numbered REQ-ALW-001 onwards. Don’t write any code.
```

**Claude should** first state the stop (evidentiary) with a reason, then ask four to six numbered questions and stop. Answer them from the sheet below, then move on while it writes.

**Answer sheet (slide 8 notes, verbatim):**

> Likely questions and answers: Age is measured on the date the subscription is received. The cash sub-limit is £12,000 a tax year for subscribers under 65, from the tax year starting 6 April 2027, and does not apply before then. The overall allowance is £20,000 a tax year. Amounts are whole pence. Only the excess over a limit is rejected; the rest of the subscription is accepted. If the date of birth is missing, refuse the subscription and raise a data-quality event. Flexible ISA withdrawals are out of scope for now; record the requirement as deferred. The approver is the product owner. All figures are illustrative.

| If Claude asks about… | Answer |
|---|---|
| The date age is measured on | Age is measured on the date the subscription is received. |
| The cash sub-limit | £12,000 a tax year for subscribers under 65, from the tax year starting 6 April 2027. It does not apply before then. |
| The overall limit | The overall allowance is £20,000 a tax year. |
| Units or rounding | Amounts are whole pence. |
| A partial breach | Only the excess over a limit is rejected; the rest of the subscription is accepted. |
| A missing date of birth | Refuse the subscription and raise a data-quality event. |
| Flexible ISA withdrawals | Out of scope for now; record the requirement as deferred. |
| The approver | The product owner. |
| Whether the figures are real | All figures are illustrative. |

**Questions Claude asked in rehearsal 1 (29 Oct, 110 s to the questions, then 229 s to write):** it named the stop as **evidentiary** first, then asked whether to reject the whole subscription or only the excess; which date sets the tax year; whether backdated subscriptions are allowed; the exact year the £12,000 cash limit starts; whether the limits are fixed or configurable per year; which date is used for age 65 and whether the boundary is strict; and how cash and stocks subscriptions are told apart. The answer sheet above covers every one of these. For anything else, answer "use your judgement and list it as an open question". Rehearsal 1 wrote 12 REQs, not 7, with source, evidence and approver lines and REQ-012 deferred. Fallback `stage/01-requirements` has the brief's 7.

**Expected output:** `specs/allowance-ledger/requirements.md`, numbered from REQ-ALW-001, with:
- one EARS pattern per requirement;
- must-nots written as IF … THEN … reject;
- source, effective, evidence, review and approver lines;
- the flexible ISA requirement marked deferred;
- an "illustrative" note.

No code is written.

**Review (slide 11). Check:**
- The stop is evidentiary, with a reason
- Each requirement uses one EARS pattern and a REQ-ALW number
- The must-nots are written as IF … THEN … reject
- Each requirement has source, evidence and approver lines
- Your answers to its questions appear in the text
- No vague words, and no code written

**Show:**

```sh
less specs/allowance-ledger/requirements.md
make trace          # lists every REQ with no test yet; that is expected at this stage
```

Read two or three requirements aloud and ask the room which EARS pattern each one uses.

**Commit on a branch, so that demo 2 builds on it:**

```sh
git switch -c demo/live-requirements
git add specs && git commit -m "Requirements for allowance-ledger (live)"
```

**Fallback:** if the output is poor, say so. Do not fix it live; switch to the prepared tag:

```sh
git stash -u                                 # keep the live attempt aside
git switch --detach stage/01-requirements
git switch -c demo/live-requirements         # so demo 2 starts from a branch
```

**Reset (between rehearsals):** `git switch --discard-changes --detach stage/00-brief && git clean -fd specs/ && git branch -D demo/live-requirements`

---

## Demo 2 · Design and review

**Kick-off:** slide 12 `d2-go`, at 0:19. **Review:** slide 15, at 0:24. **Runs during:** slides 13–14 (decomposition, visibility). **Slide expects:** five to eight minutes in total.

**Start (terminal A).** Create the contract branch first and say why: the hook allows edits under `contracts/` only on a branch whose name starts with `contract/`.

```sh
!git switch -c contract/v1           # if it already exists: !git switch -C contract/v1
```

**Prompt:**

```text
Use the sdd skill. Write the design for allowance-ledger, including the REQ-to-component table and the options you rejected, and draft the ledger–report contract in contracts/ledger-api.yaml. Then have the design-reviewer subagent review the design against the requirements and record its findings. Don’t fix the findings yet.
```

**Likely questions:**

| If Claude asks… | Answer (slide 12 notes) |
|---|---|
| Does the report need per-subscriber detail, or only totals? | Per-subscriber remaining allowance and cash sub-limit. |

Questions Claude asked in rehearsal: fill in at rehearsal.

**Expected output:**
- `specs/allowance-ledger/design.md`, with a REQ → component table, decisions that list the options rejected, and §3.2 "rules engine".
- A draft of `contracts/ledger-api.yaml` (OpenAPI 3.1). The edit is allowed because the branch is `contract/v1`.
- A run of the design-reviewer subagent, which can only read, recorded in `specs/allowance-ledger/design-review.md` with findings marked blocking or non-blocking.
- No finding fixed.

**Review (slide 15). Check:**
- Every REQ appears in the REQ → component table
- The ledger–report interface has a contract draft
- Each decision lists the options rejected
- Findings are split into blocking and non-blocking
- Findings are about gaps, not style
- Claude did not fix the findings on its own

**Show:**

```sh
make trace-design
less specs/allowance-ledger/design-review.md
less contracts/ledger-api.yaml
```

Read one blocking and one non-blocking finding, and ask the room whether they agree with each.

**Commit on the contract branch:**

```sh
git add specs contracts && git commit -m "Design, contract draft and design review (live)"
```

**Fallback:**

```sh
git stash -u
git switch --detach stage/02-design
git switch -C contract/v1            # put demo 3 back on the contract branch
```

**Reset:** `git switch --discard-changes demo/live-requirements && git clean -fd specs/ contracts/ && git branch -D contract/v1`

---

## Demo 3 · Tasks and the board

**Kick-off:** slide 16 `d3-go`, at 0:26. **Review:** slide 20 `board`, at 0:33. **Runs during:** slides 17–19 (parallel work, gates). **Slide expects:** three to five minutes.

**Start:** terminal A, on the same branch (`contract/v1`). The prompt does not depend on earlier chat, so `/clear` is optional.

**Prompt:**

```text
Use the sdd skill. Resolve the design-review findings marked blocking, then break the design into tasks. Owners are person-a for the ledger and person-b for the report. Create the feature issue, the sub-issues and the board fields, and give me the board URL.
```

**Likely questions:**

| If Claude asks… | Answer (slide 16 notes) |
|---|---|
| How to split the rules work, or whether to split a large task | One task for the overall allowance and one for the cash sub-limit. |

Questions Claude asked in rehearsal: fill in at rehearsal.

**Expected output:**
- The blocking findings resolved in `design.md`.
- `specs/allowance-ledger/tasks.yaml`, holding TASK-01 to TASK-09.
- `gh` commands that create the labels, the Project fields (Status, REQs, Dial stop, Gate, Owner), the feature issue and one sub-issue per task.
- The board URL.

The board script is idempotent, so it is safe to run again if it fails part-way.

**Review (slide 20).** Switch to the Project tab in the browser and open one sub-issue. Read its fields: the REQs it covers, the code area, the gate it waits on and the owner. The slide shows roughly what the board looks like after a few tasks have moved:

| Todo | In progress | In review | Landing | Done |
|---|---|---|---|---|
| TASK-09 Breach report job · B · gate G2 | TASK-07 Cash sub-limit · A · ALW-003, 004; TASK-08 Report client · B · RPT-001 | TASK-06 Contract v1 · A and B · gate G0 | TASK-05 Ledger schema · A · queue #2 | TASK-01…04 Specs, design · evidence linked |

**Check (slide 20):** every card cites REQs, a code area, a gate and an owner, and status lives on the board rather than in a file. **In Jira:** an epic, sub-tasks and custom fields.

**Commit:** `git add specs && git commit -m "Tasks for allowance-ledger (live)"`

**Fallback:** `make board-reset` restores the prepared board. To restore the prepared `tasks.yaml` as well: `git stash -u && git switch --detach stage/03-tasks`. With no network, the board script's `--dry-run` prints the `gh` commands without running them.

**Reset:** `make board-reset`

**Before demo 4:** leave the Claude session in terminal A with `/exit`.

---

## Demo 4 · Two people in parallel

**Kick-off:** slide 21 `d4-go`, at 0:35. **Review:** slide 27, at 0:45, after the demo 5 kick-off and the freshness slide. **Runs during:** slides 22–26 (testing, evidence, mutation testing, the demo 5 kick-off, freshness). **Slide expects:** ten to fifteen minutes; this is the longest step.

**Start.** `scripts/setup_demo.sh` prepared both worktrees at `demo/parallel-start`: `stage/04-plan` plus contract v1.0.0 frozen, the ledger built through TASK-06 with no cash sub-limit, and no report client. The consumer contract tests fail until B writes `src/report/client.py`. This is the G1-to-G2 part of the plan.

```sh
# terminal A
cd ../sdd-a && git log --oneline --decorate -1     # expect G1 start for demo 4
claude

# terminal B
cd ../sdd-b && git log --oneline --decorate -1     # expect G1 start for demo 4
claude
```

Paste prompt A, then prompt B.

**Prompt, terminal A (person A, provider, TASK-07):**

```text
Use the sdd skill. You are person A’s agent on the ledger. Claim TASK-07 on the board and implement it to contract v1, tests first. Don’t read src/report/. When the provider contract tests pass, open a PR and move the card to In review.
```

**Prompt, terminal B (person B, consumer, TASK-08). This is the planted moment:**

```text
Use the sdd skill. You are person B’s agent on the breach report. Claim TASK-08 and build the report client against the contract v1 mock. Include each subscriber’s display name. Don’t read src/ledger/. When the consumer contract tests pass, open a PR and move the card to In review.
```

**The planted moment.** "Include each subscriber’s display name" is deliberate: contract v1 has no display name. One of two things should happen, and either makes the point:
- B's agent tries to edit `contracts/ledger-api.yaml`, and the PreToolUse hook blocks it with `contracts/ is read-only in implementation sessions — raise a contract-change issue`. It then opens an issue with `gh issue create --label contract-change`.
- B's agent notices the gap and raises the contract-change issue without trying the edit.

**Likely questions:**

| If Claude asks… | Answer (slide 21 notes) |
|---|---|
| B: can it add the field to the contract? | No, raise a contract-change issue and carry on without it. |

Other questions Claude asked in rehearsal: fill in at rehearsal.

**Expected output:**
- **A:** claims TASK-07 (REQ-ALW-003 and REQ-ALW-004, `src/ledger/rules/`). It writes tests named `test_REQ_ALW_…` before the code, the provider contract tests pass, it opens a PR and TASK-07 moves to In review.
- **B:** claims TASK-08 (REQ-RPT-001, `src/report/client.py`). The transcript shows the hook message, then a contract-change issue. The consumer tests pass against the mock, it opens a PR and TASK-08 moves to In review.

Both cards are already In progress on the seeded board, so claiming them changes nothing and only adds a comment.

**Review (slide 27).** Go to terminal B first, because the hook moment is the part people remember. Scroll to where the edit was refused and show the issue that was opened instead. Then show terminal A's test names and the passing provider tests.

Check, person A (provider):
- Tests named test_REQ_ALW_…, written before the code
- Provider contract tests pass
- PR open, card in In review
- Never read src/report/

Check, person B (consumer):
- Hook message in the transcript
- A contract-change issue instead of an edit
- Consumer tests pass against the mock
- Never read src/ledger/

**Show:**

```sh
gh pr list
gh issue list --label contract-change
make contract
```

This is gate G2: each side passes on its own, against the same contract, and neither read the other's code. The contract-change issue asks for a v1.1 additive change, so it does not send the pair back to G0. If one side is still running, show the other and come back at the next review.

**Fallback (prepared branches).** Stop Claude with Ctrl-C, then:

```sh
# terminal A (../sdd-a)
git stash -u && git switch --detach demo/a-provider && make contract
# terminal B (../sdd-b)
git stash -u && git switch --detach demo/b-consumer && make contract
```

**Reset:** close that run's PRs and its contract-change issue (see the pre-flight list), then run `scripts/setup_demo.sh`.

---

## Demo 5 · Mutation testing and evidence

**Kick-off:** slide 25 `d5-go`, at 0:42. Demo 4 is probably still running; leave it. **Review:** slide 28, at 0:47, then freshness. **Runs during:** slide 26 (freshness), then the demo 4 review. **Slide expects:** four to six minutes.

**Start (terminal C, repo root).** Use a third terminal so that the demo 4 sessions are left untouched.

```sh
git status                              # clean; if not, git stash -u
git switch --detach stage/06-testing
claude
```

**At `stage/06-testing`, `make check` is red, and only on the mutation gate.** That is the point of this act. It is green on `demo/act5-fix`. (The brief's stage table says green here; this build fails the mutation gate on purpose.)

**Prompt:**

```text
Use the sdd skill. Run mutation testing on the rule modules. For each survivor, tell me which REQ it belongs to and whether a test is missing or the mutant is equivalent. Add the missing tests without changing anything under src/, waive equivalent mutants as the skill describes, and rerun until there are no unwaived survivors. Then build the evidence pack.
```

Move on once the first mutation run has started.

**Likely questions:** fill in at rehearsal.

**Expected output:**
- **The survivor.** Exactly one: `>` changed to `>=` in `src/ledger/rules/cash_limit.py`, on the line `if total_cash > CASH_LIMIT_PENCE:`. It traces to REQ-ALW-004.
- **The cause.** A test is missing; the mutant is not equivalent. At exactly £12,000 (1,200,000 pence) the original code returns `capped=False` and the mutant returns `capped=True`.
- **The fix.** Claude adds `test_REQ_ALW_004_exactly_at_cash_limit_is_accepted` and reruns. The mutant is killed, no unwaived survivors remain and no waiver is needed.
- **The evidence pack.** `evidence/allowance-ledger/<sha>/` holds six files: `spec.md`, `trace.md`, `junit.xml`, `mutation.txt`, `review.json` and `README.md`. A detached tag has no PR, so `review.json` holds no PR data. What it shows instead: fill in at rehearsal.
- **The `make mutate` runtime** (the brief's budget is under two minutes): fill in at rehearsal.

**Review (slide 28). Check:**
- The survivor was traced to REQ-ALW-004
- A new test at exactly £12,000, named for the REQ
- Nothing under src/ changed
- Any waiver has a reason and is marked for review
- The evidence folder holds all six files

**Show:**

```sh
git diff --stat src/                 # empty: the gap was closed by a test, not by changing code
ls evidence/allowance-ledger/*/
```

**Then freshness.** This needs no agent and takes a few seconds. The drift branch changes a rule without touching its spec.

```sh
git stash -u                         # set demo 5's new test aside; evidence/ is git-ignored and stays
git switch demo/act4-drift
make fresh                           # reports allowance-ledger as drifting
```

**Fallback for the mutation step.** The deck names it only in the notes:

```sh
git stash -u && git switch --detach demo/act5-fix
make mutate                          # no unwaived survivors
make check                           # green
```

**Reset:** `git switch --discard-changes --detach stage/06-testing && git clean -fd tests/ && rm -rf evidence/allowance-ledger mutants`

---

## Demo 6 · The landing queue

**Kick-off:** slide 30 `d6-go`, at 0:51. Start it straight after explaining the problem on slide 29. **Review:** slide 32, at 0:54. **Runs during:** slide 31 (how the queue works). **Slide expects:** three to five minutes.

**Start (terminal C, repo root).** If demo 5's Claude session is still open, leave it with `/exit` first.

```sh
scripts/reset_act6.sh        # recreates the three planted PRs against demo/trunk, in order
claude
```

**Prompt:**

```text
Use the sdd skill. Run the landing queue against demo/trunk and show me the summary. For any PR that was ejected, read the failure, explain the root cause in five lines or fewer, and propose a fix on that PR’s branch. Don’t push or merge anything.
```

**The three planted PRs** (record the PR numbers after each `reset_act6.sh`):

| Order | PR # | Branch | Change | Alone | After PR 1 |
|---|---|---|---|---|---|
| 1 | see `gh pr list --base demo/trunk` | `act6/tax-year-end-label` | `tax_year()` now returns the year the tax year **ends** (2028 for 2027/28), and every caller and test is updated | green | — |
| 2 | see `gh pr list --base demo/trunk` | `act6/sub-limit-flag` | A new `src/report/flags.py` that calls `tax_year(d) >= 2027` assuming start-year semantics, plus tests | green | **red**: a 2026/27 date is flagged a year early and the REQ-ALW-003 test fails |
| 3 | see `gh pr list --base demo/trunk` | `act6/glossary` | Docs only | green | green |

No file is touched by both PR 1 and PR 2, so git reports no conflict.

**Likely questions:** none in rehearsal. `make land BASE=demo/trunk` took 49 s for the three PRs (29 Oct). PRs are recreated with new numbers by every `scripts/reset_act6.sh` run.

**Expected output:**
- **The queue.** Claude runs `make land BASE=demo/trunk`. For each PR in turn, the script rebases it onto `demo/trunk`, runs `make check`, then lands or ejects it.
- **The summary.** PRs 1 and 3 land. PR 2 is ejected with the failing REQ-ALW-003 test named. The summary also prints the base SHA before and after.
- **The ejected PR.** PR 2 gets a comment naming the failing test, and its `ready-to-land` label is swapped for `ejected`. Its card goes back to In progress.
- **The diagnosis**, in five lines or fewer. A good answer says that PR 1 changed `tax_year()` to return the year the tax year ends, and that PR 2's new code still assumes the start year, so a 2026/27 date is treated as 2027/28.
- **The fix.** A fix is proposed on `act6/sub-limit-flag` locally. Nothing is pushed or merged.

Let the landing summary print, then move to slide 31 while Claude works on the diagnosis.

**Review (slide 32). Check:**
- Summary: two landed, one ejected
- The ejected PR has the failing test in a comment and the ejected label
- The diagnosis names the tax_year() change, not just the failing test
- A fix is proposed on the branch; nothing pushed or merged

**Show:**

```sh
gh pr list --label ejected
git log --oneline demo/trunk -5      # if the local ref is stale: git fetch origin && git log --oneline origin/demo/trunk -5
```

**Then in GitHub.** Switch to the browser tab showing the same three PRs through merge queue on `main`, run before the session, with PR 2 removed from the queue. Two practical points, if asked:
- CI workflows must trigger on `merge_group` as well as `pull_request`, or the required check never reports.
- Merge queue is only available on public repositories owned by an organisation, or on private organisation repositories on Enterprise Cloud. Check what your plan supports.

**Fallback:** the deck's fallback is the merge-queue run in the browser. The brief adds a recorded queue log under `docs/demo/` (`ls docs/demo/`), which the deck does not mention.

**Reset:** `scripts/reset_act6.sh`

---

## If something goes wrong

- **The output is poor or the step is running long.** Say so and use the demo's fallback; do not fix it live. Every demo has a prepared tag, branch or board.
- **`git switch` refuses** because of local changes, or because untracked files would be overwritten. Run `git stash -u`, then retry.
- **`fatal: a branch named 'contract/v1' already exists`.** Run `git switch -C contract/v1` instead.
- **`… is already checked out at '../sdd-a'`.** Add `--detach` to the switch.
- **Terminal B edited `contracts/` and the hook did not fire.** Say so and show `git diff contracts/`. Undo it with `git restore contracts/`, then use the `demo/b-consumer` fallback.
- **One demo 4 side is still running at its review.** Show the other side and come back at the demo 5 review.
- **The network or GitHub is down.** The board script's `--dry-run` prints the `gh` commands. The browser tabs already show the board and the merge-queue run, and the demo 6 log is under `docs/demo/`.
- **You are running behind.** In this order:
  1. Combine the demo 4 and demo 5 reviews.
  2. Keep freshness, since it takes seconds.
  3. Replace the live demo 6 run with the merge-queue tab and the recorded log.

## Optional: drift sweep (not scheduled)

`scripts/drift_sweep.md` is a prompt file for a separate reviewer session. The session compares `design.md` with `src/` and opens drift issues with `gh issue create --label drift`. It only reports; it never edits code or specs. The deck describes this as a scheduled agent, but nothing is scheduled in this repo, so it is run by hand when there is time. For a real finding, run it on `demo/act4-drift`:

```sh
git switch demo/act4-drift && claude
```

Then tell the session: "Follow scripts/drift_sweep.md."

## Timings

Fill in one column per rehearsal. If a step overruns its window, start it later.

| Step | Window on the clock | Deck expects | Rehearsal 1 | Rehearsal 2 | Rehearsal 3 | Live |
|---|---|---|---|---|---|---|
| Demo 1: requirements | 0:10 → 0:17 | 2–4 min to write | 1:50 to questions + 3:49 to write | | | |
| Demo 2: design and review | 0:19 → 0:24 | 5–8 min | | | | |
| Demo 3: tasks and board | 0:26 → 0:33 | 3–5 min | | | | |
| Demo 4: parallel, A | 0:35 → 0:45 | 10–15 min | | | | |
| Demo 4: parallel, B | 0:35 → 0:45 | 10–15 min | | | | |
| Demo 5: mutation and evidence | 0:42 → 0:47 | 4–6 min | | | | |
| `make mutate` on `stage/06-testing` | — | under 2 min (brief) | | | | |
| `make fresh` on `demo/act4-drift` | at 0:47 | a few seconds | | | | |
| Demo 6: landing queue | 0:51 → 0:54 | 3–5 min | `make land` 0:49 | | | |
| Summary slide reached | 0:56 | — | | | | |

**Questions Claude asked** (one row per demo, filled in at rehearsal):

| Demo | Rehearsal 1 | Rehearsal 2 | Rehearsal 3 |
|---|---|---|---|
| 1 | whole vs excess rejection; tax-year date; backdating; sub-limit start year; configurable limits; age-65 date and boundary; cash vs stocks | | |
| 2 | | | |
| 3 | | | |
| 4 A | | | |
| 4 B | | | |
| 5 | | | |
| 6 | | | |
