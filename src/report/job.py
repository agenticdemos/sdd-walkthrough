"""Daily breach report: lists subscribers whose remaining overall allowance is below the threshold.

Contract v1 has no list endpoint, so subscriber ids come from a text file, one per line.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

from report.client import LedgerClient, LedgerUnavailable

THRESHOLD_PENCE = 100_000  # £1,000, illustrative  # REQ-RPT-001


def run(client, subscriber_ids: list[str], tax_year: int, out_path: Path) -> int:
    out_path = Path(out_path)
    rows = []
    try:
        for sid in subscriber_ids:
            print(f"report: asking ledger for {sid} ({tax_year})")
            remaining = client.allowance(sid, tax_year)["remaining_allowance_pence"]
            if remaining < THRESHOLD_PENCE:  # REQ-RPT-001
                rows.append(f"{sid},{remaining}")
    except LedgerUnavailable as exc:  # REQ-RPT-002: no file, non-zero exit
        print(f"report: ledger unavailable, writing nothing: {exc}", file=sys.stderr)
        return 2
    body = "subscriber_id,remaining_allowance_pence\n" + "".join(r + "\n" for r in rows)
    fd, tmp = tempfile.mkstemp(dir=out_path.parent, prefix=f".{out_path.name}.")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(body)
        os.replace(tmp, out_path)  # atomic: readers never see a partial report
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    print(f"report: {len(rows)} of {len(subscriber_ids)} below {THRESHOLD_PENCE}p -> {out_path}")
    return 0


def read_ids(path: Path) -> list[str]:
    lines = (line.strip() for line in Path(path).read_text().splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m report.job", description=__doc__)
    p.add_argument("--ledger", required=True, help="ledger API base URL")
    p.add_argument("--subscribers", required=True, type=Path, help="file of subscriber ids")
    p.add_argument("--tax-year", required=True, type=int, help="start year, e.g. 2027")
    p.add_argument("--out", required=True, type=Path, help="report CSV path")
    args = p.parse_args(argv)
    ids = read_ids(args.subscribers)
    print(f"report: {len(ids)} subscribers, ledger {args.ledger}, tax year {args.tax_year}")
    return run(LedgerClient(args.ledger), ids, args.tax_year, args.out)


if __name__ == "__main__":
    sys.exit(main())
