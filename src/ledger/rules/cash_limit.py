"""Cash sub-limit (illustrative: £12,000 from the 2027/28 tax year, labelled 2028, under-65s only)."""
from typing import NamedTuple

CASH_LIMIT_PENCE = 1_200_000  # REQ-ALW-004
SUB_LIMIT_FIRST_YEAR = 2028  # REQ-ALW-003: 2027/28, labelled by the year it ends
EXEMPT_AGE = 65  # REQ-ALW-004


class CashDecision(NamedTuple):
    accepted: int
    rejected: int
    capped: bool


def sub_limit_applies(tax_year: int, age: int) -> bool:
    # REQ-ALW-003: no sub-limit in tax years starting before 6 April 2027 (labelled 2027 or earlier)
    return tax_year >= SUB_LIMIT_FIRST_YEAR and age < EXEMPT_AGE


def cash_acceptance(prior_cash: int, amount: int, tax_year: int, age: int) -> CashDecision:
    """Accept cash up to the remaining sub-limit; reject the excess."""
    if not sub_limit_applies(tax_year, age):
        return CashDecision(amount, 0, False)
    total_cash = prior_cash + amount
    if total_cash > CASH_LIMIT_PENCE:  # REQ-ALW-004
        accepted = max(CASH_LIMIT_PENCE - prior_cash, 0)
        return CashDecision(accepted, amount - accepted, True)
    return CashDecision(amount, 0, False)
