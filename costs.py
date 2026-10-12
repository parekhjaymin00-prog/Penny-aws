"""Cost data access. Demo Mode reads a local JSON file; Live Mode reads AWS Cost Explorer (read-only)."""
import json, datetime as dt
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

DEMO_FILE = Path(__file__).parent / "data" / "demo_costs.json"


@lru_cache(maxsize=8)
def _load(mode: str, days: int, today: str):
    """Return list of {date, service, amount}. Cached so we don't pay for repeated Cost Explorer calls."""
    if mode == "demo":
        rows = json.loads(DEMO_FILE.read_text())["rows"]
        last = max(r["date"] for r in rows)
        cutoff = (dt.date.fromisoformat(last) - dt.timedelta(days=days - 1)).isoformat()
        return [r for r in rows if r["date"] >= cutoff]

    import boto3  # imported lazily so Demo Mode works with no AWS setup
    ce = boto3.client("ce", region_name="us-east-1")  # Cost Explorer is served from us-east-1
    end = dt.date.fromisoformat(today) + dt.timedelta(days=1)  # End is exclusive
    start = end - dt.timedelta(days=days + 1)
    out, token = [], None
    while True:
        kw = dict(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        if token:
            kw["NextPageToken"] = token
        resp = ce.get_cost_and_usage(**kw)
        for day in resp["ResultsByTime"]:
            for g in day["Groups"]:
                out.append({
                    "date": day["TimePeriod"]["Start"],
                    "service": g["Keys"][0],
                    "amount": float(g["Metrics"]["UnblendedCost"]["Amount"]),
                })
        token = resp.get("NextPageToken")
        if not token:
            return out


def get_rows(mode: str, days: int):
    return _load(mode, int(days), dt.date.today().isoformat())


def totals_by_service(rows):
    t = defaultdict(float)
    for r in rows:
        t[r["service"]] += r["amount"]
    return dict(t)
