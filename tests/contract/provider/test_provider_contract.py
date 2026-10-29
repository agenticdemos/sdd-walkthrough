"""Provider side (G2): property-based tests generated from the LOCAL contract file,
run in-process against the FastAPI app. Offline: no server, no network."""
from pathlib import Path

import schemathesis
from hypothesis import settings
from schemathesis.specs.openapi.checks import positive_data_acceptance

from ledger.api import create_app
from ledger.store import Store

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "ledger-api.yaml"

schema = schemathesis.openapi.from_path(str(CONTRACT))
schema.app = create_app(Store())


@schema.parametrize()
@settings(max_examples=50, deadline=None)
def test_REQ_ALW_002_provider_conforms_to_contract(case):
    # Every generated request must get a documented status and a body matching the contract.
    # positive_data_acceptance is excluded: a schema-valid null date_of_birth is REFUSED with
    # 422 by design (REQ-ALW-006), which the contract documents.
    case.call_and_validate(excluded_checks=[positive_data_acceptance])


def test_REQ_ALW_002_contract_version_is_published():
    import yaml

    assert yaml.safe_load(CONTRACT.read_text())["info"]["version"] == "1.0.0"
