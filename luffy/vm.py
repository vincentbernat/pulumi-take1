from types import SimpleNamespace
import pulumi
import pulumi_hcloud as hcloud


def hetzner_server(name, id):
    """An Hetzner server (we import them)"""
    # We do not create them. There is a problem with importing
    # existing servers when they don't have an image.
    server = hcloud.Server.get(name, id=id)
    hcloud.Rdns(
        f"rdns4-{name}",
        server_id=server.id.apply(int),
        ip_address=server.ipv4_address,
        dns_ptr=name,
    )
    hcloud.Rdns(
        f"rdns6-{name}",
        server_id=server.id.apply(int),
        ip_address=server.ipv6_address,
        dns_ptr=name,
    )
    return server


# Each location should be covered by at least two servers...
www_servers = [
    {
        "server": hetzner_server("web03.luffy.cx", "1041986"),
        "geolocations": [("continent", ["EU", "AF"])],
    },
    {
        "server": hetzner_server("web04.luffy.cx", "1413514"),
        "geolocations": [("continent", ["EU", "AF"])],
    },
    {
        "server": hetzner_server("web05.luffy.cx", "15724596"),
        "geolocations": [("continent", ["NA", "SA"])],
    },
    {
        "server": SimpleNamespace(
            _name="web06.luffy.cx",
            ipv4_address="149.28.124.245",
            ipv6_address="2001:19f0:5c01:1894::1",
        ),
        "geolocations": [("continent", ["NA", "SA"])],
    },
]
