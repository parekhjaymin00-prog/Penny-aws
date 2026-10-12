import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import agent as penny
from streamlit.testing.v1 import AppTest

penny.STATE["mode"] = "demo"
# strands @tool objects keep the plain function in .original_function? call via the decorated object directly:
def call(t, **kw):
    f = getattr(t, "_tool_func", None) or t
    return f(**kw)

def test_summary_totals_and_top_service():
    r = call(penny.get_cost_summary, days=30)
    assert r["total_usd"] > 0 and r["top_services"][0]["usd"] >= r["top_services"][-1]["usd"]
    assert r["source"] == "sample data"

def test_spikes_find_the_planted_story():
    r = call(penny.find_cost_spikes)
    flagged = {s["service"] for s in r["spikes"]}
    assert "EC2 - Other" in flagged and "Amazon Bedrock" in flagged
    assert "Amazon Relational Database Service" not in flagged  # steady service must not be flagged

def test_playbook_match_and_fallback():
    assert call(penny.explain_service_cost, service="EC2 - Other")["matched"] == "ec2 - other"
    assert call(penny.explain_service_cost, service="Some New Service")["matched"] is None

def test_verdict_parsing():
    txt, v = penny.split_verdict("All fine.\n\nVERDICT: yellow")
    assert v == "YELLOW" and "VERDICT" not in txt
    assert penny.split_verdict("no verdict here")[1] is None
    sample = (
        "Here are the steps:\n"
        "1. Open EC2 (see console) to check volumes.\n\n"
        "VERDICT: YELLOW\n"
        "(worth a look)"
    )
    cleaned, verdict = penny.split_verdict(sample)
    assert verdict == "YELLOW"
    assert "(see console)" in cleaned
    assert "(worth a look)" not in cleaned


def test_esc_dollars():
    from app import esc_dollars
    res = esc_dollars("$22.80 and $19.58")
    assert res == r"\$22.80 and \$19.58"

def test_friendly_errors():
    class NoCredentialsError(Exception): pass
    assert "Demo mode" in penny.friendly_error(NoCredentialsError("Unable to locate credentials"))
    assert "Throttl" not in penny.friendly_error(Exception("ThrottlingException: slow down"))

def test_app_loads_and_error_path_is_friendly(monkeypatch):
    monkeypatch.setattr(penny, "ask", lambda a, p, l="English": (_ for _ in ()).throw(Exception("Unable to locate credentials")))
    at = AppTest.from_file(str(pathlib.Path(__file__).parent.parent / "app.py"), default_timeout=30).run()
    assert not at.exception
    at.chat_input[0].set_value("hi").run()
    assert not at.exception
    assert any("credentials" in m.markdown[0].value for m in at.chat_message if m.markdown)

def test_forgotten_resources_demo_mode():
    penny.STATE["mode"] = "demo"
    r = call(penny.find_forgotten_resources)
    types = {f["type"] for f in r["found"]}
    assert {"NAT Gateway", "Elastic IP (not attached)", "EBS volume (not attached)"} <= types

def test_forgotten_resources_live_path_uses_only_describe_calls(monkeypatch):
    calls = []
    class FakeEC2:
        def describe_addresses(self): calls.append("describe_addresses"); return {"Addresses": [{"AllocationId": "eipalloc-1"}, {"AllocationId": "eipalloc-2", "AssociationId": "x"}]}
        def describe_nat_gateways(self, **k): calls.append("describe_nat_gateways"); return {"NatGateways": [{"NatGatewayId": "nat-1"}]}
        def describe_volumes(self, **k): calls.append("describe_volumes"); return {"Volumes": [{"VolumeId": "vol-1", "Size": 8}]}
    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **k: FakeEC2())
    penny.STATE["mode"] = "live"
    try:
        r = call(penny.find_forgotten_resources)
    finally:
        penny.STATE["mode"] = "demo"
    ids = {f["id"] for f in r["found"]}
    assert ids == {"eipalloc-1", "nat-1", "vol-1"}          # the attached EIP is not reported
    assert all(c.startswith("describe_") for c in calls)    # read-only

def test_language_instruction(monkeypatch):
    seen = {}
    class A:
        def __call__(self, p): seen["p"] = p; return "ok\nVERDICT: GREEN"
    penny.ask(A(), "hi", "French")
    assert "French" in seen["p"] and "VERDICT" in seen["p"]
    penny.ask(A(), "hi")            # Auto: no forced language
    assert seen["p"] == "hi"

def test_languages_are_global_not_one_country():
    assert len(penny.LANGUAGES) >= 8 and penny.LANGUAGES["Auto (match my language)"] is None

def test_report_export_has_no_invented_content():
    msgs = [{"role": "user", "content": "Why?"}, {"role": "assistant", "content": "Because NAT.", "verdict": "RED"},
            {"role": "assistant", "content": "oops", "error": True}]
    r = penny.make_report(msgs, "demo")
    assert "Because NAT." in r and "RED" in r and "oops" not in r and "sample data" in r
