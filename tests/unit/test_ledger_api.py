SUB = {"subscriber_id": "S-1", "date_of_birth": "1990-01-01", "kind": "cash"}


def post(client, amount, received="2027-05-01", **over):
    return client.post("/subscriptions", json={**SUB, "amount_pence": amount, "received": received, **over})


def test_REQ_ALW_001_subscription_recorded_against_its_tax_year(client, store):
    r = post(client, 100_000, received="2028-04-05")
    assert r.status_code == 201 and r.json()["tax_year"] == 2027
    assert store.totals("S-1", 2027) == (100_000, 100_000)


def test_REQ_ALW_002_response_carries_both_remainders(client):
    r = post(client, 300_000)
    assert r.json() == {
        "subscriber_id": "S-1", "tax_year": 2027, "accepted_pence": 300_000, "rejected_pence": 0,
        "outcome": "accepted", "remaining_allowance_pence": 1_700_000, "remaining_cash_sub_limit_pence": 900_000,
    }
    g = client.get("/subscribers/S-1/allowance", params={"tax_year": 2027})
    assert g.status_code == 200 and g.json()["remaining_cash_sub_limit_pence"] == 900_000


def test_REQ_ALW_003_no_sub_limit_reported_before_2027(client):
    r = post(client, 1_300_000, received="2026-05-01")
    assert r.json()["accepted_pence"] == 1_300_000
    assert r.json()["remaining_cash_sub_limit_pence"] is None


def test_REQ_ALW_004_cash_over_sub_limit_partially_accepted(client):
    r = post(client, 1_300_000)
    assert (r.json()["accepted_pence"], r.json()["rejected_pence"]) == (1_200_000, 100_000)
    assert r.json()["outcome"] == "partially_accepted"


def test_REQ_ALW_005_stocks_over_overall_limit_rejected(client):
    post(client, 2_000_000, kind="stocks")
    r = post(client, 50_000, kind="stocks")
    assert r.json()["outcome"] == "rejected" and r.json()["remaining_allowance_pence"] == 0


def test_REQ_ALW_006_missing_date_of_birth_refused_with_event(client, store):
    r = post(client, 100_000, date_of_birth=None)
    assert r.status_code == 422 and r.json() == {"error": "date_of_birth_missing"}
    assert store.events()[0]["kind"] == "date_of_birth_missing"
    assert store.totals("S-1", 2027) == (0, 0)


def test_REQ_ALW_002_unknown_subscriber_is_404(client):
    assert client.get("/subscribers/nobody/allowance", params={"tax_year": 2027}).status_code == 404
