---
id: allowance-ledger
stop: evidentiary
covers: [src/ledger/, contracts/ledger-api.yaml]
verified_at: 51135b1
owner: person-a
---

# Allowance ledger: requirements

> **Illustrative.** Every figure, date and rule wording in this spec is illustrative, written for a walkthrough. It is not the actual ISA rule set. Check the actual rule wording before using anything like this in a real spec.

**Stop: evidentiary.** The ledger decides how much of a customer's money is accepted, the rules come from outside engineering, a second person builds against its interface, and audit may ask how each rule was met.

## Definitions

- **Tax year:** 6 April to 5 April. A tax year is labelled by the year it ends in (6 April 2027 to 5 April 2028 is tax year 2028). Dates in the requirements below are unaffected by the label.
- **Age:** the subscriber's age on the date the subscription is received.
- **Amounts:** whole pence, as integers. No fractions of a penny.
- **Excess:** the part of a subscription above a limit. Only the excess is rejected; the rest of the subscription is accepted.

## Requirements

1. **REQ-ALW-001** (ubiquitous): The ledger shall record every subscription against the UK tax year, 6 April to 5 April, in which it is received.
   - source: [rule reference — illustrative]
   - evidence: REQ-named tests; no unwaived surviving mutants in `src/ledger/rules/`; reviewer ≠ author
   - approver: [product owner]

2. **REQ-ALW-002** (event): WHEN a subscription is received, the ledger shall return the subscriber’s remaining overall allowance and remaining cash sub-limit for that tax year.
   - source: [rule reference — illustrative]
   - evidence: REQ-named tests; no unwaived surviving mutants in `src/ledger/rules/`; reviewer ≠ author
   - approver: [product owner]

3. **REQ-ALW-003** (state): WHILE the tax year starts before 6 April 2027, the ledger shall apply no cash sub-limit.
   - source: [rule reference — illustrative]
   - effective: tax years starting before 6 April 2027
   - evidence: REQ-named tests; no unwaived surviving mutants in `src/ledger/rules/`; reviewer ≠ author
   - approver: [product owner]

4. **REQ-ALW-004** (must-not): WHILE the tax year starts on or after 6 April 2027, IF a cash subscription would take a subscriber under 65 above £12,000 of cash subscriptions in that tax year, THEN the ledger shall accept only the remaining cash sub-limit and reject the excess.
   - source: [rule reference — illustrative]
   - effective: 6 April 2027 (tax year 2027/28, labelled 2028, onwards)
   - evidence: REQ-named tests; no unwaived surviving mutants in `src/ledger/rules/`; reviewer ≠ author
   - approver: [product owner]

5. **REQ-ALW-005** (must-not): IF a subscription would take a subscriber above £20,000 in a tax year, THEN the ledger shall reject the excess.
   - source: [rule reference — illustrative]
   - evidence: REQ-named tests; no unwaived surviving mutants in `src/ledger/rules/`; reviewer ≠ author
   - approver: [product owner]

6. **REQ-ALW-006** (unwanted): IF the subscriber’s date of birth is missing, THEN the ledger shall refuse the subscription and emit a data-quality event.
   - source: [rule reference — illustrative]
   - evidence: REQ-named tests; no unwaived surviving mutants in `src/ledger/rules/`; reviewer ≠ author
   - approver: [product owner]

7. **REQ-ALW-007** (optional feature, status: deferred): WHERE the account is flexible, the ledger shall restore withdrawn cash to the available allowance within the same tax year.
   - source: [rule reference — illustrative]
   - evidence: none until the requirement is made active
   - approver: [product owner]

## Answers recorded at requirements review

The product owner answered these questions before the requirements were written. They are defaults the implementing agent no longer has to guess.

- Age is measured on the date the subscription is received.
- The cash sub-limit is £12,000 a tax year for subscribers under 65, from the tax year starting 6 April 2027, and does not apply before then.
- The overall allowance is £20,000 a tax year.
- Amounts are whole pence.
- Only the excess over a limit is rejected; the rest of the subscription is accepted.
- A missing date of birth refuses the subscription and raises a data-quality event.
- Flexible withdrawals are out of scope for now; the requirement is recorded as deferred.
- The approver is the product owner.
