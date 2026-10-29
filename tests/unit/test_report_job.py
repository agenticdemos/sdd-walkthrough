"""Unit tests for report.job: REQ-RPT-001 (who is listed) and REQ-RPT-002 (no partial report)."""

from report.client import LedgerUnavailable
from report.job import THRESHOLD_PENCE, main, read_ids, run


class FakeLedger:
    def __init__(self, remaining: dict[str, int], fail_on: str | None = None):
        self.remaining, self.fail_on = remaining, fail_on

    def allowance(self, subscriber_id: str, tax_year: int) -> dict:
        if subscriber_id == self.fail_on:
            raise LedgerUnavailable("down")
        return {"subscriber_id": subscriber_id, "tax_year": tax_year,
                "remaining_allowance_pence": self.remaining[subscriber_id],
                "remaining_cash_sub_limit_pence": None}


def test_REQ_RPT_001_threshold_is_1000_pounds_in_pence():
    assert THRESHOLD_PENCE == 100_000


def test_REQ_RPT_001_lists_only_subscribers_below_threshold(tmp_path):
    ledger = FakeLedger({"LOW": 99_999, "EDGE": 100_000, "HIGH": 2_000_000, "ZERO": 0})
    out = tmp_path / "breaches.csv"
    assert run(ledger, ["LOW", "EDGE", "HIGH", "ZERO"], 2027, out) == 0
    assert out.read_text().splitlines() == [
        "subscriber_id,remaining_allowance_pence", "LOW,99999", "ZERO,0"]


def test_REQ_RPT_001_empty_report_still_written(tmp_path):
    out = tmp_path / "breaches.csv"
    assert run(FakeLedger({"HIGH": 500_000}), ["HIGH"], 2027, out) == 0
    assert out.read_text() == "subscriber_id,remaining_allowance_pence\n"


def test_REQ_RPT_002_ledger_down_midway_exits_non_zero_and_writes_nothing(tmp_path):
    ledger = FakeLedger({"A": 10, "B": 10}, fail_on="B")
    out = tmp_path / "breaches.csv"
    assert run(ledger, ["A", "B"], 2027, out) != 0
    assert list(tmp_path.iterdir()) == []  # no report, no stray temp file


def test_REQ_RPT_002_cli_with_unreachable_ledger_exits_non_zero(tmp_path):
    ids = tmp_path / "ids.txt"
    ids.write_text("S1\n")
    out = tmp_path / "breaches.csv"
    argv = ["--ledger", "http://127.0.0.1:9", "--subscribers", str(ids),
            "--tax-year", "2027", "--out", str(out)]
    assert main(argv) != 0
    assert not out.exists()


def test_read_ids_skips_blanks_and_comments(tmp_path):
    f = tmp_path / "ids.txt"
    f.write_text("# daily list\nS1\n\n  S2  \n")
    assert read_ids(f) == ["S1", "S2"]
