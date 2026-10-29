SUB = {"subscriber_id": "S-1", "date_of_birth": "1990-01-01", "kind": "cash"}


def post(client, amount, received="2027-05-01", **over):
    return client.post("/subscriptions", json={**SUB, "amount_pence": amount, "received": received, **over})


def test_REQ_ALW_001_subscription_recorded_against_its_tax_year(client, store):
    r = post(client, 100_000, received="2028-04-05")
    assert r.status_code == 201 and r.json()["tax_year"] == 2027
    assert store.totals("S-1", 2027) == (100_000, 100_000)


def test_REQ_ALW_002_response_carries_both_remainders(client):
    # The cash remainder's VALUE belongs to TASK-07 (cash sub-limit); here only its presence is checked.
    r = post(client, 300_000, kind="stocks")
    body = r.json()
    assert "remaining_cash_sub_limit_pence" in body
    assert {k: v for k, v in body.items() if k != "remaining_cash_sub_limit_pence"} == {
        "subscriber_id": "S-1", "tax_year": 2027, "accepted_pence": 300_000, "rejected_pence": 0,
        "outcome": "accepted", "remaining_allowance_pence": 1_700_000,
    }
    g = client.get("/subscribers/S-1/allowance", params={"tax_year": 2027})
    assert g.status_code == 200
    assert set(g.json()) == {"subscriber_id", "tax_year", "remaining_allowance_pence", "remaining_cash_sub_limit_pence"}
    assert g.json()["remaining_allowance_pence"] == 1_700_000


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
