#!/usr/bin/env python3
"""Board: mirror specs and tasks onto GitHub Issues + a Project; move cards.

  board.py bootstrap [--dry-run]       labels, project, fields, issues, sub-issues
  board.py move TASK STATUS [--pr N] [--evidence URL] [--dry-run]
  board.py reset [--dry-run]           every task back to sdd.yaml board.seed
Every name comes from sdd.yaml `board:`; every gh call goes through _sdd.gh.
"""
import argparse, json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _sdd  # noqa: E402

LABELS = {"feature": "1d76db", "task": "0e8a16", "ready-to-land": "5319e7",
          "ejected": "b60205", "drift": "fbca04", "contract-change": "d93f0b"}


def _json(out, default):
    try:
        return json.loads(out) if out and out.strip() else default
    except json.JSONDecodeError:
        return default


def key_of(title):
    m = re.search(r"TASK-\d\d", title)
    return m.group(0) if m else title.split(" · ")[0]


def load_tasks(cfg):
    path = Path(cfg["root"]) / cfg["board"]["tasks"]
    data = _sdd.parse_yaml(path.read_text())
    tasks = data.get("tasks", []) if isinstance(data, dict) else (data or [])
    return path, tasks


def as_list(v):
    if v is None:
        return []
    return [str(x).strip() for x in (v if isinstance(v, list) else str(v).split(","))]


class Board:
    def __init__(self, cfg, dry):
        self.cfg, self.b, self.dry = cfg, cfg["board"], dry
        self.repo, self.owner = self.b["repo"], str(self.b["owner"])

    def gh(self, *args):
        return _sdd.gh([str(a) for a in args], self.dry)

    def specs_for_fields(self):
        return {"Status": self.b["statuses"], "REQs": None, "Dial stop": _sdd.STOPS,
                "Gate": self.b["gates"], "Owner": self.b["owners"]}

    def project(self, create=False):
        name = self.b["project"]
        data = _json(self.gh("project", "list", "--owner", self.owner, "--format", "json", "--limit", "100"), {})
        for p in data.get("projects", []):
            if p.get("title") == name:
                return p
        if self.dry:
            return {"number": "<project>", "id": "<project-id>"}
        if not create:
            sys.exit(f"project {name!r} not found under {self.owner}; run board.py bootstrap")
        print(f"creating project {name!r}")
        return _json(self.gh("project", "create", "--owner", self.owner, "--title", name, "--format", "json"), {})

    def fields(self, num):
        if self.dry:  # synthesise ids so the dry run shows every item-edit
            return {n: {"id": f"<{n}>", "options": [{"id": f"<{o}>", "name": o} for o in opts]}
                    if opts else {"id": f"<{n}>"} for n, opts in self.specs_for_fields().items()}
        data = _json(self.gh("project", "field-list", num, "--owner", self.owner, "--format", "json", "--limit", "100"), {})
        return {f["name"]: f for f in data.get("fields", [])}

    def ensure_fields(self, num):
        have = self.fields(num)
        for name, opts in self.specs_for_fields().items():
            f = have.get(name)
            if f is None:
                print(f"creating field {name}")
                kind = ["--data-type", "TEXT"] if opts is None else \
                    ["--data-type", "SINGLE_SELECT", "--single-select-options", ",".join(opts)]
                self.gh("project", "field-create", num, "--owner", self.owner, "--name", name, *kind)
            elif opts and [o["name"] for o in f.get("options", [])] != list(opts):
                print(f"setting {name} options to {', '.join(opts)}")  # e.g. the default Status field
                keep = {o["name"]: o["id"] for o in f.get("options", [])}
                items = ", ".join('{name: %s, color: GRAY, description: ""%s}'
                                  % (json.dumps(o), f', id: "{keep[o]}"' if o in keep else "") for o in opts)
                q = 'mutation { updateProjectV2Field(input: {fieldId: "%s", singleSelectOptions: [%s]}) ' \
                    '{ clientMutationId } }' % (f["id"], items)
                self.gh("api", "graphql", "-f", f"query={q}")
        return self.fields(num)

    def issues(self):
        out = self.gh("issue", "list", "--repo", self.repo, "--state", "all", "--limit", "500",
                      "--json", "number,title,url")
        return {key_of(i["title"]): i for i in _json(out, [])}

    def issue(self, issues, key, title, body, label):
        if key in issues:
            print(f"exists  #{issues[key]['number']} {title}")
            return issues[key], False
        print(f"creating issue {title}")
        url = self.gh("issue", "create", "--repo", self.repo, "--title", title, "--body", body, "--label", label).strip()
        num = url.rstrip("/").split("/")[-1] if url else f"<{key}>"
        return {"number": num, "url": url or f"https://github.com/{self.repo}/issues/{num}", "title": title}, True

    def add_item(self, proj, url):
        args = ("project", "item-add", proj["number"], "--owner", self.owner, "--url", url, "--format", "json")
        try:
            out = self.gh(*args)
        except _sdd.CommandError as e:
            # GitHub can auto-add a sub-issue whose parent is on the board; adding it again then races.
            if "already exists" not in str(e):
                raise
            print("  item already on the board (added with its parent); re-reading it")
            time.sleep(2)
            out = self.gh(*args)
        return _json(out, {}).get("id", "<item>")

    def set_field(self, proj, fields, item, name, value):
        f = fields.get(name)
        if f is None or value in (None, ""):
            return
        if "options" in f:
            oid = next((o["id"] for o in f["options"] if o["name"] == value), None)
            if oid is None:
                print(f"  ! field {name} has no option {value!r}")
                return
            val = ["--single-select-option-id", oid]
        else:
            val = ["--text", value]
        print(f"  {name} = {value}")
        self.gh("project", "item-edit", "--id", item, "--project-id", proj["id"], "--field-id", f["id"], *val)


