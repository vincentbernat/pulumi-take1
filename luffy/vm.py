from types import SimpleNamespace
import ipaddress
import pulumi
import pulumi_hcloud as hcloud
import pulumi_vultr as vultr


class Server:
    """Abstraction for a server."""


class HetznerServer(Server):
    kind = "hetzner"
    def __init__(self, name, id):
        """An Hetzner server (we import them)"""
        # We do not create them. There is a problem with importing
        # existing servers when they don't have an image.
        self.name = name
        self.obj = hcloud.Server.get(name, id=id)
        self.ipv4_address = self.obj.ipv4_address
        self.ipv6_address = self.obj.ipv6_address
        hcloud.Rdns(
            f"rdns4-{name}",
            server_id=self.obj.id.apply(int),
            ip_address=self.ipv4_address,
            dns_ptr=name,
        )
        hcloud.Rdns(
            f"rdns6-{name}",
            server_id=self.obj.id.apply(int),
            ip_address=self.ipv6_address,
            dns_ptr=name,
        )


class VultrServer(Server):
    kind = "vultr"
    def __init__(self, name, **kwargs):
        """A Vultr server."""
        self.name = name
        self.obj = vultr.Instance(name, **kwargs)
        self.ipv4_address = self.obj.main_ip
        self.ipv6_address = self.obj.v6_main_ip
        vultr.ReverseIpv4(
            f"rdns4-{name}",
            instance_id=self.obj.id,
            ip=self.ipv4_address,
            reverse=name,
        )
        vultr.ReverseIpv6(
            f"rdns6-{name}",
            instance_id=self.obj.id,
            ip=self.ipv6_address.apply(lambda x: ipaddress.ip_address(x).exploded),
            reverse=name,
        )


# Each location should be covered by at least two servers...
www_servers = [
    {
        "server": HetznerServer("web03.luffy.cx", "1041986"),
        "geolocations": [("continent", ["EU", "AF"])],
    },
    {
        "server": HetznerServer("web04.luffy.cx", "1413514"),
        "geolocations": [("continent", ["EU", "AF"])],
    },
    {
        "server": HetznerServer("web05.luffy.cx", "15724596"),
        "geolocations": [("continent", ["NA", "SA"])],
    },
    {
        "server": VultrServer("web06.luffy.cx", plan="vc2-1c-1gb", region="ord"),
        "geolocations": [("continent", ["NA", "SA"])],
    },
]
pulumi.export("www-servers", [{k: getattr(x['server'], k)
                               for k in ("name", "kind", "ipv4_address", "ipv6_address")}
                              for x in www_servers])
