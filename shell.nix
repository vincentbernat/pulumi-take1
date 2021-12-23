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
    # Custom plugins (pulumi+python)
    pulumi-plugins =
      let builder = name: src': args: {
            plugin = pkgs.buildGoModule (rec {
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
              subPackages = [ "cmd/pulumi-resource-${name}" ];
            } // args);
            python = mach-nix.buildPythonPackage {
              pname = "pulumi_${name}";
              src = "${src'}/sdk/python";
            };
          };
      in
        {
          vultr = builder "vultr" (pkgs.fetchFromGitHub {
            owner = "vincentbernat";
            repo = "pulumi-vultr";
            rev = "171c75f59d16";
            sha256 = "sha256-MxBgrs3hunZ1ub1GlhYup2Zw/Uypws3xMYmvbDwjtbU=";
          }) {
            vendorSha256 = "sha256-EkSZ2pGlyBLz+FL/0ViXmzKmWjcYqYYJ+rY18LF3Q4E=";
          };
          gandi = builder "gandi" (pkgs.fetchFromGitHub {
            owner = "vincentbernat";
            repo = "pulumi-gandi";
            rev = "57a01e67ed3e";
            sha256 = "sha256-92ZsFcThqFh8jGz6hKMXFq2r6TOV41r+xlc5X4f8GT8=";
          }) {
            vendorSha256 = "sha256-LjUxilWiVyzqjhRSfJ+tnxkj3JWb1o7xs1zBns1cTHA=";
          };
        };
    # Grab versions we got to match for Python
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
    # Python environment
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
      packagesExtra = [
        pulumi-plugins.vultr.python
        pulumi-plugins.gandi.python
      ];
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
    pulumi-plugins.vultr.plugin
    pulumi-plugins.gandi.plugin
    python-env
  ];
  shellHook = ''
    export PULUMI_SKIP_UPDATE_CHECK=1
    echo "Importing secrets..."
    export PULUMI_CONFIG_PASSPHRASE=$(pass show personal/pulumi/stack-dev)
    for p in \
      njf.nznmba.pbz/Nqzvavfgengbe \
      urgmare.pbz/ivaprag@oreang.pu \
      ihyge.pbz/ihyge@ivaprag.oreang.pu; do
        eval $(pass show personal/$(echo $p | tr 'A-Za-z' 'N-ZA-Mn-za-m') | grep '^export')
    done
  '';
}
