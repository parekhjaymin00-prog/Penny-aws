# [Title: e.g. "Penny: an AWS bill buddy that explains surprise charges in plain English"]
Tag: #agents   (minimum 500 words; fill every [bracket] with REAL facts, delete this line)

## What it does and who it's for
[2-3 sentences. Audience: anyone new to AWS, anywhere in the world (students, solo developers, tiny startups) who gets a surprise bill.
Add one real story: what happened to you or someone you know.]

## How I built it
- **Amazon Bedrock** ([model you actually used]) for reasoning
- **Strands Agents SDK**: agent with 4 tools: cost summary, week-over-week spike finder, forgotten-resource scan, plain-English playbooks
- **AWS Cost Explorer** and **EC2 Describe APIs** (read-only) via boto3
- **Streamlit** for the chat UI
- [Anything else you really used, and nothing you didn't]
Explain the security design: Penny is read-only on purpose, and the IAM policy in the README grants only ce:GetCostAndUsage plus three EC2 Describe* actions (least privilege). Data from AWS APIs is limited to IDs and types before it reaches the model.
[Paste a short code snippet of one tool.]

## The delightful detail
[Pick ONE and describe it: the 🟢🟡🔴 verdict badge / replies in the language you type / Demo mode so the first run just works.]
**How I know it worked:** [N testers, X thumbs up, Y thumbs down, plus one real quote]. [Real numbers only.]

## Proof it works
[Screenshot(s) and/or short video link. Caption what's shown.]

## What went wrong and what's next
[1-2 honest lessons, e.g. a bug you hit, a limitation: one Region scanned, Cost Explorer data lags a day.]
Built on [date] in [N] hours.
