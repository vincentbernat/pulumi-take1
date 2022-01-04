import re
import json
import collections
import pulumi
import pulumi_aws as aws
import pulumi_gandi as gandi
from .kms import dns_cmk
from .vm import all_servers

gandi_vb = gandi.Provider("gandi-vb", key=pulumi.Config().get_secret("gandi-vb"))
gandi_rb = gandi.Provider("gandi-rb", key=pulumi.Config().get_secret("gandi-rb"))


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

    def registrar(self, provider):
        """Register zone to Gandi."""
        gandi.domain.Nameservers(
            self.name,
            domain=self.name,
            nameservers=self.zone.name_servers,
            opts=pulumi.ResourceOptions(provider=provider),
        )
        if self.ksk:
            gandi.domain.DnssecKey(
                self.name,
                domain=self.name,
                algorithm=self.ksk.signing_algorithm_type,
                public_key=self.ksk.public_key,
                type="ksk",
                opts=pulumi.ResourceOptions(provider=provider),
            )
        return self

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
        self.TXT("_dmarc", "v=DMARC1; p=none; sp=none")
        return self

    def fastmail_services(self):
        """Create service records for Fastmail."""
        self.SRV("_submission._tcp", "0 1 587 smtp.fastmail.com.")
        for service, port in (("imap", 993), ("carddav", 443), ("caldav", 443)):
            self.SRV(f"_{service}._tcp", "0 0 0 .")
            self.SRV(f"_{service}s._tcp", f"0 1 {port} {service}.fastmail.com.")
        return self

    def www(self, name, **kwargs):
        """Create records for web servers."""
        ttl = 60 * 60 * 2
        servers = {
            server["server"].name: {
                "A": server["server"].ipv4_address,
                "AAAA": server["server"].ipv6_address,
                "geolocations": server["geolocations"],
            }
            for server in all_servers
            if not server.get("disabled") and "web" in server.get("tags", [])
        }
        self._www(name, servers, ttl, **kwargs)
        self.record(name, "CAA", ['0 issue "buypass.com"', '0 issuewild ";"'])
        if name == "@":
            self.CNAME("_acme-challenge", f"{self.name}.acme.luffy.cx.")
        else:
            self.CNAME(f"_acme-challenge.{name}", f"{name}.{self.name}.acme.luffy.cx.")
        return self

    def _www(self, name, servers, ttl, geolocation=False):
        """Create A/AAAA records for servers."""
        assert not geolocation, "cannot handle geolocation request"
        for rrtype in ("A", "AAAA"):
            self.record(
                name,
                rrtype,
                [servers[server][rrtype] for server in servers],
                ttl=ttl,
            )
        return self


class MultiZone(Zone):
    def __init__(self, *zones):
        self.zones = zones

    def __getattribute__(self, attr):
        if attr.startswith("__"):
            return object.__getattribute__(self, attr)
        zones = object.__getattribute__(self, "zones")
        val = getattr(zones[0], attr)
        if callable(val):

            def wrapper(*args, **kwargs):
                for zone in zones:
                    getattr(zone, attr)(*args, **kwargs)
                return self

            return wrapper
        return val


class GandiZone(Zone):
    def __init__(self, name, provider, **kwargs):
        """Manage a zone on Gandi LiveDNS."""
        self.name = name
        self.provider = provider
        self.ksk = None

    def record(self, name, rrtype, records, ttl=86400):
        """Create a record."""
        if type(records) is str:
            records = [records]
        if rrtype == "TXT":
            records = [f'"{r}"' for r in records]
        gandi.livedns.Record(
            f"{rrtype}-{name}.{self.name}",
            zone=self.name,
            name=name,
            type=rrtype,
            ttl=ttl,
            values=records,
            opts=pulumi.ResourceOptions(provider=self.provider),
        )
        return self


class Route53Zone(Zone):
    def __init__(self, name, **kwargs):
        self.name = name
        self.zone = aws.route53.Zone(name, name=name, **kwargs)
        self.ksk = None

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

    def _www(self, name, servers, ttl, geolocation=True):
        """Create records for web servers."""
        if geolocation:
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
        else:
            super()._www(name, servers, ttl)
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
        return self

    def allow_user(self, user_name):
        """Create a user allowed to make modifications to the zone."""
        user = aws.iam.User(user_name, name=user_name, path="/")
        aws.iam.UserPolicy(
            f"{user_name}-{self.name}",
            name=f"AmazonRoute53-{self.name}-FullAccess",
            policy=self.zone.arn.apply(
                lambda arn: json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "route53:GetChange",
                                    "route53:ChangeResourceRecordSets",
                                    "route53:ListResourceRecordSets",
                                ],
                                "Resource": ["arn:aws:route53:::change/*", arn],
                            },
                            {
                                "Effect": "Allow",
                                "Action": ["route53:ListHostedZones"],
                                "Resource": "*",
                            },
                        ],
                    },
                )
            ),
            user=user,
        )
        return self


# enxio.fr
zone = MultiZone(
    Route53Zone("enxio.fr").sign().registrar(gandi_vb),
    GandiZone("enxio.fr", gandi_vb),
)
zone.www("@").www("www").www("media")
zone.fastmail_mx()

# une-oasis-une-ecole.fr
zone = MultiZone(
    Route53Zone("une-oasis-une-ecole.fr").sign().registrar(gandi_rb),
    GandiZone("une-oasis-une-ecole.fr", gandi_rb),
)
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
zone = MultiZone(
    Route53Zone("bernat.im").registrar(gandi_vb),
    GandiZone("bernat.im", gandi_vb),
)
zone.www("@").www("vincent")
zone.fastmail_mx()
zone = MultiZone(
    Route53Zone("bernat.ch").sign().registrar(gandi_vb),
    GandiZone("bernat.ch", gandi_vb),
)
zone.www("@").www("vincent").www("media")
zone.CNAME("4unklrhyt7lw.vincent", "gv-qcgpdhlvhtgedt.dv.googlehosted.com.")
zone.fastmail_mx(subdomains=["vincent"]).fastmail_services()

# luffy.cx
zone = luffy_cx = MultiZone(
    Route53Zone("luffy.cx").sign().registrar(gandi_vb),
    GandiZone("luffy.cx", gandi_vb),
)
zone.fastmail_mx()
zone.www("@").www("media").www("www").www("haproxy", geolocation=False)
zone.CNAME("comments", "web03.luffy.cx.")
zone.CNAME("eizo", "eizo.y.luffy.cx.")
for server in all_servers:
    name = server["server"].name
    if not name.endswith(".luffy.cx"):
        continue
    name = name.removesuffix(".luffy.cx")
    zone.A(name, [server["server"].ipv4_address])
    zone.AAAA(name, [server["server"].ipv6_address])

# y.luffy.cx (DDNS)
zone = Route53Zone("y.luffy.cx").sign()
luffy_cx.record("y", "NS", records=zone.zone.name_servers)
luffy_cx.record("y", "DS", records=[zone.ksk.ds_record])
zone.allow_user("DDNS")

# acme.luffy.cx (ACME DNS-01 challenges)
zone = Route53Zone("acme.luffy.cx").sign()
luffy_cx.record("acme", "NS", records=zone.zone.name_servers)
luffy_cx.record("acme", "DS", records=[zone.ksk.ds_record])
zone.allow_user("ACME")
pulumi.export("acme-zone", zone.zone.zone_id)
