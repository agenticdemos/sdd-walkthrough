"""Breach report sub-limit flag. Dates are illustrative."""
from datetime import date

from report.flags import sub_limit_applies


def test_REQ_ALW_003_date_in_2026_27_is_not_flagged():
    assert not sub_limit_applies(date(2026, 12, 1))
    assert not sub_limit_applies(date(2027, 4, 5))


def test_REQ_ALW_003_date_in_2027_28_is_flagged():
    assert sub_limit_applies(date(2027, 4, 6))
    assert sub_limit_applies(date(2027, 5, 1))
