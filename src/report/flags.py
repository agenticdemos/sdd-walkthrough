"""Per-subscription flags for the breach report. All dates illustrative."""
from datetime import date

from ledger.taxyear import tax_year


def sub_limit_applies(d: date) -> bool:
    """True when the cash sub-limit applies to a subscription received on d.

    Tax years are named by the year they start in, so 2027 is 6 April 2027 to 5 April 2028,
    the first tax year with a cash sub-limit."""
    # REQ-ALW-003: no sub-limit in tax years starting before 6 April 2027
    return tax_year(d) >= 2027
