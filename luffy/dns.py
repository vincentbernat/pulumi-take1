import re
import collections
import pulumi
import pulumi_aws as aws
from .kms import dns_cmk
from .vm import www_servers


class Zone:
    def TXT(self, name, records, **kwargs):
        return self.record(name, "TXT", records, **kwargs)

    def MX(self, name, records, **kwargs):
        return self.record(name, "MX", records, **kwargs)

    def A(self, name, records, **kwargs):
        return self.record(name, "A", records, **kwargs)

    def AAAA(self, name, records, **kwargs):
        return self.record(name, "AAAA", records, **kwargs)

    def CNAME(self, name, records, **kwargs):
        return self.record(name, "CNAME", records, **kwargs)

    def SRV(self, name, records, **kwargs):
        return self.record(name, "SRV", records, **kwargs)

    def fastmail_mx(self, subdomains=[]):
        """Create records for MX with FastMail."""
        for subdomain in subdomains + ["@", "*"]:
            self.MX(
                subdomain,
                [
                    "10 in1-smtp.messagingengine.com.",
                    "20 in2-smtp.messagingengine.com.",
                ],
            )
        self.TXT("@", "v=spf1 include:spf.messagingengine.com ~all")
        for dk in ("mesmtp", "fm1", "fm2", "fm3"):
            self.CNAME(f"{dk}._domainkey", f"{dk}.{self.name}.dkim.fmhosted.com.")
        self.SRV("_submission._tcp", "0 1 587 smtp.fastmail.com.")
        self.SRV("_imap._tcp", "0 0 0 .")
        self.SRV("_imaps._tcp", "0 1 993 imap.fastmail.com.")
        self.TXT("_dmarc", "v=DMARC1; p=none; sp=none")
        return self


class Route53Zone(Zone):
    def __init__(self, name, **kwargs):
        self.name = name
        self.zone = aws.route53.Zone(name, name=name, **kwargs)
        pulumi.export(f"{self.name}-NS", self.zone.name_servers)

    def record(self, name, rrtype, records, ttl=86400, **more):
        """Create a record."""
        if name == "@":
            name = self.name
        else:
            name = f"{name}.{self.name}"
        if type(records) is str:
            records = [records]
        aws.route53.Record(
            f"{rrtype}-{more['set_identifier']}-{name}"
            if more.get("set_identifier")
            else f"{rrtype}-{name}",
            zone_id=self.zone.zone_id,
            name=f"{name}",
            type=rrtype,
            ttl=ttl,
            records=records,
            **more,
        )
        return self

    def www(self, name):
        """Create records for web servers."""
        ttl = 60 * 60 * 2
        servers = {
            server["server"].name: {
                "A": server["server"].ipv4_address,
                "AAAA": server["server"].ipv6_address,
                "geolocations": server["geolocations"],
            }
            for server in www_servers
            if not server.get("disabled")
        }
        # Normalize the data a bit
        geolocations = set()
        for server, data in servers.items():
            data["geolocations"] = [
                (k, v1) for k, v in data["geolocations"] for v1 in v
            ]
        # Build geolocation sets
        geolocations = {
            geoloc for data in servers.values() for geoloc in data["geolocations"]
        }
        # Compute records for each location
        rrs = {}
        rrs[("country", "*")] = servers.keys()
        for geoloc in geolocations:
            rrs[geoloc] = [
                server
                for server, data in servers.items()
                if geoloc in data["geolocations"]
            ]
        # Create records for Route53
        for rrtype in ("A", "AAAA"):
            for geoloc, selected_servers in rrs.items():
                self.record(
                    name,
                    rrtype,
                    [servers[server][rrtype] for server in selected_servers],
                    ttl=ttl,
                    set_identifier=f"geo-{geoloc[0]}-{geoloc[1]}",
                    geolocation_routing_policies=[dict([geoloc])],
                )
        self.record(name, "CAA", ['0 issue "buypass.com"', '0 issuewild ";"'])
        return self

    def sign(self):
        """Sign a zone."""
        self.ksk = aws.route53.KeySigningKey(
            self.name,
            hosted_zone_id=self.zone.zone_id,
            key_management_service_arn=dns_cmk.target_key_arn,
            name=re.sub(r"[^0-9a-zA-Z]", "", self.name),
            status="ACTIVE",
        )
        aws.route53.HostedZoneDnsSec(
            f"DNSSEC-{self.name}",
            hosted_zone_id=self.zone.zone_id,
            signing_status="SIGNING",
            opts=pulumi.ResourceOptions(depends_on=[self.ksk]),
        )
        pulumi.export(f"{self.name}-DS", self.ksk.ds_record)
        pulumi.export(f"{self.name}-PK", self.ksk.public_key)
        return self


# enxio.fr
zone = Route53Zone("enxio.fr").sign()
zone.www("@").www("www").www("media")
zone.fastmail_mx()

# une-oasis-une-ecole.fr
zone = Route53Zone("une-oasis-une-ecole.fr").sign()
zone.www("@").www("www").www("media")
zone.MX("@", ["10 spool.mail.gandi.net.", "50 fb.mail.gandi.net."])
zone.TXT(
    "@",
    [
        "google-site-verification=_GFUTYZ19KcdCDA26QfZI_w3oWDJoQyD5GyZ6a-ieh8",
        "v=spf1 include:_mailcust.gandi.net include:spf.mailjet.com ?all",
    ],
)
zone.TXT(
    "mailjet._domainkey",
    "k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDWsJlP6+qLJS/RLvoNrMPRPrfzcQAuvZ1vUIJkqGauJ23zowQ9ni44XqzYyiBPx00c0QCQhO7oBEhnTeVGMcIfzNASeofZDfiu2dk7iOARpBeKT+EPJtXKS8cW0nz6cusANW7Mxa1Or1sUeV5+J0jFSAmeqWjginJPHJri7ZDA6QIDAQAB",
)

# bernat.im (not signed) / bernat.ch (signed)
for zone in [Route53Zone("bernat.ch").sign(), Route53Zone("bernat.im")]:
    zone.www("@").www("vincent")
    zone.fastmail_mx(subdomains=["vincent"])
    if zone.name == "bernat.ch":
        zone.CNAME("4unklrhyt7lw.vincent", "gv-qcgpdhlvhtgedt.dv.googlehosted.com.")

# luffy.cx
zone = Route53Zone("luffy.cx").sign()
zone.fastmail_mx()
# y.luffy.cx DDNS
y_luffy_cx = Route53Zone("y.luffy.cx").sign()
zone.record("y", "NS", records=y_luffy_cx.zone.name_servers)
zone.record("y", "DS", records=[y_luffy_cx.ksk.ds_record])
zone.CNAME("eizo", "eizo.y.luffy.cx.")
# services
zone.www("@").www("media").www("www").www("haproxy")
zone.CNAME("comments", "web03.luffy.cx.")
# hosts
for server in www_servers:
    name = server["server"].name
    if not name.endswith(".luffy.cx"):
        continue
    name = name.removesuffix(".luffy.cx")
    zone.A(name, [server["server"].ipv4_address])
    zone.AAAA(name, [server["server"].ipv6_address])
