# Contracts

Contracts live in `contracts_dir` from `sdd.yaml`, versioned in git.

## Formats

| Interface | Contract |
| --- | --- |
| API | OpenAPI (the version goes in `info.version`) |
| Data | A data contract (ODCS) |
| Events | AsyncAPI and a schema registry |
| In-process | A typed interface with pre- and post-conditions |

## Where contracts go

Put contracts on the interfaces between people, not between every pair of agents.

| Level | Sync | Through |
| --- | --- | --- |
| Within one person | soft sync | The spec and task list |
| Between people | hard sync | The contract |
| Across the team | check-in sync | The tracker |

Agree the interface, then build without reading each other's code. The consumer reads the contract and never reads the provider's code; the provider reads the contract and never reads the consumer's code.

Draft the contract in the design. Freeze it once each side has built one thin slice. It is agreed by both owners before either side starts and frozen for the iteration. The mock and the tests are generated from it:

- The consumer builds against the mock served from the contract.
- The provider implements the contract, checked by validators generated from the same contract.
- Contract tests: both sides must pass to merge. The consumer's CI runs the consumer side and the provider's CI runs the provider side.

An OpenAPI file that no test runs against drifts quickly, and a consumer is usually the first to notice.

## Gates G0–G3

| Gate | Passes when |
| --- | --- |
| G0 · agreed | Both owners approve the contract PR. Work can start on both sides. |
| G1 · thin slice | One operation built on each side against mocks. The contract can still change; then v1 is frozen. |
| G2 · both sides pass | The provider passes the contract tests and the consumer passes against the mock, each in its own CI. |
| G3 · integrated | Both sides land through the queue and the contract tests run against the real pair. |

**How approval is recorded.** Approvals are by role, not by GitHub login, so the method works when one person holds several roles or the team shares one account. The PR template has one approval line per owner role listed in `sdd.yaml` (`board.owners`), in the form `- [ ] person-a approves`. Each owner ticks their own box (`- [x] person-a approves`); G0 passes when every owner's box is ticked in the contract PR body. An agent never ticks a box. The evidence pack records these role approvals plus any GitHub reviews. A team with a GitHub user per person should turn on required code-owner reviews in a branch ruleset instead, so GitHub enforces the approval.

## Changing a contract

`python3 .claude/skills/sdd/scripts/contract_diff.py [--base REF]` classifies a change and fails CI if `info.version` was not bumped to match.

- An additive change is a minor bump (v1.1): both specs note it and no gate is repeated.
- A breaking change is v2 and goes back to G0.

An agent that can't meet the contract stops and raises a change: open an issue labelled `contract-change` describing what is needed and why. Never edit the contract to make your side work. This instruction goes in CLAUDE.md and in the task.

Two pieces of repo config hold the line:

- A hook keeps `contracts/` read-only in implementation sessions. It only allows edits under `contracts/` on a branch that starts with `contract/`, so contract drafting happens on such a branch.
- CODEOWNERS requires both owners to approve any edit: it lists both owners on `contracts/`, and GitHub enforces it once required code-owner reviews are on.
