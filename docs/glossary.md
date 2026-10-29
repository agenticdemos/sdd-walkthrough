# Glossary

> **Illustrative.** The domain is a fictional ISA subscription ledger. Figures and rule wording are illustrative; the specs under `specs/` are the source of truth.

| Term | Meaning |
| --- | --- |
| Allowance | The most a subscriber may pay in across all their ISAs in one tax year (£20,000, illustrative). |
| Cash sub-limit | A lower limit on cash subscriptions for subscribers under 65 (£12,000, illustrative), from the tax year starting 6 April 2027. |
| Contract | The OpenAPI file in `contracts/` that the ledger (provider) and the breach report (consumer) are both tested against. |
| Criticality dial | The five stops (vibe, spec-light, spec-driven, contract-driven, evidentiary) that decide which gates a spec must pass. |
| EARS | Easy Approach to Requirements Syntax: one sentence pattern per requirement (ubiquitous, event, state, unwanted, optional feature). |
| Evidence pack | The files `make evidence` writes for a landed commit, showing how each requirement was met. |
| Excess | The part of a subscription above a limit. Only the excess is rejected. |
| Freshness | Whether a spec is still true of the code it covers, computed from git. |
| Gate | A check a change must pass before it moves on (G0 to G3 on the board; `make check` in CI). |
| Landing queue | Lands ready pull requests onto the base branch one at a time, each tested on the latest base, and ejects any that turn red. |
| Mutant | A small deliberate change to the code. A test suite that still passes has let it survive. |
| Tax year | 6 April to 5 April. How a tax year is labelled is defined in the allowance-ledger spec. |
