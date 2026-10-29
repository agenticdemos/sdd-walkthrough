#!/usr/bin/env python3
"""Contract diff: classify each contracts_dir/*.yaml change against a base ref.

  breaking  removed path / operation / response field, or a newly required request field
            -> needs a MAJOR info.version bump (and goes back to G0)
  additive  added path / operation / response field / optional request field
            -> needs at least a MINOR bump
  none      unchanged surface -> OK
Exits 1 when any contract's info.version is not bumped to match its change.
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _sdd  # noqa: E402

METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


def resolve(doc, schema, depth=0):
    while isinstance(schema, dict) and "$ref" in schema and depth < 20:
        node = doc
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = (node or {}).get(part, {})
        schema, depth = node, depth + 1
    return schema if isinstance(schema, dict) else {}


def fields(doc, schema, prefix="", depth=0):
    """Dotted property names reachable from a schema ('items[].id')."""
    s = resolve(doc, schema)
    out = set()
    if depth > 8:
        return out
    for sub in s.get("allOf", []) or []:
        out |= fields(doc, sub, prefix, depth + 1)
    if s.get("type") == "array" or "items" in s:
        out |= fields(doc, s.get("items", {}), prefix + "[]", depth + 1)
    for name, sub in (s.get("properties") or {}).items():
        out.add(prefix + "." + name if prefix else name)
        out |= fields(doc, sub, (prefix + "." if prefix else "") + name, depth + 1)
    return out


def surface(doc):
    """(paths, operations, response fields, request fields, required request fields)."""
    paths, ops, resp, req, required = set(), set(), set(), set(), set()
    for path, item in ((doc or {}).get("paths") or {}).items():
        paths.add(path)
        for method, op in (item or {}).items():
            if method not in METHODS or not isinstance(op, dict):
                continue
            key = f"{method.upper()} {path}"
            ops.add(key)
            for code, r in (op.get("responses") or {}).items():
                for media in (resolve(doc, r).get("content") or {}).values():
                    resp |= {f"{key} {code} {f}" for f in fields(doc, (media or {}).get("schema", {}))}
            for media in (resolve(doc, op.get("requestBody", {})).get("content") or {}).values():
                s = resolve(doc, (media or {}).get("schema", {}))
                req |= {f"{key} {f}" for f in fields(doc, s)}
                required |= {f"{key} {f}" for f in s.get("required", []) or []}
            for p in op.get("parameters", []) or []:
                p = resolve(doc, p)
                req.add(f"{key} {p.get('in')}:{p.get('name')}")
                if p.get("required"):
                    required.add(f"{key} {p.get('in')}:{p.get('name')}")
    return paths, ops, resp, req, required


def classify(old, new):
    """Return (breaking reasons, additive reasons)."""
    (op_, oo, orr, oq, oreq), (np_, no, nr, nq, nreq) = surface(old), surface(new)
    breaking = [f"removed path {p}" for p in sorted(op_ - np_)]
    breaking += [f"removed operation {o}" for o in sorted(oo - no) if o.split(" ", 1)[1] in np_]
    breaking += [f"removed response field {f}" for f in sorted(orr - nr) if f.split(" ")[0] + " " + f.split(" ")[1] in no]
    breaking += [f"newly required request field {f}" for f in sorted(nreq - oreq)
                 if " ".join(f.split(" ")[:2]) in oo]
    additive = [f"added path {p}" for p in sorted(np_ - op_)]
    additive += [f"added operation {o}" for o in sorted(no - oo) if o.split(" ", 1)[1] in op_]
    additive += [f"added response field {f}" for f in sorted(nr - orr) if " ".join(f.split(" ")[:2]) in oo]
    additive += [f"added request field {f}" for f in sorted(nq - oq) if " ".join(f.split(" ")[:2]) in oo
                 and f not in nreq]
    return breaking, additive


def version(doc):
    v = str(((doc or {}).get("info") or {}).get("version", "0.0.0"))
    nums = [int(x) for x in re.findall(r"\d+", v)[:3]]
    return tuple(nums + [0] * (3 - len(nums)))


def check(cfg, base):
    root, cdir = Path(cfg["root"]), cfg["contracts_dir"]
    try:
        listed = _sdd.git("ls-tree", "--name-only", base, f"{cdir}/", root=root).splitlines()
    except _sdd.CommandError as e:
        raise SystemExit(f"cannot read {base}: {e}")
    names = sorted({Path(p).name for p in listed if p.endswith((".yaml", ".yml"))}
                   | {p.name for p in (root / cdir).glob("*.y*ml")})
    failures = 0
    for name in names:
        rel, path = f"{cdir}/{name}", root / cdir / name
        old = _sdd.parse_yaml(_sdd.git("show", f"{base}:{rel}", root=root)) if f"{cdir}/{name}" in listed else None
        new = _sdd.parse_yaml(path.read_text()) if path.is_file() else None
        if old is None or new is None:
            print(f"{rel}: {'new contract' if old is None else 'contract deleted (breaking)'}")
            failures += new is None
            continue
        breaking, additive = classify(old, new)
        ov, nv = version(old), version(new)
        vs = f"{'.'.join(map(str, ov))} -> {'.'.join(map(str, nv))}"
        if breaking:
            kind, ok = "BREAKING", nv[0] > ov[0]
            need = "a major bump (and a return to G0)"
        elif additive:
            kind, ok = "additive", nv[:2] > ov[:2]
            need = "at least a minor bump"
        else:
            kind, ok, need = "no surface change", True, ""
        print(f"{rel}: {kind} (version {vs})")
        for reason in breaking + additive:
            print(f"  - {reason}")
        if not ok:
            failures += 1
            print(f"  FAIL: {kind} change needs {need}; info.version is {vs}")
        else:
            print("  OK")
    return failures


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="git ref to compare against (default: sdd.yaml base_branch)")
    a = ap.parse_args(argv)
    cfg = _sdd.load_config()
    base = a.base or cfg["base_branch"]
    print(f"comparing {cfg['contracts_dir']}/ against {base}")
    failures = check(cfg, base)
    print("contract versions OK" if not failures else f"{failures} contract(s) need a version bump")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
