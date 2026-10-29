"""Consumer contract tests (G2, person B): the report runs against a mock served from the
contract's own examples. Every request the client sends and every response the mock returns
is validated against contracts/ledger-api.yaml with openapi-core. No network, no ledger code."""

import json
from pathlib import Path

import httpx
import pytest
import yaml
from openapi_core import OpenAPI
from openapi_core.datatypes import RequestParameters
from openapi_core.validation.request.exceptions import RequestValidationError
from openapi_core.validation.response.exceptions import ResponseValidationError
from werkzeug.datastructures import Headers, ImmutableMultiDict

from report.client import LedgerClient

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "ledger-api.yaml"
RAW = yaml.safe_load(CONTRACT.read_text())
SPEC = OpenAPI.from_file_path(str(CONTRACT))
BASE_URL = RAW["servers"][0]["url"]
ALLOWANCE = RAW["paths"]["/subscribers/{subscriber_id}/allowance"]["get"]["responses"]


def examples(status: str) -> list[dict]:
    content = ALLOWANCE[status]["content"]["application/json"]
    return [e["value"] for e in content.get("examples", {}).values()]


class OpenAPIRequest:  # httpx.Request -> openapi-core Request protocol
    def __init__(self, req: httpx.Request):
        self.req, self.path, self.method = req, req.url.path, req.method.lower()
        self.host_url = f"{req.url.scheme}://{req.url.netloc.decode()}"
        self.body = req.content or None
        self.content_type = req.headers.get("content-type", "application/json")
        self.parameters = RequestParameters(
            query=ImmutableMultiDict(list(req.url.params.multi_items())),
            header=Headers(dict(req.headers)))


class OpenAPIResponse:  # httpx.Response -> openapi-core Response protocol
    def __init__(self, resp: httpx.Response):
        self.status_code, self.data = resp.status_code, resp.content
        self.content_type = resp.headers.get("content-type", "")
        self.headers = Headers(dict(resp.headers))


def contract_mock(request: httpx.Request) -> httpx.Response:
    """Serve the contract example whose subscriber_id matches; 404 example otherwise."""
    wrapped = OpenAPIRequest(request)
    SPEC.validate_request(wrapped)  # the consumer must send what the contract allows
    sid = request.url.path.split("/")[2]
    match = [e for e in examples("200") if e["subscriber_id"] == sid]
    status, body = (200, match[0]) if match else (404, examples("404")[0])
    response = httpx.Response(status, json=body, request=request)
    SPEC.validate_response(wrapped, OpenAPIResponse(response))  # and the mock honours it
    return response


def mock_client() -> LedgerClient:
    return LedgerClient(BASE_URL, transport=httpx.MockTransport(contract_mock))


def test_contract_is_v1():
    assert RAW["info"]["version"].startswith("1.")


def test_REQ_RPT_001_client_reads_every_contract_example():
    for example in examples("200"):
        got = mock_client().allowance(example["subscriber_id"], example["tax_year"])
        assert got["remaining_allowance_pence"] == example["remaining_allowance_pence"]


def test_unknown_subscriber_gets_contract_404():
    with pytest.raises(httpx.HTTPStatusError) as err:
        mock_client().allowance("S-9999", 2027)
    assert err.value.response.status_code == 404


def test_validator_rejects_request_outside_contract():
    bad = httpx.Request("GET", f"{BASE_URL}/subscribers/S-0001/allowance?tax_year=1999")
    with pytest.raises(RequestValidationError):
        SPEC.validate_request(OpenAPIRequest(bad))


def test_validator_rejects_response_missing_a_contract_field():
    req = httpx.Request("GET", f"{BASE_URL}/subscribers/S-0001/allowance?tax_year=2027")
    body = {k: v for k, v in examples("200")[0].items() if k != "remaining_allowance_pence"}
    resp = httpx.Response(200, content=json.dumps(body).encode(),
                          headers={"content-type": "application/json"})
    with pytest.raises(ResponseValidationError):
        SPEC.validate_response(OpenAPIRequest(req), OpenAPIResponse(resp))
