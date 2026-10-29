# evidence/

Generated. Everything in this folder except this README is git-ignored.

`make evidence` (run by CI on every push to `main`, after a change lands) writes one
bundle per spec and commit:

```
evidence/<spec-id>/<sha>/
  spec.md        the requirements file at that SHA, with its hash and approver line
  trace.md       REQ -> code -> test matrix (trace.py --matrix)
  junit.xml      test results at that SHA
  mutation.txt   mutmut summary, plus any waived survivors with reasons and reviewers
  review.json    PR number, author, role approvals (from the PR body) and GitHub reviews
  README.md      one page tying the files above to each REQ
```

CI uploads the bundle as a build artefact named `evidence-<sha>`; the board links it
on the Done card. To build one locally:

```
make evidence          # evidence/allowance-ledger/<HEAD sha>/
```

Approvals are role-based (`person-a`, `person-b`, as listed in `sdd.yaml`), so a bundle
records which role ticked which box rather than relying on GitHub approving reviews.
All figures in this repo are illustrative.
