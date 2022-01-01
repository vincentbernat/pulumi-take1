# Musings around Pulumi

This is my first tentative to use [Pulumi][] to manage my personal
infrastructure. This is an exploration to let me become more familiar
with it. Servers are then managed using NixOps. Check my
[nixops-take1][] repository for this part.

[nixops-take1]: https://github.com/vincentbernat/nixops-take1
[Pulumi]: https://www.pulumi.com/

## Shell

Use `nix develop -c $SHELL` to enter the appropriate environment. You
need to have Flakes support for this to work.

## Setup

Use the local filesystem to store states and select `dev` as the
default (and only) stack.

```
pulumi login file://.
pulumi stack select dev
```

## Configuration

```
pulumi config set aws:region us-east-1
pulumi config set --secret gandi-vb
pulumi config set --secret gandi-rb
```

## Interaction with NixOps

When there is a change, the stack output should be exported to NixOps:

```
pulumi stack output --json > ~-automation/nixops-take1/pulumi.json
```
