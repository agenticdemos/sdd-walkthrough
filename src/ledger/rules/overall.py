"""Overall annual limit (illustrative: £20,000)."""

OVERALL_LIMIT_PENCE = 2_000_000  # REQ-ALW-005


def overall_acceptance(prior_total: int, amount: int) -> tuple[int, int]:
    """Split amount into (accepted, rejected) so the year's total never exceeds the limit."""
    room = max(OVERALL_LIMIT_PENCE - prior_total, 0)  # REQ-ALW-005
    accepted = min(amount, room)
    return accepted, amount - accepted
