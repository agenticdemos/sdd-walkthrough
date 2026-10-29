from datetime import date

from ledger.taxyear import tax_year


def test_REQ_ALW_001_tax_year_starts_on_6_april():
    assert tax_year(date(2027, 4, 6)) == 2027
    assert tax_year(date(2027, 4, 5)) == 2026
    assert tax_year(date(2028, 4, 5)) == 2027
    assert tax_year(date(2027, 12, 31)) == 2027
    assert tax_year(date(2028, 1, 1)) == 2027
