{
  description = "Korri plugin packages and release preparation";

  inputs.korri.url = "github:korri-os/korri";
  # Keep the experiment on the exact producer of the Mini's active plugin.
  inputs.baselineKorri.url = "github:korri-os/korri/1a988da5318ba5c8503c0e260bd169b57e4df4ca";

  # Index only. Each locked Core input supplies its own build tool and packages.
  outputs = { korri, baselineKorri, ... }: import ./nix { inherit korri baselineKorri; };
}
