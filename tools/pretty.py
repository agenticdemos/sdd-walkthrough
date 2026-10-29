"""Pretty-print ledger JSON (spec-light: specs/cli-pretty/spec.md).

Usage: python tools/pretty.py [FILE]   (reads standard input when FILE is omitted)
"""
import json
import sys


def pretty(text: str) -> str:
    return json.dumps(json.loads(text), indent=2, sort_keys=True, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    text = open(argv[0], encoding="utf-8").read() if argv else sys.stdin.read()
    try:
        print(pretty(text))
    except json.JSONDecodeError as e:
        print(f"pretty: invalid JSON: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
