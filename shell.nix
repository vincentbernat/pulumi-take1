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
    python-env = mach-nix.mkPython {
      requirements = ''
        pulumi==3.19.0
        pulumi-aws==4.5.1
        pulumi-hcloud==1.7.0

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
    python-env
  ];
  shellHook = ''
    export PULUMI_SKIP_UPDATE_CHECK=1
    export PULUMI_CONFIG_PASSPHRASE=$(pass show personal/pulumi/stack-dev)
    eval $(pass show personal/aws.amazon.com/Administrator | grep '^export')
    eval $(pass show personal/hetzner.com/vincent@bernat.ch | grep '^export')
  '';
}
