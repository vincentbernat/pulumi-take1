import json
import pulumi
import pulumi_aws as aws

kms_key = aws.kms.Key(
    "kms-key",
    customer_master_key_spec="ECC_NIST_P256",
    enable_key_rotation=False,
    is_enabled=True,
    key_usage="SIGN_VERIFY",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Id": "dnssec-policy",
            "Statement": [
                {
                    "Sid": "Enable IAM User Permissions",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": f"arn:aws:iam::{aws.get_caller_identity().account_id}:root"
                    },
                    "Action": "kms:*",
                    "Resource": "*",
                },
                {
                    "Sid": "Allow Route 53 DNSSEC Service",
                    "Effect": "Allow",
                    "Principal": {"Service": "dnssec-route53.amazonaws.com"},
                    "Action": ["kms:DescribeKey", "kms:GetPublicKey", "kms:Sign"],
                    "Resource": "*",
                },
                {
                    "Sid": "Allow Route 53 DNSSEC to CreateGrant",
                    "Effect": "Allow",
                    "Principal": {"Service": "dnssec-route53.amazonaws.com"},
                    "Action": "kms:CreateGrant",
                    "Resource": "*",
                    "Condition": {"Bool": {"kms:GrantIsForAWSResource": "true"}},
                },
            ],
        }
    ),
    opts=pulumi.ResourceOptions(protect=True),
)

# For DNS, reuse the master key (they are expensive!)
dns_cmk = aws.kms.Alias(
    "dns-cmk",
    name="alias/dns-cmk",
    target_key_id=kms_key.key_id,
    opts=pulumi.ResourceOptions(protect=True),
)
