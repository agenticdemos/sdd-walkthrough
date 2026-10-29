"""Unit tests for report.client against an in-process httpx transport (no network)."""

import httpx
import pytest

from report.client import LedgerClient, LedgerUnavailable


def client_for(handler) -> LedgerClient:
    return LedgerClient("http://ledger.test", transport=httpx.MockTransport(handler))


def test_allowance_calls_contract_path_with_tax_year():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"], seen["query"] = request.url.path, dict(request.url.params)
        return httpx.Response(200, json={"subscriber_id": "S1", "tax_year": 2027,
                                         "remaining_allowance_pence": 50_000,
                                         "remaining_cash_sub_limit_pence": None})

    body = client_for(handler).allowance("S1", 2027)
    assert seen == {"path": "/subscribers/S1/allowance", "query": {"tax_year": "2027"}}
    assert body["remaining_allowance_pence"] == 50_000


def test_REQ_RPT_002_connect_error_raises_ledger_unavailable():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(LedgerUnavailable):
        client_for(handler).allowance("S1", 2027)


def test_REQ_RPT_002_timeout_raises_ledger_unavailable():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(LedgerUnavailable):
        client_for(handler).allowance("S1", 2027)


def test_REQ_RPT_002_server_error_raises_ledger_unavailable():
    with pytest.raises(LedgerUnavailable):
        client_for(lambda r: httpx.Response(503)).allowance("S1", 2027)


def test_unknown_subscriber_is_not_an_outage():
    with pytest.raises(httpx.HTTPStatusError):
        client_for(lambda r: httpx.Response(404)).allowance("NOPE", 2027)
