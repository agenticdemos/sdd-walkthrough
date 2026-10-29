# sdd-walkthrough

A small Python repo for walking through spec-driven development end to end, live: from a product brief to EARS requirements, a reviewed design, tasks on a GitHub board, two people building opposite sides of a contract behind gates, mutation testing, an evidence pack, and landing through a queue.

> **Illustrative.** The domain is a fictional ISA subscription ledger. Every figure, date and rule wording here (the £20,000 allowance, the £12,000 cash sub-limit from 6 April 2027, the £[1,000] report threshold) is illustrative. Check the actual rule wording before using anything like this in a real spec. Money is integer pence throughout.

## What is in it

| Path | What it is |
|---|---|
| `docs/brief.md` | The one-page product brief the walkthrough starts from |
| `specs/` | One folder per spec. Front matter declares its stop on the dial (`stop`, `covers`, `verified_at`, `owner`) |
| `contracts/ledger-api.yaml` | The ledger–report contract (OpenAPI 3.1, version in `info.version`) |
| `src/ledger/` | Provider: FastAPI service, rules engine, SQLite store (person-a) |
| `src/report/` | Consumer: the daily breach-report job (person-b) |
| `tools/pretty.py` | A throwaway JSON pretty-printer, the spec-light end of the dial |
| `.claude/skills/sdd/` | The method as a project skill: `SKILL.md`, references and scripts. Configured only through `sdd.yaml` |
| `.claude/agents/` | Read-only `reviewer` and `design-reviewer` subagents |
| `.claude/settings.json` | Hook that keeps `contracts/` read-only outside `contract/*` branches |
| `CLAUDE.md` | The few always-on rules |
| `mutation-waivers.yaml` | Reviewed waivers for equivalent mutants |

Three specs sit at three stops: `allowance-ledger` (evidentiary), `breach-report` (contract-driven) and `cli-pretty` (spec-light). `make dial` prints which gates each one makes mandatory.

## Getting started

```sh
uv sync
make check
```

## Make targets

| Target | What it does |
|---|---|
| `make check` | Every gate the dial requires for the specs in this repo (what CI runs) |
| `make test` | The whole test suite |
| `make dial` | Each spec's stop and the gates it makes mandatory |
| `make trace` | REQ → code anchors → tests; fails on an untested active REQ or an unknown REQ id |
| `make trace-design` | Every REQ appears in the design's REQ → component table |
| `make fresh` | Each spec is fresh, drifting or stale against the code it covers |
| `make contract` | Contract tests on both sides, then the `info.version` bump check |
| `make mutate` | Mutation testing on the rule modules; fails on unwaived survivors |
| `make evidence` | Writes the evidence pack to `evidence/allowance-ledger/<sha>/` |
| `make land BASE=demo/trunk` | The scripted landing queue |
| `make board` | Creates the GitHub Project, fields, feature issue and task sub-issues |
| `make board-reset` | Puts the board back to the walkthrough's seed state |

Board and landing targets call `gh`; each script can print its `gh` commands with `--dry-run`.

## Stage tags

The allowance-ledger feature is built in one commit per stage on `main`. Check out a tag to see exactly what that stage leaves behind.

| Tag | What the commit adds | Gate shown passing |
|---|---|---|
| `stage/00-brief` | Tooling, `CLAUDE.md` and `docs/brief.md` only | — |
| `stage/01-requirements` | `requirements.md` for both specs (EARS, numbered, front matter) | `make trace` lists every REQ as uncovered, as expected |
| `stage/02-design` | `design.md`, the contract draft and `design-review.md` | Every REQ mapped to a component (`make trace-design`) |
| `stage/03-tasks` | `tasks.yaml`, imported to the board | Each task cites REQs and an area; issues exist on the board |
| `stage/04-plan` | Order, owners and gates G0–G3 in `tasks.yaml` | Owners and gates visible on the board |
| `stage/05-implementation` | Ledger and report code, contract v1, REQ anchors | Unit tests green |
| `stage/06-testing` | Contract tests both sides, mutation config, evidence | `make check` green; one planted mutant survives |
| `stage/07-docs` | Specs stamped `verified_at`, README | `make fresh` reports every spec fresh |

After `stage/03-tasks`, `tasks.yaml` is the import source only: status lives on the board, never in the file.

## Approvals

The walkthrough runs from one GitHub login, so approvals are by role. `person-a` and `person-b` tick their boxes in the pull request body (see `.github/pull_request_template.md`), and waivers name a role from `sdd.yaml` as reviewer.
