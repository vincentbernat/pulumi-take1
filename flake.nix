{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
    mach-nix = {
      url = "github:DavHau/mach-nix?ref=3.3.0";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        flake-utils.follows = "flake-utils";
      };
    };
    vultr-provider = {
      url = "github:vincentbernat/pulumi-vultr";
      flake = false;
    };
    gandi-provider = {
      url = "github:vincentbernat/pulumi-gandi";
      flake = false;
    };
  };
  outputs = { self, nixpkgs, flake-utils, ...}@inputs:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages."${system}";
        mach-nix = inputs.mach-nix.lib."${system}";
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
        # Custom providers (pulumi+python)
        pulumi-providers =
          let builder = name: src': args: {
                plugin = pkgs.buildGoModule (rec {
                  pname = "pulumi-provider-${name}";
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
                  requirementsExtra = "pulumi==${pulumi-version}";
                };
              };
          in
            {
              vultr = builder "vultr" inputs.vultr-provider {
                vendorSha256 = "sha256-EkSZ2pGlyBLz+FL/0ViXmzKmWjcYqYYJ+rY18LF3Q4E=";
              };
              gandi = builder "gandi" inputs.gandi-provider {
                vendorSha256 = "sha256-LjUxilWiVyzqjhRSfJ+tnxkj3JWb1o7xs1zBns1cTHA=";
              };
            };
        # Python environment
        python-env = mach-nix.mkPython {
          requirements = ''
            pulumi==${pulumi-version}
            pulumi-aws==${pulumi-aws-version}
            pulumi-hcloud==${pulumi-hcloud-version}

            # Needed for pulumi to detect providers
            pip
            setuptools

            # Other tools
            black
          '';
          packagesExtra = [
            pulumi-providers.vultr.python
            pulumi-providers.gandi.python
          ];
          providers = {
            pip = "nixpkgs";
            setuptools = "nixpkgs";
            black = "nixpkgs";
          };
        };
      in {
        devShell = pkgs.mkShell {
          name = "pulumi-take1";
          buildInputs = [
            pkgs.pulumi-bin
            pulumi-providers.vultr.plugin
            pulumi-providers.gandi.plugin
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
        };
    });
}
