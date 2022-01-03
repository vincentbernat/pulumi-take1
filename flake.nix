{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
    vultr-provider = {
      url = "github:vincentbernat/pulumi-vultr";
      flake = false;
    };
    gandi-provider = {
      url = "github:vincentbernat/pulumi-gandi";
      flake = false;
    };
  };
  outputs = { self, flake-utils, ... }@inputs:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = inputs.nixpkgs.legacyPackages."${system}";
        lib = pkgs.lib;
        poetry = pkgs.poetry2nix.mkPoetryPackages {
          projectDir = ./.;
          overrides = pkgs.poetry2nix.overrides.withDefaults (self: super: {
            doCheck = false;
            doInstallCheck = false;
            dontUseSetuptoolsCheck = true;
            dontUsePytestCheck = true;
          });
        };
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
            python = pkgs.python3.pkgs.buildPythonPackage {
              pname = "pulumi_${name}";
              version = "0.0.0";
              src = "${src'}/sdk/python";
              doCheck = false;
              propagatedBuildInputs = poetry.poetryPackages;
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
        # Check Python versions for mismatch
        pulumi-bin-versions = builtins.listToAttrs (map
          (p:
            let
              match = builtins.match "^(pulumi.*)-v([0-9.]+)-.*" p.name;
            in
            {
              name = builtins.replaceStrings [ "-resource-" ] [ "-" ] (lib.head match);
              value = lib.last match;
            }
          )
          pkgs.pulumi-bin.srcs);
        poetry-versions = lib.filterAttrs
          (n: _: (builtins.match "^pulumi.*" n) != null)
          (builtins.listToAttrs (map
            (p: { name = p.pname; value = p.version; })
            poetry.poetryPackages));
        warnWhenMismatch = builtins.attrValues (lib.mapAttrs
          (p: v:
            let bv = pulumi-bin-versions."${p}"; in
            lib.warnIf (bv != v) "Versions mismatch for ${p}: ${bv} != ${v}" null)
          poetry-versions);
        # Python environment
        python-env = builtins.deepSeq warnWhenMismatch
          (poetry.python.withPackages (ps: poetry.poetryPackages ++ [
            ps.pip
            ps.setuptools
            ps.black
            pulumi-providers.vultr.python
            pulumi-providers.gandi.python
          ]));
      in
      {
        packages.poetry = pkgs.poetry;
        devShell = python-env.env.overrideAttrs (oldAttrs: {
          name = "pulumi-take1";
          buildInputs = [
            pkgs.pulumi-bin
            pulumi-providers.vultr.plugin
            pulumi-providers.gandi.plugin
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
        });
      });
}