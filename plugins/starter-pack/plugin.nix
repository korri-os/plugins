{ pkgs, fake08Plugin }:
let
  cartridges = import ./cartridges-package.nix { inherit pkgs; };
  payload = "${cartridges}/share/starter-pack";
in
{
  # FAKE-08 owns the runner and runtime. Pin its exact Korri plugin output,
  # not the raw core or frontend package.
  requires = [ fake08Plugin ];
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
