---
id: breach-report
stop: contract-driven
covers: [src/report/]
verified_at: null
owner: person-b
---

# Breach report: requirements

> **Illustrative.** Every figure and rule wording in this spec is illustrative, written for a walkthrough. Figures in square brackets, such as £[1,000], are placeholders the product owner sets.

**Stop: contract-driven.** The report is built by a second person against the ledger's interface, so it needs numbered requirements, tracked tasks and a tested, versioned contract. It reads the ledger only through `contracts/ledger-api.yaml` (consumer side).

## Requirements

1. **REQ-RPT-001** (event): WHEN the daily report runs, the report job shall list every subscriber whose remaining overall allowance is below £[1,000].

2. **REQ-RPT-002** (unwanted): IF the ledger API is unavailable, THEN the report job shall exit non-zero and write no partial report.
