{ pkgs }:
pkgs.runCommand "korri-github-cache-check"
  {
    nativeBuildInputs = [
      pkgs.python3
      pkgs.nix
      pkgs.openssl
      pkgs.bash
      pkgs.actionlint
    ];
  }
  ''
    cp ${./github-cache.py} github-cache.py
    cp ${./github-cache-test.py} github-cache-test.py
    cp ${./github-cache-github-fixture.py} github-cache-github-fixture.py
    python3 github-cache-test.py
    actionlint ${../.github/workflows/plugin-repository.yml}
    touch "$out"
  ''
