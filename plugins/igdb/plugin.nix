# Source only: no native files. korrid makes every request for this plugin and
# refuses any host not named here, for the API turns, the token exchange and
# the image download alike (Core ADR 0016, ADR 0032, ADR 0034).
#
# `api.igdb.com` is the API. `images.igdb.com` serves every image
# (api-docs.igdb.com, Images). `id.twitch.tv` is where korrid exchanges the
# person's Twitch client ID and client secret for an app token
# (dev.twitch.tv, client credentials grant flow).
#
# `credentialHost` is the one host that receives the client ID and the token;
# `credentialTokenUrl` is the one address that receives the client secret,
# in a form body (Core ADR 0034, IGDB amendment). plugin.ts never sees any
# of them. No key ships in this package.
{ pkgs }:
{
  hosts = [
    "api.igdb.com"
    "id.twitch.tv"
    "images.igdb.com"
  ];
  credentialHost = "api.igdb.com";
  credentialTokenUrl = "https://id.twitch.tv/oauth2/token";
}
