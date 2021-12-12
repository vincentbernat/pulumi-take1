import re
import pulumi
import pulumi_aws as aws
from .kms import dns_cmk


def record(zone, name, rrtype, records, ttl=86400):
    if name == "@":
        name = zone._name
    else:
        name = f"{name}.{zone._name}"
    aws.route53.Record(
        f"{rrtype}-{name}",
        zone_id=zone.zone_id,
        name=f"{name}",
        type=rrtype,
        ttl=ttl,
        records=records if type(records) is list else [records],
    )


def www(zone, name):
    """Create records for web servers."""
    ttl = 60 * 60 * 2
    servers = {
        "web03": {"A": "95.216.162.158", "AAAA": "2a01:4f9:c010:1a9c::1"},
        "web04": {"A": "116.203.18.48", "AAAA": "2a01:4f8:1c0c:5eb5::1"},
        "web05": {"A": "5.161.44.145", "AAAA": "2a01:4ff:f0:b91::1"},
    }
    for rrtype in ("A", "AAAA"):
        record(
            zone,
            name,
            rrtype,
            [
                data[rrtype]
                for server, data in servers.items()
                if not data.get("disabled")
            ],
            ttl,
        )
    record(zone, name, "CAA", ['0 issue "buypass.com"', '0 issuewild ";"'])


def fastmail_mx(zone, subdomains=[]):
    """Create records for MX with FastMail."""
    subdomains += ["@", "*"]
    for subdomain in subdomains:
        record(
            zone,
            subdomain,
            "MX",
            ["10 in1-smtp.messagingengine.com.", "20 in2-smtp.messagingengine.com."],
        )
    record(
        zone,
        "@",
        "TXT",
        ["v=spf1 include:spf.messagingengine.com ~all"],
    )
    for dk in ("mesmtp", "fm1", "fm2", "fm3"):
        record(
            zone, f"{dk}._domainkey", "CNAME", f"{dk}.{zone._name}.dkim.fmhosted.com."
        )
    record(zone, "_submission._tcp", "SRV", "0 1 587 smtp.fastmail.com.")
    record(zone, "_imap._tcp", "SRV", "0 0 0 .")
    record(zone, "_imaps._tcp", "SRV", "0 1 993 imap.fastmail.com.")
    record(zone, "_dmarc", "TXT", "v=DMARC1; p=none; sp=none")


def sign(zone):
    """Sign a zone."""
    return aws.route53.KeySigningKey(
        zone._name,
        hosted_zone_id=zone.zone_id,
        key_management_service_arn=dns_cmk.target_key_arn,
        name=re.sub(r"[^0-9a-zA-Z]", "", zone._name),
        status="ACTIVE",
    )


# Luffy
y_luffy_cx = aws.route53.Zone("y.luffy.cx", name="y.luffy.cx")
# luffy_cx = aws.route53.Zone(
#     "luffy.cx",
#     name="luffy.cx",
#     opts=pulumi.ResourceOptions(protect=True),
# )
# aws.route53.Record(
#     "NS-y.luffy.cx",
#     zone_id=luffy_cx.zone_id,
#     name="y.luffy.cx",
#     type="NS",
#     ttl=86400,
#     records=y_luffy_cx.name_servers)

# ENXIO
enxio_fr = aws.route53.Zone("enxio.fr", name="enxio.fr")
www(enxio_fr, "@")
www(enxio_fr, "www")
www(enxio_fr, "media")
fastmail_mx(enxio_fr)
sign(enxio_fr)
