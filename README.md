# Musings around Pulumi

This is my first tentative to use [Pulumi][] to manage my personal
infrastructure. This is an exploration to let me become more familiar
with it. Servers are then managed using NixOps. Check my
[nixops-take1][] repository for this part.

[nixops-take1]: https://github.com/vincentbernat/nixops-take1
[Pulumi]: https://www.pulumi.com/

## Shell

Use `nix-shell` to enter the appropriate environment.

## Setup

Use the local filesystem to store states.

```
pulumi login file://.
```
