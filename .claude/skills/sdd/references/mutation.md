# Mutation testing and the evidence pack

## How it works

1. **Mutate.** The tool makes one small change to the code, such as `>` to `>=`, a changed constant or a removed call. Each change is a mutant.
2. **Run.** It runs the test suite against each mutant in turn.
3. **Classify.** Killed: a test failed. Survived: every test passed. Equivalent: the change can't alter behaviour.
4. **Act.** Each survivor is a missing test, so add one. If it is equivalent, record a waiver with the reason.

Mutation score = killed ÷ (all mutants − equivalent). Many teams set a threshold.

Line coverage is not proof: a mutant can survive while line coverage is 100%. Treating coverage as evidence is the mistake mutation testing exists to catch.

Tools: mutmut for Python, Stryker for JavaScript, TypeScript and .NET, PIT for Java. All run locally and in CI.

## Running it

Run it on rule modules only, and only on code that changed. The paths are `mutation.targets` in `sdd.yaml`.

```
python3 .claude/skills/sdd/scripts/mutate.py      # or: make mutate
```

It prints every survivor and fails on any survivor that has no waiver.

For each survivor, report which REQ it belongs to (from the `# REQ-…` anchor nearest the mutated line) and whether a test is missing or the mutant is equivalent. Then:

- **Missing test:** add a REQ-named test that fails on the mutant, such as one at the exact boundary. Rerun.
- **Equivalent:** propose a waiver. Rerun.

Repeat until there are no unwaived survivors.

**Never change the code under test to make a mutant disappear.** An agent can make a mutant disappear by rewriting the code instead of adding the missing test. Nothing under `code_dirs` (from `sdd.yaml`, such as `src/`) changes during this step; only tests and the waivers file do.

## The gate

At the evidentiary stop we require zero unwaived survivors: a change can't land with an unwaived survivor.

## Waivers

Waivers go in the file named by `mutation.waivers` in `sdd.yaml`, as entries under `waivers:` with four fields:

```yaml
waivers:
  - mutant: <mutant id as the mutation run prints it>
    reason: <why the change can't alter behaviour>
    proposed_by: <the role or agent that proposed it>
    reviewed_by: <empty until a person signs>
```

A person reviews every waiver: no survivor without a reviewed waiver. An agent may propose a waiver, giving the reason, but leaves `reviewed_by` empty and marks it for review. `reviewed_by` must be one of the roles in `mutation.approvers`; a waiver without it does not count.

## The evidence pack

CI builds the pack when the change lands, for the commit that actually landed. A pack put together later from memory and screenshots is much weaker evidence.

```
python3 .claude/skills/sdd/scripts/evidence.py <spec-id> [--sha SHA] [--pr N]
```

It writes `<evidence_dir>/<spec-id>/<sha>/`:

| File | Holds |
| --- | --- |
| `spec.md` | Spec version and who approved it: the requirements at that commit, its hash and approver lines |
| `trace.md` | Trace matrix: REQ, code, tests (`trace.py --matrix`) |
| `junit.xml` | Test results for the commit that landed |
| `mutation.txt` | Mutation report, with any waivers and reasons |
| `review.json` | Review record: who, when, what was found (role approvals from the PR body plus any GitHub reviews) |
| `README.md` | One page tying the above to each REQ |
