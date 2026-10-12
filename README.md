# 🪙 Penny: A Friendly AWS Bill Buddy for Beginners

Penny is a read-only AI bill-shock buddy that explains surprise AWS bills in plain English and tells you what actions to take next—no jargon, no panic.

Built with the **Strands Agents SDK**, supporting **Amazon Bedrock** and **Google Gemini**, with a clean **Streamlit** chat UI and cost tracking using **AWS Cost Explorer** (read-only).

---

## What Penny Does
- **Plain-English Explanations:** Breaks down which AWS services caused a bill spike and why.
- **Traffic Light Verdicts:** Issues quick, actionable verdicts (🟢 Normal, 🟡 Worth a look, 🔴 Act today).
- **Forgotten Resource Detection:** Scans for idle NAT gateways, unattached Elastic IPs, and detached EBS volumes.
- **Service Playbooks:** Provides actionable "why / check / stop" checklists.
- **Multi-language Support:** Automatically replies in your language or lets you choose from 8 languages.
- **Report Export:** Exports a shareable Markdown bill check-up report with one click.

---

## Quickstart

### 1. Prerequisites & Environment Setup
Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/parekhjaymin00-prog/Penny-aws.git
cd Penny-aws
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configure AI Provider

Penny supports two AI providers:

#### Option A: Amazon Bedrock (Default)
Requires AWS credentials configured with Bedrock model invocation access:
```bash
aws configure
```
Make sure you have model access enabled in your AWS Bedrock console for Amazon Nova (default: `us.amazon.nova-lite-v1:0`).

#### Option B: Google Gemini
Set `PENNY_PROVIDER=gemini` and export your `GEMINI_API_KEY` directly in your terminal session (**never save keys to files or commit them**):

On Linux/macOS:
```bash
export PENNY_PROVIDER="gemini"
export GEMINI_API_KEY="your-gemini-api-key"
```

On Windows (PowerShell):
```powershell
$env:PENNY_PROVIDER="gemini"
$env:GEMINI_API_KEY="your-gemini-api-key"
```

> **Security Rule: Never Commit Keys**
> Never hardcode or save API keys, credentials, or `.env` files into this repository. Always pass API keys via temporary environment variables in your terminal session.

### 3. Run Penny
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Modes

### Demo Mode (Default)
Penny starts in **Demo mode** using local sample data (`data/sample_costs.json` and `data/demo_resources.json`). No live AWS billing permissions are required to explore the tool or test the AI explanations.

### Live Mode
Flip the **"Use my real AWS account"** toggle in the sidebar. This reads costs directly via AWS Cost Explorer (`ce:GetCostAndUsage`) and inspects unattached resources in EC2.

#### Minimal Read-Only IAM Policy
Penny is strictly read-only and cannot alter or delete any resources. Here is the minimal IAM policy required for live mode:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CostExplorerReadOnly",
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2ResourceScanReadOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeAddresses",
        "ec2:DescribeNatGateways",
        "ec2:DescribeVolumes"
      ],
      "Resource": "*"
    },
    {
      "Sid": "BedrockInvokeReadOnly",
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

---

## Honest Limitations
- **Bedrock Account Access:** Bedrock model access was blocked on the developer's personal AWS account during testing; live agent evaluations were verified using the Google Gemini provider (`gemini-2.5-flash`).
- **Live Cost Explorer:** Live Cost Explorer queries incur ~$0.01 per request and require an active billing history, so development and automated evaluations relied on simulated realistic test billing datasets.
- **Single Region Scanning:** Resource scans (NAT gateways, Elastic IPs, EBS volumes) currently inspect one Region at a time (default `us-east-1`). Resources in other AWS Regions must be checked separately or configured via `AWS_REGION`.

---

## Running Tests
Run the test suite without making live model calls:
```bash
pytest -q tests
```

---

## License
MIT License - Copyright (c) 2026 Jaymin Parekh. See [LICENSE](LICENSE) for details.
