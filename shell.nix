let pkgs = import <nixpkgs> {};
    mach-nix = import (builtins.fetchGit {
      url = "https://github.com/DavHau/mach-nix";
      ref = "refs/tags/3.3.0";
    }) {
      inherit pkgs;
    };
    python-env = mach-nix.mkPython {
      requirements = ''
        pulumi==3.3.0
        pulumi-aws==4.5.1

        # Needed for pulumi to detect plugins
        pip
        setuptools
      '';
      providers = {
        pip = "nixpkgs";
        setuptools = "nixpkgs";
      };
    };
in
pkgs.mkShell {
  name = "pulumi-take1";
  buildInputs = [
    pkgs.pulumi-bin
    python-env
  ];
  shellHook = ''
    export PULUMI_SKIP_UPDATE_CHECK=1
    export PULUMI_CONFIG_PASSPHRASE=$(pass show personal/pulumi/stack-dev)
    eval $(pass show personal/aws.amazon.com/Administrator | grep '^export')
  '';
}
