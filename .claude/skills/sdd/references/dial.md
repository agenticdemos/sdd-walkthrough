# The dial: how much process this work needs

The cost of getting it wrong determines the depth. The dial runs from reversible, throwaway, one-person, low-impact work on the left to shared, long-lived, regulated, high-customer-impact work on the right.

## The five stops

| Stop | What it means |
| --- | --- |
| vibe | Prompt, review, repeat. |
| spec-light | A paragraph and a few checks. |
| spec-driven | EARS requirements, design, tracked tasks. |
| contract-driven | Plus a tested, versioned contract at each interface. |
| evidentiary | Plus evidence per requirement and mutation testing. |

Each stop includes everything from the stops to its left and adds something. Contract-driven work still has numbered EARS requirements and tracked tasks.

No stop is good or bad in itself. Problems come from using the wrong stop for the work in hand. Treating everything as evidentiary, including spikes and throwaway work, is over-specifying: it means the stop was never chosen.

## Choosing a stop: the five questions

Answer all five. Use the right-most stop any answer points to.

| Question | Points left (vibe, spec-light) | Points to the middle | Points right (evidentiary) |
| --- | --- | --- | --- |
| Blast radius | Me, today | My team, this quarter | Customers, money, eligibility, disclosures |
| Reversibility | Delete the branch | Revert and redeploy | Data has moved, letters have gone out |
| Parties | One person, their agents | A second person or team on the other side | Someone outside engineering must approve |
| Lifetime | Hours | The life of the feature | The life of the product, plus retention |
| Who will ask | Nobody | The next engineer | Audit, compliance, a regulator |

- Choose per piece of work rather than per team. One repo can hold specs at several stops.
- The parties question usually moves work to contract-driven: once a second person is building the other side of an interface, you need a contract.
- Before starting, state which stop on the dial this work is at and why. This line belongs in CLAUDE.md.
- Record the stop as `stop:` in the spec's front matter (format in `ears.md`) so CI can enforce it.

## What each stop requires (definition of done)

Each column is the definition of done for that stop. If the spec records its stop in front matter, CI can enforce the column. "＋" means "everything to the left, plus".

| | vibe | spec-light | spec-driven | contract-driven | evidentiary |
| --- | --- | --- | --- | --- | --- |
| Requirements | In your head | A paragraph, a few checks | Numbered EARS | ＋ contracts at each interface | ＋ must-nots, rule source, sign-off |
| Design | None | None | A short design note, reviewed | ＋ versioned contract files | ＋ rejected options, signed-off review |
| Tasks & plan | The chat | A checklist | Tracked tasks citing REQs | ＋ sync gates in the plan | ＋ named approver per gate |
| Tests | Manual check | Happy path | At least one per REQ, named for it | ＋ contract tests on both sides | ＋ no unwaived surviving mutants |
| Evidence | The diff | The diff | Green CI on the PR | ＋ contract changes classified | ＋ evidence pack per REQ, retained |

At the spec-light stop several of these rows become a single paragraph; at the evidentiary stop every row is required. Contract and mutation tests are added only where the stop requires them: mutation testing, for example, only runs for evidentiary specs.

## The gates `dial.py --check` runs

`python3 .claude/skills/sdd/scripts/dial.py` prints every spec, its stop and the gates that apply. `--check` runs the gates the strictest stop requires, using the shell commands under `gates:` in `sdd.yaml`, and fails if a mandatory gate fails.

| Gate (`sdd.yaml` key) | spec-light | spec-driven | contract-driven | evidentiary |
| --- | --- | --- | --- | --- |
| Unit tests (`unit`) | yes | yes | yes | yes |
| Trace: every REQ has a test (`trace`) | — | yes | yes | yes |
| Freshness (`fresh`) | warn | fail | fail | fail |
| Contract tests (`contract`) | — | — | yes | yes |
| Zero unwaived surviving mutants (`mutation`) | — | — | — | yes |
| Evidence pack written (`evidence`) | — | — | — | yes |

The freshness check warns or fails depending on the stop, as the table shows. A vibe stop has no spec, so no gate applies.
