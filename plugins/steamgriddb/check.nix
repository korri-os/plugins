# The shared acquisition check covers the manifest's `hosts`, the package
# contents, host admission, `tsc --strict` and the unit tests. It does not
# know `credentialHost` (Core ADR 0034). This check adds that one assertion
# and passes only when the shared check passed.
{
  pkgs,
  package,
  shared,
}:
pkgs.runCommand "korri-steamgriddb-credential-host-check"
  {
    nativeBuildInputs = [ pkgs.jq ];
  }
  ''
    test -e ${shared}
    jq -e '
      .credentialHost == "www.steamgriddb.com" and
      (.hosts | index("www.steamgriddb.com") != null)
    ' ${package}/manifest.json
    touch "$out"
  ''
