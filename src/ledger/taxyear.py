"""UK tax year arithmetic. A tax year runs 6 April to 5 April and is named by the year it ENDS."""
from datetime import date


def tax_year(d: date) -> int:
    """End year of the tax year containing d: 6 Apr 2027 to 5 Apr 2028 is 2028."""
    # REQ-ALW-001
    return d.year + 1 if (d.month, d.day) >= (4, 6) else d.year


def age_on(dob: date, on: date) -> int:
    """Age in whole years on a given date (age is taken on the date received)."""
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))
