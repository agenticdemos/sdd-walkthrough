# Allowance ledger: design

> **Illustrative.** Figures and rule wording are illustrative. This design says what each part owns and why; file-by-file steps belong in the plan (`tasks.yaml`), not here.

## 1. Scope

A ledger service records ISA subscriptions per subscriber and tax year and decides, as each one arrives, how much is accepted. A separate daily report, built by a second person, flags subscribers close to the end of their allowance. The two meet at one seam: the ledger API contract (§6).

## 2. Components

| Component | Owner | Owns | Side of the seam |
|---|---|---|---|
| Ledger API (`src/ledger/`) | person-a | Receiving subscriptions, working out tax year and age, applying the rules, answering allowance queries, refusing bad input | Provider |
| Rules engine (`src/ledger/rules/`) | person-a | The allowance rules as pure decisions: overall limit, cash sub-limit (§3.2) | Inside the ledger |
| Ledger store (`src/ledger/`) | person-a | Subscribers, accepted subscriptions per tax year, data-quality events (SQLite) | Inside the ledger |
| Breach report (`src/report/`) | person-b | The daily job: asks the ledger for each subscriber's remaining allowance and writes the report | Consumer |
| Contract (`contracts/ledger-api.yaml`) | person-a and person-b | The only thing both sides share | The seam |

## 3. Ledger internals

### 3.1 Tax year and age

The tax year runs 6 April to 5 April and is named by its start year, so 6 April 2027 to 5 April 2028 is tax year 2027. Every subscription is filed under the tax year of the date it was received. Age is computed from the date of birth on the date the subscription is received, never on the day the request is processed.

### 3.2 Rules engine

Each rule is a pure decision with no I/O: it takes what the subscriber has already had accepted in the tax year, the new amount, and (for the cash rule) the tax year and age, and returns the amount accepted and the amount rejected. The API reads totals from the store, asks each rule, takes the smaller accepted amount (the stricter rule wins, whichever order they run in), and records only what was accepted.

- **Overall limit.** £20,000 a tax year. A subscription that would go above it is accepted up to the remaining allowance; only the excess is rejected.
- **Cash sub-limit.** £12,000 of cash a tax year for subscribers under 65, from the tax year starting 6 April 2027. Before that tax year, and for subscribers aged 65 or over, no sub-limit applies and the remaining cash sub-limit is reported as null. Reaching exactly £12,000 is allowed; only an amount above it is excess.
- **Rule values** (limits, the first sub-limit year, the exempt age) are named constants in the rule they belong to, so a change to a rule value is a one-line diff that a reviewer can find.

The rules engine is the evidentiary core: mutation testing runs on it and nowhere else.

### 3.3 Refusals and data quality

A subscription whose subscriber has no date of birth cannot be checked against the cash rule, so it is refused outright (nothing is recorded) and a data-quality event is written to the store for the data team to follow up.

## 4. Data model

| Entity | Fields | Notes |
|---|---|---|
| Subscriber | subscriber id, date of birth (may be missing) | Date of birth is only used to work out age on the received date |
| Subscription | subscriber id, tax year (start year), amount accepted in pence, kind (cash or stocks) | Only accepted amounts are stored, so totals are a sum |
| Data-quality event | kind, detail | Written when input cannot be trusted, such as a missing date of birth |

Money is integer pence everywhere: in the store, in the rules and on the wire.

## 5. REQ → component

| REQ | Component | How |
|---|---|---|
| REQ-ALW-001 | Ledger API, ledger store | Tax year from the received date (§3.1); every subscription stored against it |
| REQ-ALW-002 | Ledger API, contract | Response carries remaining overall allowance and remaining cash sub-limit (null when none applies) |
| REQ-ALW-003 | Rules engine | Cash rule returns no sub-limit for tax years before 2027 (§3.2) |
| REQ-ALW-004 | Rules engine | Cash rule caps cash at £12,000 for under-65s from tax year 2027; excess rejected (§3.2) |
| REQ-ALW-005 | Rules engine | Overall rule caps at £20,000; excess rejected (§3.2) |
| REQ-ALW-006 | Ledger API, ledger store | Missing date of birth refused; data-quality event recorded (§3.3) |
| REQ-ALW-007 | (deferred) | Not designed while deferred; flexible withdrawals would add a withdrawal record to the store and an additive contract change |
| REQ-RPT-001 | Breach report, contract | Reads remaining allowance per subscriber through the allowance query; lists those below the threshold |
| REQ-RPT-002 | Breach report | Any unavailable-ledger error stops the job non-zero before anything is written; the report is written to a temporary file and renamed only on success |

## 6. The seam: the ledger–report contract

The ledger and the report are built by different people, so the interface between them is a contract file, `contracts/ledger-api.yaml` (OpenAPI 3.1, version in `info.version`). Neither side reads the other's code.

- **Record a subscription.** Subscriber id, date of birth, amount in pence, cash or stocks, received date. Returns the tax year, accepted and rejected pence, an outcome (accepted, partially accepted, rejected), the remaining overall allowance and the remaining cash sub-limit (null when no sub-limit applies). A missing date of birth returns a validation error naming it.
- **Query an allowance.** By subscriber id and tax year. Returns both remainders. An unknown subscriber is not found.
- **Who uses what.** The report uses only the allowance query. The contract has no list endpoint, so the report reads the subscriber ids it should check from a file it is given on the command line.

The draft is agreed by both owners at G0, built against in one thin slice per side, then frozen as version 1.0.0 at G1. An additive change is a minor version and needs no new gate; a breaking change is a major version and goes back to G0.

## 7. Decisions

**D1. The rules are pure functions in their own package, separate from the API and the store.**
Rejected: rules written inline in the API handlers (every rule test would need HTTP and a database, and mutation testing would mutate request plumbing as well as rules); rules as SQLite constraints or triggers (hard to test at the boundary, and a refusal would surface as a database error rather than a partial acceptance); a table-driven rules configuration (more machinery than two rules need, and the rule values would live outside the code that is mutation-tested).

**D2. The report reads the ledger only through the API contract.**
Rejected: the report reading the ledger's SQLite file directly (couples the report to the ledger's private schema, so any storage change breaks it silently, and the two owners could no longer work without reading each other's code); a nightly file export from the ledger (adds a second interface to version and test, and the report would see yesterday's figures).

## 8. Not in this design

Flexible-account withdrawals (deferred), authentication, multiple ISA providers, and anything about how the report is delivered to the contact centre.
