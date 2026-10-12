# Penny: An AWS Bill Buddy That Explains Surprise Charges in Plain English

Tag: #agents

## What it does and who it's for

Every developer remembers their first AWS bill shock. You launch an EC2 instance to learn cloud infrastructure, experiment with a small database, or wire together an exploratory container architecture over the weekend. A few weeks later, an unexpected billing notification arrives in your inbox: charges for an unattached Elastic IP, an idle NAT Gateway left running after a tutorial, or unexpected charges under a cryptic line item titled "EC2 - Other". For students, solo hackers, and early-stage startup founders anywhere in the world, this experience is not just confusing—it is intimidating. AWS Cost Explorer is powerful, but navigating multidimensional dimension-grouping tables and service charge hierarchies feels like reading tax law when you are just getting started.

[FILL IN: 2-3 sentences of my own story]

Penny is an AI bill-buddy designed to turn bill panic into calm, actionable clarity. Penny inspects your AWS spend, identifies sudden week-over-week cost spikes, spots abandoned cloud resources quietly racking up hourly fees, and translates opaque AWS billing line items into clear, empathetic guidance. Most importantly, Penny tells you exactly what to do next in plain English, with numbered steps, without jargon, and without touching or modifying any resource in your cloud account.

## How I built it

Penny is constructed using a focused, modern AWS AI architecture designed strictly around minimal, read-only security and rapid prototyping:

- **Amazon Bedrock (`us.amazon.nova-lite-v1:0`)**: Bedrock acts as the reasoning engine for the agent. Using the lightweight, responsive Nova Lite foundation model, Penny processes tool outputs, determines whether spending is abnormal, produces structured summaries, and provides empathetic explanations.
- **Strands Agents SDK (`strands`)**: The agent loop is orchestrated via the Strands Agents SDK. Strands provides simple Python `@tool` decorators that expose typed, structured functions directly to Bedrock's tool-use API, handling multi-turn tool calling and context maintenance cleanly.
- **AWS Cost Explorer (`ce:GetCostAndUsage`)**: Provides daily historical cost breakdowns grouped by service over a window I choose (up to 90 days, default 30), plus a 7-day vs previous-7-day comparison. Cost Explorer data is fetched on demand and cached in memory while the app runs to minimize API query charges ($0.01 per request).
- **Amazon EC2 Describe APIs (`DescribeAddresses`, `DescribeNatGateways`, `DescribeVolumes`)**: Read-only boto3 calls inspect running infrastructure to detect forgotten or unattached resources that accrue hourly charges even when no compute workloads are running.
- **Streamlit**: A clean web interface featuring interactive starter questions, a clear verdict badge, feedback capture, and one-click markdown report exports.

Cost Explorer and the EC2 scan were exercised with sample data and stubbed clients; [FILL IN: whether I also tested Live mode against a real account].

### Tools I used

Antigravity and Claude were used as AI coding assistants, and I wrote [FILL IN: what I decided/tested/changed].

### Security and Read-Only Architecture

Security was my primary architectural constraint. Beginners are rightfully terrified of granting automated tools write access to their cloud infrastructure. Penny is engineered from the ground up to be strictly **READ-ONLY**:

1. Penny has zero capability to alter, terminate, create, or delete any AWS resource. All remediation instructions are delivered as step-by-step guidance for the user to execute themselves inside the AWS Management Console.
2. The agent's minimal IAM policy grants only four read-only account actions plus Bedrock invoke permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ec2:DescribeAddresses",
        "ec2:DescribeNatGateways",
        "ec2:DescribeVolumes"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```
Cost Explorer and EC2 Describe actions cannot be scoped to individual resources, and I left Bedrock access unscoped for simplicity.
3. To protect account privacy and reduce prompt token overhead, all raw AWS API responses are filtered before reaching the LLM. Only a few fields are passed (resource type, ID, short description, volume size, and aggregated dollar totals). Account numbers, IAM usernames, ARN metadata, and sensitive tags are completely excluded.

### Core Tool Implementation

Here is how Penny's forgotten resource scanner inspects idle infrastructure safely and concisely using the exact implementation from `agent.py`:

```python
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
```

## The Delightful Detail: The Three-Tier Verdict Badge and Demo Mode

When someone is panicked about a cloud bill, their cognitive load is already spiked. Giving them a wall of text or a dry table of raw percentages does not help. 

Penny's delightful detail is the clear **🟢🟡🔴 Verdict Badge**, for example:
- **🟢 All looks normal**: For example, spend is steady with no unusual spikes detected.
- **🟡 Worth a look**: For example, an orphaned volume or unused Elastic IP detected; review within the week.
- **🔴 Act today**: For example, an unattached NAT Gateway running non-stop; immediate steps provided.

Beneath the badge, I instruct Penny to format each answer into three digestible sections [FILL IN: result of my live eval, e.g. N of 8 answers followed the format; what failed]:
1. **What I see:** One or two sentences with the key figures.
2. **Why it probably happened:** Plain-English explanation without acronyms.
3. **Do this now:** At most 3 numbered steps. For yellow and red answers, a step is included to set a safety-net budget alert in AWS Budgets (a 'Zero spend' or monthly cost budget) as a permanent guardrail.

In addition, Penny offers a low-risk **Demo mode** loaded with realistic sample spend data (including a planted week-over-week spike in EC2 - Other and Bedrock, alongside orphaned Elastic IPs and NAT gateways). This allows beginners and reviewers to experience the full conversational diagnostic workflow immediately without incurring Cost Explorer API charges or exposing their production accounts. Note that Demo mode still needs AWS credentials and Bedrock access for the model itself, as the AI reasoning runs live even though billing data is loaded from local samples (model tokens are still billed by Bedrock).

**How I know it worked:**
[FILL IN: N testers tried Penny. Results: X thumbs up, Y thumbs down in the Streamlit UI feedback counter. Real user quote: "Quote from tester about how Penny explained their bill or reduced their anxiety."]

## Proof It Works

Penny was validated through automated offline tests and UI state checks:
- Automated test suite (`tests/test_penny.py`) verifying cost calculations, week-over-week spike detection algorithms, playbook resolution, that the live scan only calls describe_* methods using a fake client, multi-language instructions, and friendly error handlers.
- Streamlit browser session verification capturing clean initial state, starter prompt chips, starter prompt click leading to the friendly credential error, and polite credential error handling without displaying raw Python tracebacks.

[FILL IN: screenshot of a real answer with verdict badge]
[FILL IN: upload screenshots into the article; check them for personal paths first]

## What Went Wrong and What's Next

Building an agent around cloud billing taught me several practical lessons:

1. **Billing Data Latency**: AWS Cost Explorer data updates at least once per day. When users deploy something expensive that morning, Cost Explorer will not reflect it until the following day. I added a note to the system prompt to be explicit about this latency window so users do not assume today's tests were free.
2. **Multi-Region Reality**: The prototype scans one AWS Region (`us-east-1` by default). Cloud beginners frequently launch resources across multiple regions accidentally (for example, leaving an instance in `eu-west-1` after following an online tutorial). Expanding the resource scanner to query all active AWS regions concurrently while maintaining low latency is my next major roadmap milestone.
3. **Budget Guard Automation**: While Penny provides step-by-step instructions on setting up AWS Budgets alerts, users would benefit from an optional, one-click button that creates an initial $10 budget notification with explicit user confirmation.

Built on October 11, 2026.
