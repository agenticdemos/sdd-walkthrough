---
name: sdd
description: Spec-driven development method. Use for any work on specs, requirements, EARS, design, design review, tasks, the board (GitHub Issues and Projects), contracts, mutation testing, evidence packs, freshness and landing through the queue. Chooses the stop on the criticality dial, then walks the seven stages from requirements to documentation, each with its artefact, gate and script.
---

# Spec-driven development (sdd)

The method runs from a product brief to landed, evidenced code in seven stages. How much of it applies depends on the stop on the dial.

## Always, before anything else

1. Read `sdd.yaml` at the repo root. Every path, the board, the base branch, the mutation targets and the gate commands come from there; never assume them.
2. State which stop on the dial this work is at, and why (read `references/dial.md`).
3. Find the spec that covers the files you will touch (`covers:` in each spec's front matter) and read its requirements, design and task before changing anything.

## The seven stages

### 1. Requirements
- **Produces:** `<specs_dir>/<spec-id>/requirements.md`, numbered EARS with front matter.
- **Gate:** reviewed; open questions closed.
- **Read:** `references/ears.md` (format, questions first, no code) and `references/dial.md`.
- **Run:** `dial.py` to show the stop and its gates; `trace.py` lists every REQ as having no test yet, which is expected here.

### 2. Design and design review
- **Produces:** `design.md` (components, data model, REQ → component table, interfaces, decisions with rejected options), a contract draft for each interface between people, and `design-review.md` from a read-only reviewer.
- **Gate:** independent review passed; every REQ mapped; blocking findings resolved; both owners approve (G0).
- **Read:** `references/stages-and-gates.md` (Design, Design review) and `references/contracts.md`.
- **Run:** `trace.py --design`. Draft contracts on a `contract/*` branch.

### 3. Task decomposition
- **Produces:** the tasks file named by `board.tasks`, then a feature issue and one sub-issue per task.
- **Gate:** each task cites REQs and fits one PR.
- **Read:** `references/stages-and-gates.md` (Tasks) and `references/board.md`.
- **Run:** `board.py bootstrap`; give the board URL.

### 4. Implementation plan
- **Produces:** order, owners and sync gates (G0–G3) on each task and as board fields.
- **Gate:** owners and gates agreed.
- **Read:** `references/stages-and-gates.md` (The plan) and `references/contracts.md` (Gates).
- **Run:** `board.py bootstrap` again (it is idempotent) to set the fields.

### 5. Implementation
- **Produces:** code with REQ anchors, one PR per task, one task per worktree and branch.
- **Gate:** the task's REQ tests pass.
- **Read:** `references/stages-and-gates.md` (Implementation and testing), `references/contracts.md` (Changing a contract), `references/board.md` (Moving cards).
- **Run:** `board.py move <TASK> "In progress"` on claim; `trace.py`; `contract_diff.py` if a contract changed; `board.py move <TASK> "In review" --pr <n>` once the PR is open.

### 6. Testing
- **Produces:** REQ-named tests, plus what the stop adds: contract tests on both sides, zero unwaived surviving mutants, an evidence pack.
- **Gate:** an independent check is green.
- **Read:** `references/mutation.md` and `references/dial.md` (which gates apply).
- **Run:** `dial.py --check`; `mutate.py` at the evidentiary stop; `evidence.py <spec-id>` after landing.

### 7. Documentation
- **Produces:** the spec refreshed in the same PR as the behaviour change, decisions recorded, reference docs generated.
- **Gate:** the freshness check passes.
- **Read:** `references/stages-and-gates.md` (Freshness).
- **Run:** `fresh.py`; `fresh.py --stamp <spec-id>` only after a person or reviewer has checked the spec against the code.

### Landing
- Every change reaches the base branch through the queue, never around it.
- **Read:** `references/board.md` (Landing).
- **Run:** `land.py --base <branch>`, which lands or ejects and moves the cards.

## Scripts

Run them from the repo root as `python3 .claude/skills/sdd/scripts/<name>.py`, or through the repo's make targets. They use the standard library plus `gh`, read every path from `sdd.yaml`, print what they are doing, and exit non-zero on failure. If the skill is installed as a plugin, the scripts sit in this skill's own `scripts/` folder.

| Script | Does |
| --- | --- |
| `dial.py [--check]` | Table of every spec, its stop and the gates that apply; `--check` runs the mandatory gates |
| `trace.py [--design \| --matrix]` | REQ → tests and code anchors; fails on an untested active REQ or a reference to a REQ that does not exist. `--design` checks the design's REQ map; `--matrix` writes the evidence matrix |
| `fresh.py [--stamp SPEC]` | fresh, drifting or stale for each spec; `--stamp` records the checked commit |
| `board.py bootstrap \| move TASK STATUS [--pr N] [--evidence URL] \| reset` | Creates and updates the board; `--dry-run` prints the `gh` commands |
| `contract_diff.py [--base REF]` | Additive or breaking, and whether `info.version` was bumped to match |
| `mutate.py` | Mutation testing on `mutation.targets`; fails on unwaived survivors |
| `evidence.py SPEC [--sha SHA] [--pr N]` | Writes the evidence pack for a landed commit |
| `land.py --base BRANCH [--dry-run]` | The scripted landing queue |

## Where things live

- **This skill** holds the method and loads when the work needs it, so CLAUDE.md stays short and holds only a few always-on rules. It works in any repo once `sdd.yaml` is set, the scripts travel with it, and it can become a plugin unchanged when more teams need it.
- **Repo config** stays in the repo: the hook that keeps `contracts/` read-only off `contract/*` branches, CODEOWNERS and the CI workflow.
- **Prompts** start with "Use the sdd skill" so it always loads.

## Approvals

Approvals are by role (the roles in `sdd.yaml`), not by GitHub login: owners tick their box in the PR body, and waivers name a reviewing role. A team where each person has their own GitHub user turns on required reviews in a branch ruleset instead. Details: `references/contracts.md` and `references/mutation.md`.
