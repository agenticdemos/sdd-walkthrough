# Drift sweep (prompt file)

A prompt a separate reviewer session can run to compare each design with the code it describes and open drift issues. It is optional and not scheduled; a team could run it from a scheduled job later. It reports; a person decides. It never edits code, specs or contracts.

Run it from the repository root, for example:

```text
claude -p "$(cat scripts/drift_sweep.md)" --allowedTools "Skill(sdd),Read,Grep,Glob,Bash(gh issue list:*),Bash(gh issue create:*),Bash(git log:*)"
```

---

Use the sdd skill. You are a drift reviewer. You did not write any of this code or these specs, and you only report.

1. Read `sdd.yaml` to find the specs directory, code directories and contracts directory.
2. For each spec folder that has a `design.md`, read its `requirements.md` and `design.md`, then read the code under the paths in the spec's `covers` front matter and any contract the design names.
3. List each place where the code and the design disagree: a component doing something the design gives to another, a decision the code no longer follows, a rule value or effective date that differs, an interface the code uses that the contract does not describe, or a requirement in the REQ → component table with no code behind it.
4. Before opening an issue, check `gh issue list --label drift --state open` and skip anything already reported.
5. For each new disagreement, open one issue:
   `gh issue create --label drift --title "Drift: <spec id>: <one line>" --body "<design section, file and line, what each says, which REQ is affected>"`
6. Finish with a table: spec, finding, issue URL (or "already open").

Do not edit any file. Do not decide which side is right; the spec owner does.
