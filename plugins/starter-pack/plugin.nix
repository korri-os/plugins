{
  pkgs,
  fake08Plugin,
  solarusPlugin,
}:
let
  cartridges = import ./cartridges-package.nix { inherit pkgs; };
  payload = "${cartridges}/share/starter-pack";
in
{
  # Runtimes own discovery and launch. Pin their exact Korri plugin outputs,
  # not raw engines or cores. Keep the existing native file treaty unchanged.
  requires = [
    fake08Plugin
    solarusPlugin
  ];
  packages = { inherit cartridges; };
  files = {
    cartridges = "${payload}/cartridges";
    credits = "${payload}/CREDITS.md";
    license = "${payload}/CC-BY-NC-SA-4.0.txt";
    notices = "${payload}/notices";
    checksums = "${payload}/SHA256SUMS";
    instructions = "${payload}/README.md";
  };
}
