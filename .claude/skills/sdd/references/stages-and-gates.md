# Stages and gates

## The seven stages

| Stage | Artefact | Lives in | Gate |
| --- | --- | --- | --- |
| Requirements | requirements.md — numbered EARS | git | Reviewed; open questions closed |
| Design | design.md — components, seams, decisions | git | Independent review passed; every REQ mapped |
| Task decomposition | Sub-issues under the feature issue | tracker | Each cites REQs and fits one PR |
| Implementation plan | Order, owners, sync gates | tracker | Owners and gates agreed |
| Implementation | Code with REQ anchors, one PR per task | git | The task's REQ tests pass |
| Testing | REQ-named tests, plus what the stop adds | CI | An independent check is green |
| Documentation | Spec refreshed, ADRs, generated docs | git | The freshness check passes |

Requirements, design and code live in git; progress lives in the tracker. Nothing should exist only in a chat.

Decomposition and planning are separate stages. Decomposition works out what the tasks are. Planning decides the order, who owns each task, and which gates it has to pass.

## Design

`design.md` sits next to `requirements.md`. It contains:

- Components and what each owns
- The data model
- Which component meets each REQ, as a REQ → component table
- Interfaces between components and between people
- Decisions, with the options rejected

It leaves out file-by-file instructions (those belong in the plan), code, and a restatement of the requirements. If the design names files and functions, it has turned into an implementation plan: keep it to what and why.

The design identifies the interfaces, and each one gets a contract file in the repo, especially where two people build from different sides (see `contracts.md`). Record the rejected options at the evidentiary stop in particular: someone will eventually ask why you didn't do it another way.

## Design review

- A separate, read-only reviewer session gets the requirements and the design. It did not write the design and can only read. Use the repo's `design-reviewer` subagent if there is one.
- It checks that every REQ is assigned to a component, every interface between people has a contract draft, must-nots and rule dates are handled, decisions record the options rejected, and nothing contradicts a requirement.
- Findings are about gaps, not style, and each is marked blocking or non-blocking. Write them to `design-review.md` unchanged.
- Blocking findings are resolved before decomposition starts.
- Both owners approve the design PR, including the contract draft (gate G0; how approval is recorded is in `contracts.md`).
- At the evidentiary stop, a named approver signs off the review.

## Tasks

A good task:

- Cites its REQs and design section
- Fits one PR and one agent session
- Names the area of code it touches
- States what done means
- Can be tested on its own

Task card fields: `reqs`, `design`, `area`, `done`, `after` (the gate it waits for) and `owner`. Write tasks to the `tasks.yaml` named in `sdd.yaml` (`board.tasks`).

The area field is what allows two people's agents to work at the same time without editing the same files.

## The plan

The plan adds to the tasks: order, as dependencies; one human owner per task; where the sync gates are; what can run in parallel; and the critical path. Every task has a human owner even when an agent does the work, because a person has to answer for it at the gate.

## Implementation and testing

- One task, one worktree, one branch.
- Read the spec, design and task first.
- Put REQ ids in code comments (`# REQ-ALW-004` on the governing line) and in commit trailers (`Spec-REQ: REQ-ALW-004`).
- Write tests from the EARS, before or with the code: tests first.
- If the spec or contract is wrong, raise it rather than editing it to make tests pass.
- Have a separate session review for gaps, not style: a reviewer that did not write the code. When the same session writes the spec, code, tests and verdict, that is self-review; the check needs to come from somewhere independent.
- If the design changed, record the decision.
- Generate reference docs rather than maintaining them by hand.
- The PR template asks: spec updated, or why not.
- A task is done when code, tests and docs change together, in the same pull request.

## Freshness

Every spec is in one of three states:

| State | Meaning |
| --- | --- |
| fresh | Nothing the spec covers has changed since it was last checked. |
| drifting | Covered code changed, the spec didn't, and nobody has checked. |
| stale | Spec and code disagree, and something relies on the spec. |

If specs go out of date, the next agent builds on the wrong version. Four mechanisms keep them fresh:

- **Trace anchors.** REQ ids in code, test names and commit trailers. CI fails if a REQ has no test or code cites a REQ that no longer exists. Run `trace.py`.
- **Covers and verified-at.** Front matter lists the paths a spec covers and the commit it was last checked against. CI flags covered files changed since. Run `fresh.py`. Whether it warns or fails follows the gate table in `dial.md`.
- **Same-PR rule.** A behaviour change and its spec change go in the same PR. Reviewers read the spec diff first.
- **Drift review.** A scheduled agent compares design with code and opens drift issues in the tracker. It only reports; a person decides.

When someone checks a spec against the code, they record the commit: `fresh.py --stamp <spec-id>` sets `verified_at` to HEAD. Run it only after a person or a reviewer session has done that check.
