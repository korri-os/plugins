# Gamepad acceptance for the packaged player: virtual Korri seats in a
# disposable VM. No host input device is forwarded into the guest.
{ pkgs, launcher }:
let
  publicFixture = import ./zquest-public-fixture.nix { inherit pkgs; };
  python = pkgs.python3.withPackages (python: [
    python.evdev
    python.pillow
  ]);
in
pkgs.testers.runNixOSTest {
  name = "zquest-gamepad";
  nodes.machine = {
    environment.etc."zquest-gamepad-vm".text = "disposable-vm-only\n";
    environment.systemPackages = [
      python
      pkgs.xvfb-run
      pkgs.xdotool
      pkgs.imagemagick
    ];
    hardware.graphics.enable = true;
    boot.kernelModules = [ "uinput" ];
    virtualisation = {
      memorySize = 2048;
      cores = 2;
    };
  };
  testScript = ''
    machine.wait_for_unit("multi-user.target")
    machine.succeed(
        "LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a -s '-screen 0 800x600x24' "
        "python3 ${./zquest-gamepad-vm.py} "
        "${launcher}/bin/zplayer ${publicFixture}/public-room.qst "
        ">&2"
    )
  '';
}
