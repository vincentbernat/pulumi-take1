# Musings around Pulumi

This is my first tentative to use Pulumi to manage my personal
infrastructure. This is an exploration to let me become more familiar
with it. Servers are then managed using NixOps. Check my
[nixops-take1][] repository for this part.

## Shell

Use `nix-shell` to enter the appropriate environment.

## Setup

Use the local filesystem to store states.

```
pulumi login file://.
```
