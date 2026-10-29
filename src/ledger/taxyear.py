"""UK tax year arithmetic. A tax year runs 6 April to 5 April and is named by its START year."""
from datetime import date


def tax_year(d: date) -> int:
    """Start year of the tax year containing d: 6 Apr 2027 to 5 Apr 2028 is 2027."""
    # REQ-ALW-001
    return d.year if (d.month, d.day) >= (4, 6) else d.year - 1


def age_on(dob: date, on: date) -> int:
    """Age in whole years on a given date (age is taken on the date received)."""
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))
