"""Rule tests. Figures are illustrative. The cash sub-limit's tests arrive with TASK-07."""
from ledger.rules.overall import overall_acceptance

POUND = 100


def test_REQ_ALW_005_overall_limit_rejects_the_excess():
    assert overall_acceptance(0, 5_000 * POUND) == (5_000 * POUND, 0)
    assert overall_acceptance(15_000 * POUND, 8_000 * POUND) == (5_000 * POUND, 3_000 * POUND)
    assert overall_acceptance(20_000 * POUND, 1 * POUND) == (0, 1 * POUND)
    assert overall_acceptance(25_000 * POUND, 1 * POUND) == (0, 1 * POUND)
