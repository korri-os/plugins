{ pkgs }:
pkgs.runCommand "korri-github-cache-check"
  {
    NIX_SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
    nativeBuildInputs = [
      pkgs.python3
      pkgs.nix
      pkgs.openssl
      pkgs.bash
      pkgs.actionlint
      pkgs.git
    ];
  }
  ''
    cp ${./github-cache.py} github-cache.py
    cp ${./github-cache-test.py} github-cache-test.py
    cp ${./github-cache-github-fixture.py} github-cache-github-fixture.py
    cp ${./pages-cache.test.py} pages-cache.test.py
    python3 github-cache-test.py
    python3 pages-cache.test.py
    cp ${./metadata-migration.test.py} metadata-migration.test.py
    python3 metadata-migration.test.py
    actionlint ${../.github/workflows/plugin-repository.yml} ${../.github/workflows/cache-pages.yml}
    touch "$out"
  ''
