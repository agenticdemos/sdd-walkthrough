"""Rule tests. Figures are illustrative. REQ-ALW-004's exact-boundary test lives in its own file."""
from ledger.rules.cash_limit import CashDecision, cash_acceptance, sub_limit_applies
from ledger.rules.overall import overall_acceptance

POUND = 100


def test_REQ_ALW_003_no_cash_sub_limit_before_2027_28():
    assert cash_acceptance(0, 13_000 * POUND, 2027, 30) == CashDecision(13_000 * POUND, 0, False)
    assert not sub_limit_applies(2027, 30)
    assert sub_limit_applies(2028, 30)


def test_REQ_ALW_004_under_cash_limit_is_accepted():
    assert cash_acceptance(0, 11_000 * POUND, 2028, 30) == CashDecision(11_000 * POUND, 0, False)


def test_REQ_ALW_004_over_cash_limit_rejects_the_excess():
    assert cash_acceptance(0, 13_000 * POUND, 2028, 30) == CashDecision(12_000 * POUND, 1_000 * POUND, True)
    assert cash_acceptance(5_000 * POUND, 8_000 * POUND, 2028, 30) == CashDecision(
        7_000 * POUND, 1_000 * POUND, True
    )


def test_REQ_ALW_004_sub_limit_already_used_rejects_everything():
    assert cash_acceptance(12_000 * POUND, 1 * POUND, 2028, 30) == CashDecision(0, 1 * POUND, True)


def test_REQ_ALW_004_over_65_is_exempt():
    assert cash_acceptance(0, 13_000 * POUND, 2028, 65) == CashDecision(13_000 * POUND, 0, False)
    assert sub_limit_applies(2028, 64)


def test_REQ_ALW_005_overall_limit_rejects_the_excess():
    assert overall_acceptance(0, 5_000 * POUND) == (5_000 * POUND, 0)
    assert overall_acceptance(15_000 * POUND, 8_000 * POUND) == (5_000 * POUND, 3_000 * POUND)
    assert overall_acceptance(20_000 * POUND, 1 * POUND) == (0, 1 * POUND)
    assert overall_acceptance(25_000 * POUND, 1 * POUND) == (0, 1 * POUND)
