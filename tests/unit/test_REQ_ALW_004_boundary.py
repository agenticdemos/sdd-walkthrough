"""The act 5 fix: exactly £12,000 of cash is within the sub-limit (illustrative figure)."""
from ledger.rules.cash_limit import CashDecision, cash_acceptance


def test_REQ_ALW_004_exactly_at_cash_limit_is_accepted():
    assert cash_acceptance(0, 1_200_000, 2028, 30) == CashDecision(1_200_000, 0, False)
    assert cash_acceptance(700_000, 500_000, 2028, 30) == CashDecision(500_000, 0, False)
