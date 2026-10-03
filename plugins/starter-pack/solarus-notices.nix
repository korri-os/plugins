{ pkgs }:
{
  licenses = [
    (pkgs.fetchurl {
      name = "CC-BY-4.0.txt";
      url = "https://creativecommons.org/licenses/by/4.0/legalcode.txt";
      hash = "sha256-m6lVCtSEONCDbdqz2kgLO2n/oKrHt4eLWgA556tClBE=";
    })
    (pkgs.fetchurl {
      name = "CC-BY-SA-4.0.txt";
      url = "https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt";
      hash = "sha256-KKlSnH0LtNxR9L9cEWo9Fu8kegUvdZFGZ2jd9WP9HPU=";
    })
    (pkgs.fetchurl {
      name = "CC-BY-3.0.txt";
      url = "https://creativecommons.org/licenses/by/3.0/legalcode.txt";
      hash = "sha256-5ryenEdHALcI9Wi6yeWoqbyysdrVNEL1ukSfy4SLjnY=";
    })
    (pkgs.fetchurl {
      name = "CC0-1.0.txt";
      url = "https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt";
      hash = "sha256-ogEPNDSH0/dhiv/lT3ifVIdgIzHAqNA/SemnxUfPBJk=";
    })
  ];
  # First-party wiki version, not a mutable current-page fetch. The source
  # README points to this credits page; the archive cannot include its wiki.
  credits = pkgs.fetchurl {
    name = "voadi-credits.json";
    url = "https://gitlab.com/api/v4/projects/6909214/wikis/credits?version=ab311c41cb1b7fce58ff3465889f9cd272c20a4b";
    hash = "sha256-Xw5L7z4oH9mapGjKzdPHtvTWQpB5CWt2f/dItMF/mWA=";
  };
}
