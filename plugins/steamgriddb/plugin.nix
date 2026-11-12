# Source only: no native files. korrid makes every request for this plugin and
# refuses any host not named here, for the API turns and for the image
# download alike (Core ADR 0016, ADR 0032).
#
# `www.steamgriddb.com` is the API. `cdn2.steamgriddb.com` served the `url` of
# all 444 assets observed on 2026-11-11 (README, "Hosts").
#
# `credentialHost` is the one host that receives the person's API key (Core
# ADR 0034). korrid adds it as `Authorization: Bearer`; plugin.ts never sees
# it, and the image host never gets it. No key ships in this package.
{ pkgs }:
{
  hosts = [
    "www.steamgriddb.com"
    "cdn2.steamgriddb.com"
  ];
  credentialHost = "www.steamgriddb.com";
}
