# Allowance ledger: design review

Reviewer: `design-reviewer` subagent (read-only: Read, Grep, Glob). It did not write the design.
Inputs: `specs/allowance-ledger/requirements.md`, `specs/allowance-ledger/design.md`, `contracts/ledger-api.yaml` (draft 0.1.0).
Criteria: unmapped REQs; interfaces between people without a contract draft; must-nots and effective dates not handled; decisions without rejected options; contradictions with a requirement.

The findings below are recorded as the reviewer returned them. Lines starting **Resolution** were added afterwards by the main session when the blocking findings were resolved (demo 3), before any tasks were created.

## Findings

**B1 · BLOCKING · unmapped REQ.** REQ-ALW-006 does not appear in the REQ → component table. The design never says which component refuses a subscription with a missing date of birth or where the data-quality event goes.
**Resolution:** added §3.3 (refusals and data quality) and a REQ-ALW-006 row mapping it to the ledger API and the ledger store.

**B2 · BLOCKING · effective date and must-not not handled.** §3.2 describes the cash sub-limit without its effective date, so nothing in the design stops it applying to tax years before 6 April 2027 (REQ-ALW-003). It also does not say whether reaching exactly £12,000 is allowed, which decides the boundary in REQ-ALW-004.
**Resolution:** §3.2 now states the sub-limit applies from the tax year starting 6 April 2027 and reports null before then, and that reaching exactly £12,000 is allowed; only an amount above it is excess.

**B3 · BLOCKING · contradiction with a requirement.** The draft contract's record-a-subscription response returns the remaining overall allowance only. REQ-ALW-002 requires the remaining cash sub-limit as well.
**Resolution:** the contract draft and §6 now return the remaining cash sub-limit on both operations, null when no sub-limit applies.

**N1 · NON-BLOCKING · interface detail.** The contract has no way to list subscribers, so the report cannot discover whom to check. The design should say where the report gets its subscriber ids.
**Resolution:** §6 now says the report reads subscriber ids from a file given on the command line. A list endpoint would be an additive change later.

**N2 · NON-BLOCKING · deferred requirement.** REQ-ALW-007 is deferred and correctly left undesigned. Noting where it would land (a withdrawal record in the store, an additive contract change) would make reactivating it cheaper.
**Status:** noted in the REQ → component table. No further action.

**N3 · NON-BLOCKING · edge case.** Age on the received date is defined, but the design does not say how a 29 February birthday counts in a non-leap year.
**Status:** open. Raised with the product owner; does not block decomposition because age is worked out in one place and can change alone.

## Sign-off

- [x] All blocking findings resolved before decomposition
- [ ] person-a approves (design PR, G0)
- [ ] person-b approves (design PR, G0)
- [ ] approver: [product owner] signs off the review (evidentiary stop)