def task_body(t):
    return "\n".join([f"**REQs:** {', '.join(as_list(t.get('reqs')))}", f"**Design:** {t.get('design', '')}",
                      f"**Area:** `{t.get('area', '')}`", f"**Done means:** {t.get('done', '')}",
                      f"**Gate:** {t.get('gate', '—')}", f"**Owner:** {', '.join(as_list(t.get('owner'))) or '—'}"])


def pick(value, allowed):
    """First allowed name mentioned in value ('after G1' -> 'G1')."""
    text = ", ".join(as_list(value))
    return next((a for a in allowed if re.search(rf"\b{re.escape(a)}\b", text)), None)


def bootstrap(cfg, dry):
    bd, root = Board(cfg, dry), Path(cfg["root"])
    for name, color in LABELS.items():
        bd.gh("label", "create", name, "--repo", bd.repo, "--color", color, "--force")
    proj = bd.project(create=True)
    fields = bd.ensure_fields(proj["number"])
    issues, tasks_path = bd.issues(), load_tasks(cfg)
    path, tasks = tasks_path
    parents = {}
    for spec in _sdd.specs(cfg):
        sp = root / spec["path"]
        reqs = [r for r, _ in _sdd.reqs(sp, cfg["req_pattern"])]
        body = f"**Spec:** `{sp.relative_to(root)}`\n**Dial stop:** {spec['stop']}\n**REQs:** {', '.join(reqs)}"
        iss, _ = bd.issue(issues, spec["id"], f"{spec['id']} · feature", body, "feature")
        item = bd.add_item(proj, iss["url"])
        for name, val in (("REQs", ", ".join(reqs)), ("Dial stop", spec["stop"]), ("Owner", spec.get("owner"))):
            bd.set_field(proj, fields, item, name, val)
        parents[(root / spec["dir"]).resolve()] = (iss, spec)
    parent, spec = parents.get(path.parent.resolve(), (None, {}))
    linked = set()
    if parent and not dry:
        out = bd.gh("api", f"repos/{bd.repo}/issues/{parent['number']}/sub_issues", "--jq", "[.[].number]")
        linked = {str(n) for n in _json(out, [])}
    for t in tasks:
        iss, _ = bd.issue(issues, t["id"], f"{t['id']} · {t['title']}", task_body(t), "task")
        if parent and str(iss["number"]) not in linked:
            print(f"  sub-issue of #{parent['number']}")
            rid = bd.gh("api", f"repos/{bd.repo}/issues/{iss['number']}", "--jq", ".id").strip() or "<id>"
            bd.gh("api", "-X", "POST", f"repos/{bd.repo}/issues/{parent['number']}/sub_issues",
                  "-F", f"sub_issue_id={rid}")
        item = bd.add_item(proj, iss["url"])
        values = {"Status": cfg["board"].get("seed", {}).get(t["id"], cfg["board"]["statuses"][0]),
                  "REQs": ", ".join(as_list(t.get("reqs"))), "Dial stop": spec.get("stop"),
                  "Gate": pick(t.get("gate"), cfg["board"]["gates"]),
                  "Owner": pick(t.get("owner"), cfg["board"]["owners"])}
        for name, val in values.items():
            bd.set_field(proj, fields, item, name, val)
    print(f"board ready: project {proj.get('url') or proj['number']}")


def move(cfg, task, status, pr=None, evidence=None, dry=False, bd=None, proj=None, fields=None, issues=None):
    if status not in cfg["board"]["statuses"]:
        sys.exit(f"unknown status {status!r}; expected one of {cfg['board']['statuses']}")
    bd = bd or Board(cfg, dry)
    proj = proj or bd.project()
    fields = fields or bd.fields(proj["number"])
    issues = bd.issues() if issues is None else issues
    iss = issues.get(task) or ({"number": f"<{task}>", "url": f"https://github.com/{bd.repo}/issues/<{task}>"}
                               if dry else sys.exit(f"no issue found for {task}; run board.py bootstrap"))
    print(f"{task} (#{iss['number']}) -> {status}")
    bd.set_field(proj, fields, bd.add_item(proj, iss["url"]), "Status", status)
    if pr or evidence:
        note = f"Moved to **{status}**" + (f" · PR #{pr}" if pr else "") + (f" · evidence: {evidence}" if evidence else "")
        bd.gh("issue", "comment", iss["number"], "--repo", bd.repo, "--body", note)


def reset(cfg, dry):
    bd = Board(cfg, dry)
    proj = bd.project()
    fields, issues = bd.fields(proj["number"]), bd.issues()
    seed = cfg["board"].get("seed", {})
    for t in load_tasks(cfg)[1]:
        move(cfg, t["id"], seed.get(t["id"], cfg["board"]["statuses"][0]), dry=dry, bd=bd, proj=proj,
             fields=fields, issues=issues)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print gh commands, touch nothing")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bootstrap")
    sub.add_parser("reset")
    mv = sub.add_parser("move")
    mv.add_argument("task"), mv.add_argument("status")
    mv.add_argument("--pr"), mv.add_argument("--evidence")
    for p in sub.choices.values():
        p.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    cfg = _sdd.load_config()
    if a.cmd == "bootstrap":
        bootstrap(cfg, a.dry_run)
    elif a.cmd == "reset":
        reset(cfg, a.dry_run)
    else:
        move(cfg, a.task, a.status, a.pr, a.evidence, a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
