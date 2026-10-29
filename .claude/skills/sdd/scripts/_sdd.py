"""Shared helpers for the sdd skill scripts. Standard library only (PyYAML used if present).

Every path comes from sdd.yaml; nothing here knows about any particular repo.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

STOPS = ["vibe", "spec-light", "spec-driven", "contract-driven", "evidentiary"]
GATES = ["unit", "trace", "fresh", "contract", "mutation", "evidence"]
_N = "—"  # em dash: gate does not apply
GATES_BY_STOP: dict[str, dict[str, str]] = {
    "vibe":            dict(unit=_N, trace=_N, fresh=_N, contract=_N, mutation=_N, evidence=_N),
    "spec-light":      dict(unit="yes", trace=_N, fresh="warn", contract=_N, mutation=_N, evidence=_N),
    "spec-driven":     dict(unit="yes", trace="yes", fresh="fail", contract=_N, mutation=_N, evidence=_N),
    "contract-driven": dict(unit="yes", trace="yes", fresh="fail", contract="yes", mutation=_N, evidence=_N),
    "evidentiary":     dict(unit="yes", trace="yes", fresh="fail", contract="yes", mutation="yes", evidence="yes"),
}
DEFAULTS = {"specs_dir": "specs", "base_branch": "main", "req_pattern": r"REQ-[A-Z]+-\d{3}",
            "test_dirs": ["tests"], "code_dirs": ["src"], "contracts_dir": "contracts",
            "evidence_dir": "evidence", "gates": {}}
SPEC_FILES = ["requirements.md", "spec.md"]


# ---------------------------------------------------------------- YAML
def parse_yaml(text: str) -> object:
    """Parse YAML with PyYAML when importable, else with the stdlib subset parser."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return parse_yaml_subset(text)
    return yaml.safe_load(text)


def _strip_comment(s: str) -> str:
    quote = None
    for j, c in enumerate(s):
        if quote:
            if c == quote:
                quote = None
        elif c in "'\"" and (j == 0 or s[j - 1] in " [,{:"):
            quote = c
        elif c == "#" and (j == 0 or s[j - 1] in " \t"):
            return s[:j].rstrip()
    return s.rstrip()


def _split_top(s: str, sep: str) -> list[str]:
    parts, depth, quote, cur = [], 0, None, ""
    for c in s:
        if quote:
            quote = None if c == quote else quote
        elif c in "'\"":
            quote = c
        elif c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
        elif c == sep and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        cur += c
    parts.append(cur)
    return [p.strip() for p in parts]


def _key_split(s: str):
    """Return (key, rest) if s is a `key: value` / `key:` entry, else None."""
    quote = None
    for j, c in enumerate(s):
        if quote:
            quote = None if c == quote else quote
        elif c in "'\"" and j == 0:
            quote = c
        elif c in "[{" and j == 0:
            return None
        elif c == ":" and (j + 1 == len(s) or s[j + 1] == " "):
            return _scalar(s[:j].strip()), s[j + 1:].strip()
    return None


