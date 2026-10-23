{
  pkgs,
  cemuSource,
  sdl3,
  fmt,
}:
pkgs.runCommand "cemu-license-notices" { nativeBuildInputs = [ pkgs.python3 ]; } ''
  python3 ${./license_notices.py} "$out" \
    ${cemuSource} ${sdl3.src} ${fmt.src} ${pkgs.mesa.src} \
    ${pkgs.zarchive.src} ${pkgs.pugixml.src} ${pkgs.rapidjson.src} \
    ${pkgs.glm.src} ${pkgs.glslang.src} ${pkgs.spirv-tools.src} \
    ${./licenses/OFL-1.1.txt}
''
