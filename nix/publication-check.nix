{ pkgs }:
pkgs.runCommand "korri-publication-workflow-check"
  {
    nativeBuildInputs = [
      (pkgs.python3.withPackages (p: [ p.pyyaml ]))
      pkgs.actionlint
    ];
  }
  ''
    python3 ${./publication_test.py} ${./publication.py} ${../.github/workflows/plugin-repository.yml}
    actionlint ${../.github/workflows/plugin-repository.yml}
    touch "$out"
  ''