def _scalar(s: str) -> object:
    s = s.strip()
    if s in ("", "~", "null", "Null", "NULL"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if s[0] == "'" and s.endswith("'") and len(s) > 1:
        return s[1:-1].replace("''", "'")
    if s[0] == '"' and s.endswith('"') and len(s) > 1:
        try:
            return json.loads(s)
        except ValueError:
            return s[1:-1]
    if s[0] == "[" and s.endswith("]"):
        inner = s[1:-1].strip()
        return [_scalar(p) for p in _split_top(inner, ",")] if inner else []
    if s[0] == "{" and s.endswith("}"):
        inner = s[1:-1].strip()
        out = {}
        for p in _split_top(inner, ",") if inner else []:
            kv = _key_split(p)
            out[kv[0] if kv else p] = _scalar(kv[1]) if kv else None
        return out
    if re.fullmatch(r"[-+]?\d[\d_]*", s):
        return int(s.replace("_", ""))
    if re.fullmatch(r"[-+]?\d+\.\d+", s):
        return float(s)
    return s


def _is_item(c: str) -> bool:
    return c == "-" or c.startswith("- ")


def parse_yaml_subset(text: str) -> object:
    """Subset: block maps by indent, `- ` lists of scalars or maps, flow [a, b] / {a: b},
    quoted strings, ints, floats, true/false/null and `#` comments."""
    lines = []
    for raw in text.splitlines():
        body = raw.rstrip()
        content = _strip_comment(body.lstrip())
        if not content or content in ("---", "..."):
            continue
        lines.append([len(body) - len(body.lstrip()), content])
    if not lines:
        return None
    if len(lines) == 1 and not _is_item(lines[0][1]) and _key_split(lines[0][1]) is None:
        return _scalar(lines[0][1])
    return _node(lines, 0, lines[0][0])[0]


def _node(lines, i, indent):
    return _list(lines, i, indent) if _is_item(lines[i][1]) else _map(lines, i, indent)


def _child(lines, i, indent, allow_same_indent_list):
    """Value for an entry at line i whose inline value is empty."""
    if i + 1 < len(lines):
        nind, nc = lines[i + 1]
        if nind > indent:
            return _node(lines, i + 1, nind)
        if allow_same_indent_list and nind == indent and _is_item(nc):
            return _list(lines, i + 1, indent)
    return None, i + 1


def _list(lines, i, indent):
    items = []
    while i < len(lines) and lines[i][0] == indent and _is_item(lines[i][1]):
        content = lines[i][1]
        rest = content[1:].lstrip()
        if not rest:
            val, i = _child(lines, i, indent, False)
        elif _key_split(rest) is not None or _is_item(rest):
            lines[i] = [indent + len(content) - len(rest), rest]
            val, i = _node(lines, i, lines[i][0])
        else:
            val, i = _scalar(rest), i + 1
        items.append(val)
    return items, i


def _map(lines, i, indent):
    out = {}
    while i < len(lines) and lines[i][0] == indent and not _is_item(lines[i][1]):
        kv = _key_split(lines[i][1])
        if kv is None:
            raise ValueError(f"cannot parse YAML line: {lines[i][1]!r}")
        key, rest = kv
        if rest:
            out[key], i = _scalar(rest), i + 1
        else:
            out[key], i = _child(lines, i, indent, True)
    return out, i


# ---------------------------------------------------------------- config and specs
def load_config(root: Path | None = None) -> dict:
    """Load sdd.yaml from `root`, or walk up from the current directory to find it."""
    start = Path(root) if root else Path.cwd()
    for d in [start, *start.resolve().parents]:
        f = d / "sdd.yaml"
        if f.is_file():
            config = {**DEFAULTS, **(parse_yaml(f.read_text()) or {})}
            config["root"] = d.resolve()
            return config
    raise SystemExit(f"sdd: no sdd.yaml found in {start} or any parent directory")


def front_matter(path: Path) -> tuple[dict, str]:
    """Split a markdown file into (front matter dict, body)."""
    text = Path(path).read_text()
    m = re.match(r"---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", text, re.S)
    if not m:
        return {}, text
    data = parse_yaml(m.group(1))
    return (data if isinstance(data, dict) else {}), text[m.end():]


def specs(config: dict) -> list[dict]:
    """Every spec under specs_dir: id, stop, covers, verified_at, owner, path, dir."""
    base = config["root"] / config["specs_dir"]
    found = []
    for d in sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []:
        names = SPEC_FILES + sorted(p.name for p in d.glob("*.md") if p.name not in SPEC_FILES)
        for name in names:
            path = d / name
            if not path.is_file():
                continue
            fm, _ = front_matter(path)
            if "stop" not in fm:
                continue
            covers = fm.get("covers") or []
            va = fm.get("verified_at")
            found.append({
                "id": str(fm.get("id") or d.name),
                "stop": str(fm["stop"]),
                "covers": [covers] if isinstance(covers, str) else [str(c) for c in covers],
                "verified_at": None if va in (None, "", "null") else str(va),
                "owner": fm.get("owner"),
                "path": path,
                "dir": d,
            })
            break
    return found


def reqs(spec_path: Path, pattern: str) -> list[tuple[str, str]]:
    """(id, status) for each REQ defined in a requirements file, in order of first mention.

    The first REQ id on a line is the one that line is about; status is `deferred` when a
    line about that REQ contains `status: deferred`, else `active`."""
    path = Path(spec_path)
    if not path.is_file():
        return []
    found: dict[str, str] = {}
    for line in path.read_text().splitlines():
        m = re.search(pattern, line)
        if not m:
            continue
        rid = m.group(0)
        deferred = "status: deferred" in line
        if rid not in found or deferred:
            found[rid] = "deferred" if deferred else found.get(rid, "active")
    return list(found.items())


# ---------------------------------------------------------------- processes and output
class CommandError(RuntimeError):
    pass


def git(*args: str, root: Path | None = None) -> str:
    cmd = ["git", *(["-C", str(root)] if root else []), *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise CommandError(f"$ {' '.join(cmd)}\n{r.stderr.strip()}")
    return r.stdout.strip()


def gh(args: list[str], dry_run: bool) -> str:
    """Run `gh`; always print the command; in dry-run return "" without running it."""
    print("$ gh " + " ".join(_shq(a) for a in args), flush=True)
    if dry_run:
        return ""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise CommandError(f"gh {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def _shq(a: str) -> str:
    return a if re.fullmatch(r"[\w@%+=:,./{}\[\]-]+", a) else "'" + a.replace("'", "'\\''") + "'"


def table(headers: list[str], rows: list[list[str]]) -> str:
    cells = [[str(c) for c in headers]] + [[str(c) for c in r] for r in rows]
    widths = [max(len(r[k]) if k < len(r) else 0 for r in cells) for k in range(len(headers))]
    fmt = lambda r: "  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip()  # noqa: E731
    return "\n".join([fmt(cells[0]), fmt(["-" * w for w in widths])] + [fmt(r) for r in cells[1:]])


def rel(path: Path, config: dict) -> str:
    try:
        return str(Path(path).resolve().relative_to(config["root"]))
    except ValueError:
        return str(path)


def walk(config: dict, dirs: list[str]):
    """Yield text files under the given config-relative dirs (or single files)."""
    for d in dirs:
        p = config["root"] / d
        files = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else []
        for f in files:
            if "__pycache__" in f.parts or f.suffix in (".pyc", ".so", ".png", ".db"):
                continue
            yield f


if __name__ == "__main__":  # pragma: no cover - debugging aid
    print(json.dumps({k: str(v) for k, v in load_config().items()}, indent=2))
    sys.exit(0)
