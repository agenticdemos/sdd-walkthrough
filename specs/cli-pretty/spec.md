---
id: cli-pretty
stop: spec-light
covers: [tools/pretty.py]
verified_at: null
owner: person-a
---

# cli-pretty

> **Illustrative.** A throwaway helper for the walkthrough; nothing depends on it.

`tools/pretty.py` is a small command-line helper that pretty-prints JSON returned by the ledger so it reads well in a terminal or on a projector. It reads JSON from a file named on the command line, or from standard input when no file is given, and prints it indented. It is reversible, used by one person, and nobody will audit it, so a paragraph and a few checks are enough.

Checks:

- [ ] Valid JSON from a file or from standard input is printed indented, with keys sorted.
- [ ] The output is still valid JSON, so it can be piped into another tool.
- [ ] Invalid JSON exits non-zero with a one-line error, not a traceback.
