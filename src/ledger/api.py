"""FastAPI provider for contracts/ledger-api.yaml."""
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import re

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from ledger.rules.overall import OVERALL_LIMIT_PENCE, overall_acceptance
from ledger.store import Store
from ledger.taxyear import tax_year


class SubscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subscriber_id: str = Field(min_length=1, max_length=64)
    date_of_birth: date | None
    amount_pence: StrictInt = Field(ge=1, le=100_000_000)
    kind: Literal["cash", "stocks"]
    received: date

    @field_validator("date_of_birth", "received", mode="before")
    @classmethod
    def _iso_date_only(cls, v):
        if v is not None and not (isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)):
            raise ValueError("expected an ISO date YYYY-MM-DD")
        return v


def _remaining(store: Store, sid: str, year: int) -> tuple[int, int | None]:
    # REQ-ALW-002: both remainders; the cash one is None when no sub-limit applies
    total, _cash = store.totals(sid, year)
    overall_left = max(OVERALL_LIMIT_PENCE - total, 0)
    # TASK-07: cash sub-limit goes here (until then none applies, so the cash remainder is None)
    return overall_left, None


def create_app(store: Store | None = None) -> FastAPI:
    store = store or Store()
    app = FastAPI(title="Allowance ledger", version="1.0.0")
    app.state.store = store

    @app.post("/subscriptions", status_code=201)
    def subscribe(req: SubscriptionRequest):
        dob = req.date_of_birth
        if dob is None:
            # REQ-ALW-006: refuse and emit a data-quality event
            store.record_event("date_of_birth_missing", {
                "subscriber_id": req.subscriber_id,
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
            return JSONResponse(status_code=422, content={"error": "date_of_birth_missing"})
        store.add_subscriber(req.subscriber_id, dob)
        year = tax_year(req.received)  # REQ-ALW-001
        total, _cash = store.totals(req.subscriber_id, year)
        accepted, _ = overall_acceptance(total, req.amount_pence)  # REQ-ALW-005
        # TASK-07: cash sub-limit goes here
        if accepted:
            store.record(req.subscriber_id, year, accepted, req.kind)
        rejected = req.amount_pence - accepted
        outcome = "accepted" if not rejected else "partially_accepted" if accepted else "rejected"
        overall_left, cash_left = _remaining(store, req.subscriber_id, year)
        return {
            "subscriber_id": req.subscriber_id, "tax_year": year,
            "accepted_pence": accepted, "rejected_pence": rejected, "outcome": outcome,
            "remaining_allowance_pence": overall_left, "remaining_cash_sub_limit_pence": cash_left,
        }

    @app.get("/subscribers/{subscriber_id}/allowance")
    def allowance(subscriber_id: str, tax_year: int = Query(ge=2000, le=2100)):
        if store.subscriber_dob(subscriber_id) is None:
            return JSONResponse(status_code=404, content={"error": "subscriber_not_found"})
        overall_left, cash_left = _remaining(store, subscriber_id, tax_year)
        return {
            "subscriber_id": subscriber_id, "tax_year": tax_year,
            "remaining_allowance_pence": overall_left, "remaining_cash_sub_limit_pence": cash_left,
        }

    return app


app = create_app()
