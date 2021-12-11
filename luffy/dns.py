import pulumi
import pulumi_aws as aws

aws.route53.Zone(
    "y.luffy.cx",
    comment="DDNS for luffy.cx hosts",
    name="y.luffy.cx",
    opts=pulumi.ResourceOptions(protect=True),
)
