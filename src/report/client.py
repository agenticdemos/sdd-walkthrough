"""Thin client for the ledger API, written to contracts/ledger-api.yaml v1 only."""

import httpx


class LedgerUnavailable(Exception):
    """The ledger could not be reached or failed on its side (REQ-RPT-002)."""


class LedgerClient:
    def __init__(self, base_url: str, transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(base_url=base_url, transport=transport, timeout=5.0)

    def allowance(self, subscriber_id: str, tax_year: int) -> dict:
        """GET /subscribers/{id}/allowance: remaining allowance and cash sub-limit, in pence."""
        try:
            resp = self._http.get(
                f"/subscribers/{subscriber_id}/allowance", params={"tax_year": tax_year}
            )
        except httpx.TransportError as exc:  # connect errors and timeouts  # REQ-RPT-002
            raise LedgerUnavailable(f"ledger unreachable: {exc}") from exc
        if resp.status_code >= 500:  # REQ-RPT-002
            raise LedgerUnavailable(f"ledger returned {resp.status_code}")
        resp.raise_for_status()
        return resp.json()
