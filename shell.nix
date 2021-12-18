let pkgs = import <nixpkgs> {};
    mach-nix = import (pkgs.fetchFromGitHub {
      owner = "DavHau"; repo = "mach-nix";
      rev = "3.3.0";
      sha256 = "sha256-RvbFjxnnY/+/zEkvQpl85MICmyp9p2EoncjuN80yrYA=";
    }) {
      inherit pkgs;
      pypiDataRev = "99799f6300b2dc4a4063dc3da032f5f169709567";
      pypiDataSha256 = "0kacxgr7cybd0py8d3mshr9h3wab9x3fvrlpr2fd240xg0v2k5gm";
    };
    pulumi-plugins =
      let builder = name: src': args: pkgs.buildGoModule (rec {
            pname = "pulumi-plugin-${name}";
            version = "0.0.0";
            src = src';
            modRoot = "./provider";
            preBuild = ''
              cat <<EOF > pkg/version/version.go
              package version
              var Version string = "v0.0.0"
              EOF
            '';
          } // args);
      in
        {
          vultr = builder "vultr" (pkgs.fetchFromGitHub {
            owner = "vincentbernat";
            repo = "pulumi-vultr";
            rev = "main";
            sha256 = "sha256-Pl3bi3VUtw/SARMBNBthKQaXuVYzbRDHfhZ+g7/iXJc=";
          }) {
            vendorSha256 = "sha256-EkSZ2pGlyBLz+FL/0ViXmzKmWjcYqYYJ+rY18LF3Q4E=";
          };
        };
    pulumi-version = pkgs.pulumi-bin.version;
    pulumi-XXX-version = what: builtins.elemAt
      (pkgs.lib.flatten
        (builtins.filter (x: x != null)
          (map
            (x: builtins.match "^pulumi-resource-${what}-v([0-9.]+)-linux.*" x.name)
            pkgs.pulumi-bin.srcs)))
      0;
    pulumi-aws-version = pulumi-XXX-version "aws";
    pulumi-hcloud-version = pulumi-XXX-version "hcloud";
    python-env = mach-nix.mkPython {
      requirements = ''
        pulumi==${pulumi-version}
        pulumi-aws==${pulumi-aws-version}
        pulumi-hcloud==${pulumi-hcloud-version}

        # Needed for pulumi to detect plugins
        pip
        setuptools

        # Other tools
        black
      '';
      providers = {
        pip = "nixpkgs";
        setuptools = "nixpkgs";
        black = "nixpkgs";
      };
    };
in
pkgs.mkShell {
  name = "pulumi-take1";
  buildInputs = [
    pkgs.pulumi-bin
    pulumi-plugins.vultr
    python-env
  ];
  shellHook = ''
    export PULUMI_SKIP_UPDATE_CHECK=1
    echo "Importing secrets..."
    export PULUMI_CONFIG_PASSPHRASE=$(pass show personal/pulumi/stack-dev)
    eval $(pass show personal/aws.amazon.com/Administrator | grep '^export')
    eval $(pass show personal/hetzner.com/vincent@bernat.ch | grep '^export')
  '';
}
