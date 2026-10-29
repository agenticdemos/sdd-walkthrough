from datetime import date

from ledger.taxyear import age_on, tax_year


def test_REQ_ALW_001_tax_year_starts_on_6_april():
    assert tax_year(date(2027, 4, 6)) == 2027
    assert tax_year(date(2027, 4, 5)) == 2026
    assert tax_year(date(2028, 4, 5)) == 2027
    assert tax_year(date(2027, 12, 31)) == 2027
    assert tax_year(date(2028, 1, 1)) == 2027


def test_REQ_ALW_004_age_is_taken_on_the_date_received():
    assert age_on(date(1962, 5, 1), date(2027, 4, 30)) == 64
    assert age_on(date(1962, 5, 1), date(2027, 5, 1)) == 65
