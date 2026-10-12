"""Plain-English 'why does this cost money and how do I stop it' notes for the usual bill-shock suspects.
Written to be safe and conservative: the agent can only READ costs, it gives steps, the human acts."""

PLAYBOOKS = {
    "nat gateway": {
        "why": "A NAT Gateway bills for every hour it exists AND for every GB of data pushed through it. "
               "The 'VPC and more' wizard can create one without you noticing.",
        "check": "VPC console > NAT gateways. Look for any in 'Available' state you do not recognise.",
        "stop": "If nothing needs it, delete the NAT gateway, then release its Elastic IP.",
    },
    "public ipv4": {
        "why": "AWS charges for every public IPv4 address per hour, whether or not it is attached to anything.",
        "check": "EC2 console > Elastic IPs, and the 'Public IPv4 address' column on your instances.",
        "stop": "Release unused Elastic IPs. Prefer private subnets / IPv6 where you can.",
    },
    "virtual private cloud": {
        "why": "In Cost Explorer, 'Amazon Virtual Private Cloud' often hides public IPv4 address charges and VPN/endpoint costs.",
        "check": "EC2 > Elastic IPs, and VPC > Endpoints for any interface endpoints left running.",
        "stop": "Release unused Elastic IPs and delete interface endpoints you no longer use.",
    },
    "ec2 - other": {
        "why": "'EC2 - Other' is a catch-all: NAT Gateways, EBS volumes, snapshots and data transfer all land here.",
        "check": "Billing > Cost Explorer, group by 'Usage type' to see which one it is (e.g. NatGateway-Bytes, EBS:VolumeUsage).",
        "stop": "Delete unattached EBS volumes and old snapshots; delete idle NAT gateways.",
    },
    "elastic compute cloud": {
        "why": "Running instances bill per hour. Stopped instances stop compute charges but their EBS disks still bill.",
        "check": "EC2 console > Instances, check every Region you have used (the Region selector top-right).",
        "stop": "Terminate instances you do not need. Stop (not terminate) only if you will use them again soon.",
    },
    "relational database": {
        "why": "A database instance bills hourly even when nobody queries it. A stopped RDS instance restarts by itself after 7 days.",
        "check": "RDS console > Databases, in every Region.",
        "stop": "Take a final snapshot if needed, then delete databases you do not use.",
    },
    "simple storage": {
        "why": "S3 bills for storage, requests and data going out to the internet.",
        "check": "S3 console > Storage Lens or Metrics, and look for large buckets or buckets with versioning on.",
        "stop": "Add a lifecycle rule to expire old versions and delete test data.",
    },
    "cloudwatch": {
        "why": "Log ingestion and storage add up fast, especially log groups whose retention is 'Never expire'.",
        "check": "CloudWatch > Log groups, sort by stored bytes; look at the Retention column.",
        "stop": "Set a retention period (for example 7 or 30 days) on noisy log groups.",
    },
    "bedrock": {
        "why": "Bedrock bills per token processed. Loops, long prompts or a forgotten script can burn through tokens quickly.",
        "check": "CloudWatch > Bedrock metrics (InputTokenCount / OutputTokenCount) and check any scripts or agents still running.",
        "stop": "Stop looping jobs, shorten prompts, and consider a cheaper model for simple tasks.",
    },
}

GENERIC = {
    "why": "I do not have a ready-made note for this service.",
    "check": "Billing > Cost Explorer, filter to this service and group by 'Usage type' to see exactly what is billing.",
    "stop": "Once you know the usage type, search the service's pricing page and delete the resource behind it.",
}

FREE_TIER_NOTE = ("Free Tier rules depend on when your account was created. "
                  "Check Billing console > Free Tier to see what you have left.")


def lookup(service: str) -> dict:
    s = service.lower()
    for key, pb in PLAYBOOKS.items():
        if key in s:
            return {**pb, "matched": key, "free_tier": FREE_TIER_NOTE}
    return {**GENERIC, "matched": None, "free_tier": FREE_TIER_NOTE}
