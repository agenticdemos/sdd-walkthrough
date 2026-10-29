# CLAUDE.md

Always-on rules for every session in this repo, whatever the task. The method itself lives in the `sdd` project skill (`.claude/skills/sdd/`), which loads when the work needs it; `sdd.yaml` tells it where specs, contracts and the board are.

- Use the sdd skill for any work touching specs, contracts, tasks, tests or landing.
- Before starting, state which stop on the dial this work is at and why.
- Never edit `contracts/` outside a `contract/*` branch. If the contract is wrong or missing something, stop and raise a `contract-change` issue instead.
- Never change `src/` to make a mutant disappear. Add the missing test, or propose a waiver for a person to review.
- Never merge to main except through the queue.
