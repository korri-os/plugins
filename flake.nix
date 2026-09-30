{
  description = "Korri plugin packages and release preparation";

  inputs.korri.url = "github:korri-os/korri";

  # Index only. Core's locked inputs supply every build tool and package set.
  outputs = { korri, ... }: import ./nix { inherit korri; };
}
