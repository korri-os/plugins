# Read cache identities from the locked Core input's existing owners.
{ korri, includeCore }:
let
  requirements = import "${korri}/nix/product/requirements.nix" { inherit korri; };
  publisher = requirements.constants.publishers."@korri";
in
{
  # Publishing must not inherit Core signatures into its append-only cache.
  # Lifecycle verification does not export, so it can also reuse Core outputs.
  substituters =
    builtins.filter (url: includeCore || url != korri.cache.url) requirements.constants.substituters
    ++ [ publisher.cacheUrl ];
  publicKeys = (if includeCore then korri.cache.publicKeys else [ ]) ++ [ publisher.publicKey ];
}
