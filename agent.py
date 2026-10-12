"""Penny: a friendly bill-shock buddy for people new to AWS. Built with the Strands Agents SDK + Amazon Bedrock.
READ-ONLY by design: Penny can look at costs and explain them, but cannot change anything in your account."""
import os
import re
from collections import defaultdict

from strands import Agent, tool
from strands.models import BedrockModel

import costs
import playbooks

STATE = {"mode": "demo"}  # "demo" (sample data) or "live" (your account via Cost Explorer)

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")
REGION = os.getenv("AWS_REGION", "us-east-1")

SYSTEM_PROMPT = """You are Penny, a warm, calm bill-shock buddy for people who are new to AWS (students, solo developers, tiny startups).
Your job: explain AWS costs in plain English and tell the person what to do next. Never make them feel silly.

Rules:
- ALWAYS call your tools before stating any number. For 'what should I switch off', also call find_forgotten_resources and name the exact resource IDs it returns. Never invent costs, services or dates.
- Reply in the same language the person writes in, unless they ask otherwise.
- Use simple words. Explain jargon in a few words the first time you use it. Amounts are in USD.
- You are READ-ONLY. You cannot change anything. Give steps for the person to do themselves, and warn before anything that deletes data.
- Cost data can lag by up to a day. Say so if it matters.
- Only discuss AWS costs and billing. If asked about anything else, kindly say it is outside what you do and offer a billing check instead.
- If a tool fails, say what went wrong in one friendly sentence and what the person can try.

Answer format (keep it under about 180 words):
**What I see:** 1-2 sentences with the key numbers.
**Why it probably happened:** 1-2 sentences, plain English.
**Do this now:** at most 3 numbered steps.
If the verdict is YELLOW or RED, make one of your steps: set a safety-net alert in Billing console > Budgets (a 'Zero spend' or monthly cost budget), so future surprises reach their email early.
End with exactly one last line: VERDICT: GREEN (all normal), VERDICT: YELLOW (worth a look), or VERDICT: RED (act today).
"""


@tool
def get_cost_summary(days: int = 30) -> dict:
    """Get total spend and the top services by cost for the last N days.

    Args:
        days: How many days back to look (1-90). Default 30.
    """
    days = max(1, min(int(days), 90))
    rows = costs.get_rows(STATE["mode"], days)
    by_service = costs.totals_by_service(rows)
    total = sum(by_service.values())
    top = sorted(by_service.items(), key=lambda kv: kv[1], reverse=True)[:8]
    return {
        "period_days": days,
        "total_usd": round(total, 2),
        "top_services": [
            {"service": s, "usd": round(v, 2), "share_pct": round(100 * v / total, 1) if total else 0}
            for s, v in top
        ],
        "source": "sample data" if STATE["mode"] == "demo" else "AWS Cost Explorer",
    }


@tool
def find_cost_spikes() -> dict:
    """Compare the last 7 days with the 7 days before, and flag services whose cost jumped. Use this to answer 'why did my bill go up?'."""
    rows = costs.get_rows(STATE["mode"], 14)
    dates = sorted({r["date"] for r in rows})
    if len(dates) < 8:
        return {"error": "Not enough history yet to compare weeks (need at least 8 days of cost data)."}
    recent_dates = set(dates[-7:])
    prior_dates = set(dates[-14:-7])
    recent, prior = defaultdict(float), defaultdict(float)
    for r in rows:
        if r["date"] in recent_dates:
            recent[r["service"]] += r["amount"]
        elif r["date"] in prior_dates:
            prior[r["service"]] += r["amount"]
    changes = []
    for s in set(recent) | set(prior):
        r_, p_ = recent[s], prior[s]
        diff = r_ - p_
        pct = (diff / p_ * 100) if p_ > 0 else None
        flagged = diff >= 1.0 and (p_ == 0 or r_ >= 1.5 * p_)
        changes.append({
            "service": s, "prior_7d_usd": round(p_, 2), "recent_7d_usd": round(r_, 2),
            "change_usd": round(diff, 2), "change_pct": None if pct is None else round(pct),
            "flagged": flagged,
        })
    changes.sort(key=lambda c: c["change_usd"], reverse=True)
    return {"spikes": [c for c in changes if c["flagged"]], "all_changes": changes[:6]}


@tool
def explain_service_cost(service: str) -> dict:
    """Get a plain-English explanation of why a service costs money, how to check for it, and how to stop it.

    Args:
        service: The service name as it appears in the cost data, e.g. 'EC2 - Other' or 'Amazon Virtual Private Cloud'.
    """
    return playbooks.lookup(service)


def _scan_live(region: str) -> list:
    """Read-only look for resources that bill while doing nothing. Only Describe* calls."""
    import boto3
    ec2 = boto3.client("ec2", region_name=region)
    found = []
    for a in ec2.describe_addresses().get("Addresses", []):
        if not a.get("AssociationId"):
            found.append({"type": "Elastic IP (not attached)", "id": a.get("AllocationId", a.get("PublicIp")),
                          "detail": "Not associated with any instance or network interface",
                          "where": "EC2 console > Elastic IPs"})
    for n in ec2.describe_nat_gateways(Filter=[{"Name": "state", "Values": ["available"]}]).get("NatGateways", []):
        found.append({"type": "NAT Gateway", "id": n["NatGatewayId"],
                      "detail": "State: available (bills every hour it exists plus per GB processed)",
                      "where": "VPC console > NAT gateways"})
    for v in ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}]).get("Volumes", []):
        found.append({"type": "EBS volume (not attached)", "id": v["VolumeId"],
                      "detail": f"{v['Size']} GiB, not attached to any instance",
                      "where": "EC2 console > Volumes"})
    return found


