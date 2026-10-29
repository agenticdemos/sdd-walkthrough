# Writing requirements in EARS

Requirements live in `<specs_dir>/<spec-id>/requirements.md` (`specs_dir` from `sdd.yaml`).

## Before you write anything

1. State the stop on the dial and why (see `dial.md`).
2. List every ambiguity you would otherwise have to guess, as numbered questions, and wait for the answers. Take the list to the product owner. An agent is for rewriting a paragraph of requirements in EARS and listing each ambiguity it had to resolve, not for inventing requirements.
3. Put every answer into the requirement text, so the implementing agent never has to guess it.

No code is written at the requirements stage.

## The five patterns

| Pattern | Form | Test it implies |
| --- | --- | --- |
| Ubiquitous | The <system> shall … | a plain unit test |
| Event-driven | WHEN <trigger>, the <system> shall … | an event test |
| State-driven | WHILE <state>, the <system> shall … | set up the state, then test |
| Unwanted behaviour | IF <condition>, THEN the <system> shall … | a fault or must-not test |
| Optional feature | WHERE <feature>, the <system> shall … | a test per feature variant |

The combined form is the one used most for business rules: WHILE <state>, WHEN <trigger>, the <system> shall …. For example: "WHILE the tax year starts on or after 6 April 2027, WHEN a cash subscription is received from a subscriber under 65, the ledger shall accept no more than the remaining cash sub-limit."

Shape: any number of preconditions, at most one trigger, one system, and one or more responses. With more than three preconditions, use a decision table or a state diagram instead.

## Writing rules

- Each requirement uses exactly one EARS pattern and has its own number, matching `req_pattern` in `sdd.yaml` (for example `REQ-ALW-001`).
- Number once; never reuse a retired number. A requirement that is out of scope for now stays, marked `status: deferred` on its header line.
- Avoid vague words such as "quickly", "appropriate", "etc.".
- Write must-nots as IF … THEN … shall reject or refuse.
- Name rule values such as limits and dates.
- Name tests after the requirement and include the REQ id in each test name, such as `test_REQ_ALW_003_…`.

## Evidentiary requirements

At the evidentiary stop, each requirement carries labelled lines under it. Write the evidence lines before any code exists.

- `source:` the rule reference the requirement comes from
- `effective:` the date the rule starts to apply, where relevant
- `evidence:` what will prove it, such as REQ-named unit and boundary tests, and no unwaived surviving mutants in the mutation targets
- `review:` reviewer is not the author
- `approver:` the role that signs the requirement off, such as the product owner

## Output format

Write `requirements.md` in exactly this shape. Keep each REQ id on its header line; trace and evidence tools read it from there.

```markdown
---
id: allowance-ledger
stop: evidentiary
covers: [src/ledger/, contracts/ledger-api.yaml]
verified_at: null
owner: person-a
---
# Allowance ledger: requirements

> Illustrative: figures and rule wording are examples. Check the actual rule wording before relying on them.

### REQ-ALW-004 · must-not · stop: evidentiary
WHILE the tax year starts on or after 6 April 2027, IF a cash subscription would take a subscriber under 65 above £12,000 of cash subscriptions in that tax year, THEN the ledger shall accept only the remaining cash sub-limit and reject the excess.
- source: [rule reference]
- effective: 6 Apr 2027
- evidence: REQ-named unit and boundary tests
- evidence: no unwaived surviving mutants
- review: reviewer is not the author
- approver: [product owner role]

### REQ-ALW-007 · optional feature · status: deferred
WHERE …, the ledger shall …
```

Below the evidentiary stop, leave out the labelled lines. At spec-light, write one paragraph and a few checks instead of numbered requirements.

## Spec front matter

Every spec file starts with front matter. CI reads it.

| Key | Meaning |
| --- | --- |
| `id` | The spec's id, the same as its folder name |
| `stop` | vibe, spec-light, spec-driven, contract-driven or evidentiary |
| `covers` | The paths this spec governs (code, contracts) |
| `verified_at` | The commit the spec was last checked against the code; `null` until first checked |
| `owner` | The human role who answers for the spec |

The examples in this file are illustrative; check the actual rule wording before using anything like them in a real spec. EARS: Mavin et al., Rolls-Royce, RE'09.
