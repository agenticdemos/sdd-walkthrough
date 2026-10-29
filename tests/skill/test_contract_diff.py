"""contract_diff.py: breaking needs a major bump, additive a minor bump, no change is OK."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude/skills/sdd/scripts"))
import _sdd  # noqa: E402
import contract_diff  # noqa: E402

BASE = """\
openapi: 3.1.0
info:
  title: Demo
  version: {version}
paths:
  /things:
    post:
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required:
                - name
{extra_required}              properties:
                name:
                  type: string
                note:
                  type: string
      responses:
        '201':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Thing'
components:
  schemas:
    Thing:
      type: object
      properties:
        id:
          type: string
{fields}"""
FULL = "        size:\n          type: integer\n"


def contract(version="1.0.0", fields=FULL, extra_required=""):
    return BASE.format(version=version, fields=fields, extra_required=extra_required)


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "sdd.yaml").write_text("base_branch: main\ncontracts_dir: contracts\n")
    (tmp_path / "contracts").mkdir()
    (tmp_path / "contracts/api.yaml").write_text(contract())
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    subprocess.run([*git, "add", "."], cwd=tmp_path, check=True)
    subprocess.run([*git, "commit", "-qm", "v1"], cwd=tmp_path, check=True)
    return tmp_path


@pytest.mark.parametrize("text, failures, kind", [
    (contract(), 0, "no surface change"),
    (contract(fields=""), 1, "BREAKING"),                                     # removed response field
    (contract("1.1.0", fields=""), 1, "BREAKING"),                            # minor is not enough
    (contract("2.0.0", fields=""), 0, "BREAKING"),
    (contract(fields=FULL + "        colour:\n          type: string\n"), 1, "additive"),
    (contract("1.1.0", fields=FULL + "        colour:\n          type: string\n"), 0, "additive"),
    (contract("1.1.0", extra_required="                - note\n"), 1, "BREAKING"),  # newly required
    (contract("2.0.0", extra_required="                - note\n"), 0, "BREAKING"),
])
def test_version_bump_matches_change(repo, capsys, text, failures, kind):
    (repo / "contracts/api.yaml").write_text(text)
    assert contract_diff.check(_sdd.load_config(repo), "main") == failures
    assert kind in capsys.readouterr().out


def test_removed_operation_is_breaking():
    old = _sdd.parse_yaml(contract())
    new = _sdd.parse_yaml(contract())
    new["paths"]["/things"]["get"] = {"responses": {"200": {"description": "ok"}}}
    breaking, additive = contract_diff.classify(new, old)
    assert breaking == ["removed operation GET /things"] and not additive
    breaking, additive = contract_diff.classify(old, new)
    assert additive == ["added operation GET /things"] and not breaking


def test_main_exit_code(repo, monkeypatch):
    monkeypatch.chdir(repo)
    assert contract_diff.main([]) == 0
    (repo / "contracts/api.yaml").write_text(contract(fields=""))
    assert contract_diff.main(["--base", "main"]) == 1
