"""Generates data/demo_costs.json: 30 days of fake-but-realistic AWS costs for Demo Mode.
Story: a beginner's account where a NAT Gateway, public IPv4 addresses and a Bedrock experiment cause bill shock."""
import json, datetime as dt

END = dt.date(2026, 10, 10)
DAYS = 30
SERVICES = {
    "Amazon Elastic Compute Cloud - Compute": lambda i: 1.20,
    "EC2 - Other": lambda i: 0.60 if i < 23 else 3.40,          # NAT Gateway data processing starts at day 23
    "Amazon Virtual Private Cloud": lambda i: 0.40 if i < 20 else 0.90,  # more public IPv4 addresses
    "Amazon Relational Database Service": lambda i: 1.10,
    "Amazon Simple Storage Service": lambda i: 0.05 + 0.002 * i,
    "AmazonCloudWatch": lambda i: 0.10 + 0.004 * i,
    "Amazon Bedrock": lambda i: 0.0 if i < 26 else 0.80,
}
rows = []
for i in range(DAYS):
    d = END - dt.timedelta(days=DAYS - 1 - i)
    for svc, f in SERVICES.items():
        wiggle = ((i * 7) % 5 - 2) / 100  # deterministic tiny variation
        amt = max(0.0, round(f(i) + (wiggle if f(i) > 0 else 0), 4))
        rows.append({"date": d.isoformat(), "service": svc, "amount": amt})
json.dump({"currency": "USD", "rows": rows}, open("data/demo_costs.json", "w"), indent=1)
print(len(rows), "rows")
