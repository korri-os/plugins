{ pkgs }:
# Fixed source archives from the two owner-approved repositories. Asset bytes
# stay in fetched outputs, never in this repository. Names follow those repos;
# Solarus discovery consumes the existing .solarus suffix, not a new catalog.
[
  (pkgs.fetchurl {
    name = "perlshaws-problems.tar.gz";
    url = "https://api.github.com/repos/AgentNintaku/perlshaws-problems/tarball/cdc5ea95d84be7051da08a1c770e511648aae1b0";
    hash = "sha256-/wWmNhAsS/yHTH7PbuRJpxvHr75t7AqTb05yF9ObebM=";
  })
  (pkgs.fetchurl {
    name = "voadi.tar.gz";
    url = "https://gitlab.com/api/v4/projects/voadi%2Fvoadi/repository/archive.tar.gz?sha=197105cb25eb0de1b7e6d4acc25303ece1be479f";
    hash = "sha256-VqPOdWw67TevB2HmTnuxqWOu4DdiGbiOc+kym6lMhKU=";
  })
]
