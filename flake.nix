{
  inputs = {
    nixpkgs.url = "nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
    vultr-provider = {
      url = "github:vincentbernat/pulumi-vultr";
      flake = false;
    };
    gandi-provider = {
      url = "github:vincentbernat/pulumi-gandi?ref=vbe/main";
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
            pulumi-hcloud = super.pulumi-hcloud.overridePythonAttrs (old: {
              nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ self.setuptools ];
            });
          });
        };
        # Custom providers (pulumi+python)
        pulumiProviders =
          let
            builder = name: src': args: {
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
              vendorSha256 = "sha256-auhDWu+0bVvZ8wUPKVyUR6DzvxBd9jI0XLAMTv7BYwI=";
            };
          };
        # Check Python versions for mismatch (against the providers shipped in pulumi-bin package)
        pulumiVersions = builtins.listToAttrs (map
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
        poetryVersions = lib.filterAttrs
          (n: _: (builtins.match "^pulumi.*" n) != null)
          (builtins.listToAttrs (map
            (p: { name = p.pname; value = p.version; })
            poetry.poetryPackages));
        warnWhenMismatch = builtins.attrValues (lib.mapAttrs
          (p: v:
            let bv = pulumiVersions."${p}"; in
            lib.warnIf (bv != v) "Versions mismatch for ${p}: ${bv} != ${v}" null)
          poetryVersions);
        # Python environment
        pythonEnv = builtins.deepSeq warnWhenMismatch
          (poetry.python.withPackages (ps: poetry.poetryPackages ++ [
            ps.pip
            ps.setuptools
            ps.black
            pulumiProviders.vultr.python
            pulumiProviders.gandi.python
          ]));
      in
      {
        packages.poetry = pkgs.poetry;
        devShell = pythonEnv.env.overrideAttrs (oldAttrs: {
          name = "pulumi-take1";
          buildInputs = [
            pkgs.pulumi-bin
            pulumiProviders.vultr.plugin
            pulumiProviders.gandi.plugin
          ];
          shellHook = ''
            export PULUMI_SKIP_UPDATE_CHECK=1
            [ "$TERM" = dumb ] || {
              export PULUMI_CONFIG_PASSPHRASE=$(pass show personal/pulumi/stack-dev)
              for p in \
                njf.nznmba.pbz/Nqzvavfgengbe \
                urgmare.pbz/ivaprag@oreang.pu \
                ihyge.pbz/ihyge@ivaprag.oreang.pu; do
                  eval $(pass show personal/$(echo $p | tr 'A-Za-z' 'N-ZA-Mn-za-m') | grep '^export')
              done
            }
          '';
        });
      });
}
