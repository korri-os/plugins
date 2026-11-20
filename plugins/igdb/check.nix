# The shared acquisition check covers the manifest's `hosts`, the package
# contents, host admission, `tsc --strict` and the unit tests. It does not
# know `credentialHost` and `credentialTokenUrl` (Core ADR 0034 and its IGDB
# amendment). This check adds those assertions and passes only when the
# shared check passed.
{
  pkgs,
  package,
  shared,
}:
pkgs.runCommand "korri-igdb-credential-check"
  {
    nativeBuildInputs = [ pkgs.jq ];
  }
  ''
    test -e ${shared}
    jq -e '
      .credentialHost == "api.igdb.com" and
      .credentialTokenUrl == "https://id.twitch.tv/oauth2/token" and
      (.hosts | index("api.igdb.com") != null) and
      (.hosts | index("id.twitch.tv") != null)
    ' ${package}/manifest.json
    touch "$out"
  ''