@tool
def find_forgotten_resources() -> dict:
    """Look (read-only) for resources that quietly cost money while doing nothing: NAT gateways, unattached Elastic IPs and unattached EBS volumes. Use after finding a cost spike, or when asked what to switch off."""
    if STATE["mode"] == "demo":
        import json
        from pathlib import Path
        d = json.loads((Path(__file__).parent / "data" / "demo_resources.json").read_text())
        return {"region": d["region"], "found": d["resources"], "note": "Sample data. Only one Region is scanned."}
    found = _scan_live(REGION)
    return {"region": REGION, "found": found,
            "note": "Only this one Region was scanned; check other Regions you have used in the console."}


def build_agent() -> Agent:
    """Bedrock by default. Set PENNY_PROVIDER=gemini (and GEMINI_API_KEY) to use Google Gemini through Strands instead."""
    provider = os.getenv("PENNY_PROVIDER", "bedrock").lower()
    if provider == "gemini":
        from strands.models.gemini import GeminiModel
        api_key = os.getenv("GEMINI_API_KEY", "").strip().strip("<>\"' ")
        model = GeminiModel(
            client_args={"api_key": api_key},
            model_id=os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash"),
            params={"temperature": 0.3},
        )
    else:
        model = BedrockModel(model_id=MODEL_ID, region_name=REGION, temperature=0.3)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[get_cost_summary, find_cost_spikes, find_forgotten_resources, explain_service_cost],
        callback_handler=None,
    )


_VERDICT = re.compile(r"VERDICT:\s*(GREEN|YELLOW|RED)", re.I)


def split_verdict(text: str):
    """Return (answer_without_verdict_line, 'GREEN'|'YELLOW'|'RED'|None)."""
    m = _VERDICT.search(text)
    verdict = m.group(1).upper() if m else None
    cleaned = _VERDICT.sub("", text).strip()
    cleaned = re.sub(r"\n\s*\([^()\n]{1,40}\)\s*$", "", cleaned).strip()
    return cleaned, verdict


def friendly_error(exc: Exception) -> str:
    """Turn scary boto/Bedrock errors into one kind sentence plus a next step."""
    name, msg = type(exc).__name__, str(exc)
    low = msg.lower()
    if "NoCredentials" in name or "credentials" in low:
        return ("I can't find AWS credentials on this computer. Run `aws configure` (or `aws sso login`). "
                "Note: even in **Demo mode** (sample bill data), AWS credentials are required for Amazon Bedrock to generate answers.")
    if "AccessDenied" in msg or "not authorized" in low:
        if "ce:" in low or "cost" in low:
            return ("Your AWS user isn't allowed to read costs yet. Ask for `ce:GetCostAndUsage` permission "
                    "(it's read-only), or use **Demo mode** in the meantime.")
        return ("Bedrock said no. Open the Bedrock console, make sure model access is enabled for the model in "
                "`BEDROCK_MODEL_ID`, and that your user can call `bedrock:InvokeModel`.")
    if "DataUnavailable" in msg or "not enabled" in low:
        return ("Cost Explorer isn't switched on for this account yet. Enable it in the Billing console; "
                "data appears in about 24 hours. **Demo mode** works right now.")
    if "api key" in low or "api_key" in low or "PERMISSION_DENIED" in msg:
        return "The AI provider rejected the API key. Check GEMINI_API_KEY is set correctly in this terminal window."
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in low:
        return "The AI provider's free limit was reached for now. Wait a minute and try again."
    if "Throttl" in name or "throttl" in low:
        return "AWS asked me to slow down for a moment. Please try again in a few seconds."
    return f"Something unexpected happened ({name}). Try again, or switch to Demo mode. Details: {msg[:160]}"


# "Auto" = reply in whatever language the person writes in. Others force a language.
LANGUAGES = {"Auto (match my language)": None, "English": "English", "Español": "Spanish", "Français": "French",
             "Deutsch": "German", "Português": "Portuguese", "日本語": "Japanese", "中文": "Chinese", "हिन्दी": "Hindi"}


def ask(agent: Agent, prompt: str, language: str | None = None):
    """Run one question. Returns (answer_text, verdict). Reply language is chosen by the person."""
    if language:
        prompt = (f"{prompt}\n\n(Reply entirely in {language}, in simple everyday words. "
                  f"Keep service names, resource IDs and the final 'VERDICT: ...' line in English.)")
    result = agent(prompt)
    return split_verdict(str(result))


def make_report(messages: list, mode: str) -> str:
    """Markdown 'bill check-up' the person can save or share. Built only from the conversation, nothing invented."""
    import datetime as dt
    icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}
    lines = [f"# Penny bill check-up", f"_Generated {dt.date.today().isoformat()} from "
             f"{'sample data' if mode == 'demo' else 'AWS Cost Explorer'}. Read-only: nothing in the account was changed._", ""]
    for i, m in enumerate(messages):
        if m["role"] == "user":
            lines.append(f"## Q: {m['content']}")
        elif not m.get("error"):
            if m.get("verdict"):
                lines.append(f"**{icon[m['verdict']]} {m['verdict']}**")
            lines += [m["content"], ""]
    return "\n".join(lines)
