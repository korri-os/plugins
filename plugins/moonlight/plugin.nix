{ pkgs, moonlightPackage }:
let
  setup = pkgs.writeTextFile {
    name = "korri-moonlight-setup.service";
    destination = "/lib/systemd/system/korri-moonlight-setup.service";
    text = pkgs.lib.replaceStrings [ "@coreutils@" ] [ (toString pkgs.coreutils) ] (
      builtins.readFile ./korri-moonlight-setup.service
    );
  };
in
{
  packages.moonlight = moonlightPackage;
  files = {
    moonlight = "${moonlightPackage}/bin/moonlight";
    mapping = "${moonlightPackage}/share/moonlight/korri-inputplumber-gamecontrollerdb.txt";
  };
  services.korri-moonlight-setup = "${setup}/lib/systemd/system/korri-moonlight-setup.service";
}
