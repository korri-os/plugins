# The libretro core catalogue. One entry produces one separate plugin package:
# its own id, its own runner, its own RetroArch inside its own closure.
#
# Every entry names its core library file exactly. A file name is never derived
# from a package name, because the two disagree often enough to matter:
# beetle-pce-fast ships mednafen_pce_fast_libretro.so.
#
# Content rules live in systems.nix. Each core names only the systems it runs.
# core-plugin.nix matches each coreFile basename to the pinned libretro-core-info
# file. Its deterministic savestate flag gates build-time netplay ABI probing.
{ pkgs }:
let
  fake08 = pkgs.callPackage ./fake08/package.nix { };
  wasm4 = pkgs.callPackage ./wasm4/package.nix { };
  lowresnx = pkgs.callPackage ./lowresnx/package.nix { };
  pzretro = pkgs.callPackage ./pzretro/package.nix { };
  # nixpkgs marks PPSSPP `badPlatforms = [ "aarch64-linux" ]`. It is the only
  # first-party PSP libretro core and it is wanted on the SM8550 target, so the
  # platform block is lifted for this catalogue only. Every other core keeps
  # nixpkgs' platform metadata.
  #
  # ParaLLEl N64's block is deliberately NOT lifted. Verified on a build host on
  # 2026-09-19: the aarch64 link fails with `relocation truncated to fit:
  # R_AARCH64_CONDBR19 against symbol 'invalidate_block'`, so this core cannot
  # ship for the target. Mupen64Plus remains the N64 runner there.
  ppsspp = pkgs.libretro.ppsspp.overrideAttrs (old: {
    meta = old.meta // {
      badPlatforms = [ ];
    };
  });
in
{
  mgba = {
    title = "mGBA";
    description = "Runs Game Boy Advance content with the mGBA libretro core.";
    core = pkgs.libretro.mgba;
    coreFile = "${pkgs.libretro.mgba}/lib/retroarch/cores/mgba_libretro.so";
    systems = [ "gba" ];
  };

  fake08 = {
    title = "FAKE-08";
    description = "Runs PICO-8 cartridges with the FAKE-08 libretro reimplementation.";
    core = fake08;
    coreFile = "${fake08}/lib/retroarch/cores/fake08_libretro.so";
    systems = [ "pico8" ];
  };

  gambatte = {
    title = "Gambatte";
    description = "Runs Game Boy and Game Boy Color content with the Gambatte libretro core.";
    core = pkgs.libretro.gambatte;
    coreFile = "${pkgs.libretro.gambatte}/lib/retroarch/cores/gambatte_libretro.so";
    systems = [
      "gb"
      "gbc"
    ];
  };

  fceumm = {
    title = "FCEUmm";
    description = "Runs Nintendo Entertainment System content with the FCEUmm libretro core.";
    core = pkgs.libretro.fceumm;
    coreFile = "${pkgs.libretro.fceumm}/lib/retroarch/cores/fceumm_libretro.so";
    systems = [
      "nes"
      "fds"
    ];
  };

  snes9x2010 = {
    title = "Snes9x 2010";
    description = "Runs Super Nintendo content with the Snes9x 2010 libretro core.";
    core = pkgs.libretro.snes9x2010;
    coreFile = "${pkgs.libretro.snes9x2010}/lib/retroarch/cores/snes9x2010_libretro.so";
    systems = [ "snes" ];
  };

  genesis-plus-gx = {
    title = "Genesis Plus GX";
    description = "Runs Sega 8-bit and 16-bit content with the Genesis Plus GX libretro core.";
    core = pkgs.libretro.genesis-plus-gx;
    coreFile = "${pkgs.libretro.genesis-plus-gx}/lib/retroarch/cores/genesis_plus_gx_libretro.so";
    systems = [
      "md"
      "sms"
      "gg"
      "sg1000"
    ];
  };

  picodrive = {
    title = "PicoDrive";
    description = "Runs Mega Drive and 32X content with the ARM-tuned PicoDrive libretro core.";
    core = pkgs.libretro.picodrive;
    coreFile = "${pkgs.libretro.picodrive}/lib/retroarch/cores/picodrive_libretro.so";
    # Mega Drive overlaps Genesis Plus GX on purpose. Two cores may claim one
    # system: content rules combine and the player picks a runner.
    systems = [
      "md"
      "sega32x"
    ];
  };

  beetle-pce-fast = {
    title = "Beetle PCE Fast";
    description = "Runs PC Engine content with the Beetle PCE Fast libretro core.";
    core = pkgs.libretro.beetle-pce-fast;
    coreFile = "${pkgs.libretro.beetle-pce-fast}/lib/retroarch/cores/mednafen_pce_fast_libretro.so";
    systems = [ "pce" ];
  };

  stella = {
    title = "Stella";
    description = "Runs Atari 2600 content with the Stella libretro core.";
    core = pkgs.libretro.stella;
    coreFile = "${pkgs.libretro.stella}/lib/retroarch/cores/stella_libretro.so";
    systems = [ "atari2600" ];
  };

  fuse = {
    title = "Fuse";
    description = "Runs ZX Spectrum content with the Fuse libretro core.";
    core = pkgs.libretro.fuse;
    coreFile = "${pkgs.libretro.fuse}/lib/retroarch/cores/fuse_libretro.so";
    systems = [ "zxspectrum" ];
  };

  mupen64plus = {
    title = "Mupen64Plus-Next";
    description = "Runs Nintendo 64 content with the Mupen64Plus-Next libretro core.";
    core = pkgs.libretro.mupen64plus;
    coreFile = "${pkgs.libretro.mupen64plus}/lib/retroarch/cores/mupen64plus_next_libretro.so";
    systems = [ "n64" ];
  };

  # Mesen overlaps FCEUmm on purpose, the same way PicoDrive overlaps Genesis
  # Plus GX: two cores may claim one system, and the player chooses a runner.
  mesen = {
    title = "Mesen";
    description = "Runs Nintendo Entertainment System content with the Mesen libretro core.";
    core = pkgs.libretro.mesen;
    coreFile = "${pkgs.libretro.mesen}/lib/retroarch/cores/mesen_libretro.so";
    systems = [
      "nes"
      "fds"
    ];
  };

  np2kai = {
    title = "Neko Project II Kai";
    description = "Runs PC-98 content with the Neko Project II Kai libretro core.";
    core = pkgs.libretro.np2kai;
    coreFile = "${pkgs.libretro.np2kai}/lib/retroarch/cores/np2kai_libretro.so";
    systems = [ "pc98" ];
  };

  pcsx-rearmed = {
    title = "PCSX-ReARMed";
    description = "Runs PlayStation content with the PCSX-ReARMed libretro core.";
    core = pkgs.libretro.pcsx-rearmed;
    coreFile = "${pkgs.libretro.pcsx-rearmed}/lib/retroarch/cores/pcsx_rearmed_libretro.so";
    systems = [ "psx" ];
  };

  # bsnes overlaps Snes9x 2010 on purpose, the same way PicoDrive overlaps
  # Genesis Plus GX: two cores may claim one system, and the player chooses a
  # runner.
  bsnes = {
    title = "bsnes";
    description = "Runs Super Nintendo content with the bsnes libretro core.";
    core = pkgs.libretro.bsnes;
    coreFile = "${pkgs.libretro.bsnes}/lib/retroarch/cores/bsnes_libretro.so";
    systems = [ "snes" ];
  };

  atari800 = {
    title = "Atari800";
    description = "Runs Atari 8-bit and Atari 5200 content with the Atari800 libretro core.";
    core = pkgs.libretro.atari800;
    coreFile = "${pkgs.libretro.atari800}/lib/retroarch/cores/atari800_libretro.so";
    systems = [
      "atari8bit"
      "atari5200"
    ];
  };

  beetle-lynx = {
    title = "Beetle Lynx";
    description = "Runs Lynx content with the Beetle Lynx libretro core.";
    core = pkgs.libretro.beetle-lynx;
    coreFile = "${pkgs.libretro.beetle-lynx}/lib/retroarch/cores/mednafen_lynx_libretro.so";
    systems = [ "lynx" ];
  };

  beetle-ngp = {
    title = "Beetle NeoPop";
    description = "Runs Neo Geo Pocket content with the Beetle NeoPop libretro core.";
    core = pkgs.libretro.beetle-ngp;
    coreFile = "${pkgs.libretro.beetle-ngp}/lib/retroarch/cores/mednafen_ngp_libretro.so";
    systems = [ "ngp" ];
  };

  beetle-pcfx = {
    title = "Beetle PC-FX";
    description = "Runs PC-FX content with the Beetle PC-FX libretro core.";
    core = pkgs.libretro.beetle-pcfx;
    coreFile = "${pkgs.libretro.beetle-pcfx}/lib/retroarch/cores/mednafen_pcfx_libretro.so";
    systems = [ "pcfx" ];
  };

  beetle-saturn = {
    title = "Beetle Saturn";
    description = "Runs Sega Saturn content with the Beetle Saturn libretro core.";
    core = pkgs.libretro.beetle-saturn;
    coreFile = "${pkgs.libretro.beetle-saturn}/lib/retroarch/cores/mednafen_saturn_libretro.so";
    systems = [ "saturn" ];
  };

  beetle-vb = {
    title = "Beetle VB";
    description = "Runs Virtual Boy content with the Beetle VB libretro core.";
    core = pkgs.libretro.beetle-vb;
    coreFile = "${pkgs.libretro.beetle-vb}/lib/retroarch/cores/mednafen_vb_libretro.so";
    systems = [ "vb" ];
  };

  beetle-wswan = {
    title = "Beetle WonderSwan";
    description = "Runs WonderSwan content with the Beetle WonderSwan libretro core.";
    core = pkgs.libretro.beetle-wswan;
    coreFile = "${pkgs.libretro.beetle-wswan}/lib/retroarch/cores/mednafen_wswan_libretro.so";
    systems = [ "wswan" ];
  };

  bluemsx = {
    title = "blueMSX";
    description = "Runs MSX, ColecoVision and SG-1000 content with the blueMSX libretro core.";
    core = pkgs.libretro.bluemsx;
    coreFile = "${pkgs.libretro.bluemsx}/lib/retroarch/cores/bluemsx_libretro.so";
    systems = [
      "msx"
      "colecovision"
      "sg1000"
    ];
  };

  citra = {
    title = "Citra";
    description = "Runs Nintendo 3DS content with the Citra libretro core.";
    core = pkgs.libretro.citra;
    coreFile = "${pkgs.libretro.citra}/lib/retroarch/cores/citra_libretro.so";
    systems = [ "3ds" ];
  };

  desmume = {
    title = "DeSmuME";
    description = "Runs Nintendo DS content with the DeSmuME libretro core.";
    core = pkgs.libretro.desmume;
    coreFile = "${pkgs.libretro.desmume}/lib/retroarch/cores/desmume_libretro.so";
    systems = [ "nds" ];
  };

  desmume2015 = {
    title = "DeSmuME 2015";
    description = "Runs Nintendo DS content with the DeSmuME 2015 libretro core.";
    core = pkgs.libretro.desmume2015;
    coreFile = "${pkgs.libretro.desmume2015}/lib/retroarch/cores/desmume2015_libretro.so";
    systems = [ "nds" ];
  };

  dolphin = {
    title = "Dolphin";
    description = "Runs GameCube and Wii content with the Dolphin libretro core.";
    core = pkgs.libretro.dolphin;
    coreFile = "${pkgs.libretro.dolphin}/lib/retroarch/cores/dolphin_libretro.so";
    systems = [
      "gamecube"
      "wii"
    ];
  };

  dosbox = {
    title = "DOSBox";
    description = "Runs DOS content with the DOSBox libretro core.";
    core = pkgs.libretro.dosbox;
    coreFile = "${pkgs.libretro.dosbox}/lib/retroarch/cores/dosbox_libretro.so";
    systems = [ "dos" ];
  };

  dosbox-pure = {
    title = "DOSBox-pure";
    description = "Runs DOS content with the DOSBox-pure libretro core.";
    core = pkgs.libretro.dosbox-pure;
    coreFile = "${pkgs.libretro.dosbox-pure}/lib/retroarch/cores/dosbox_pure_libretro.so";
    systems = [ "dos" ];
  };

  easyrpg = {
    title = "EasyRPG Player";
    description = "Runs RPG Maker content with the EasyRPG Player libretro core.";
    core = pkgs.libretro.easyrpg;
    coreFile = "${pkgs.libretro.easyrpg}/lib/retroarch/cores/easyrpg_libretro.so";
    systems = [ "rpgmaker" ];
  };

  eightyone = {
    title = "81";
    description = "Runs ZX81 content with the 81 libretro core.";
    core = pkgs.libretro.eightyone;
    coreFile = "${pkgs.libretro.eightyone}/lib/retroarch/cores/81_libretro.so";
    systems = [ "zx81" ];
  };

  fbneo = {
    title = "FinalBurn Neo";
    description = "Runs Arcade content with the FinalBurn Neo libretro core.";
    core = pkgs.libretro.fbneo;
    coreFile = "${pkgs.libretro.fbneo}/lib/retroarch/cores/fbneo_libretro.so";
    systems = [ "arcade" ];
  };

  flycast = {
    title = "Flycast";
    description = "Runs Dreamcast content with the Flycast libretro core.";
    core = pkgs.libretro.flycast;
    coreFile = "${pkgs.libretro.flycast}/lib/retroarch/cores/flycast_libretro.so";
    systems = [ "dreamcast" ];
  };

  fmsx = {
    title = "fMSX";
    description = "Runs MSX content with the fMSX libretro core.";
    core = pkgs.libretro.fmsx;
    coreFile = "${pkgs.libretro.fmsx}/lib/retroarch/cores/fmsx_libretro.so";
    systems = [ "msx" ];
  };

  freeintv = {
    title = "FreeIntv";
    description = "Runs Intellivision content with the FreeIntv libretro core.";
    core = pkgs.libretro.freeintv;
    coreFile = "${pkgs.libretro.freeintv}/lib/retroarch/cores/freeintv_libretro.so";
    systems = [ "intellivision" ];
  };

  gw = {
    title = "GW";
    description = "Runs Game & Watch content with the GW libretro core.";
    core = pkgs.libretro.gw;
    coreFile = "${pkgs.libretro.gw}/lib/retroarch/cores/gw_libretro.so";
    systems = [ "gameandwatch" ];
  };

  handy = {
    title = "Handy";
    description = "Runs Lynx content with the Handy libretro core.";
    core = pkgs.libretro.handy;
    coreFile = "${pkgs.libretro.handy}/lib/retroarch/cores/handy_libretro.so";
    systems = [ "lynx" ];
  };

  hatari = {
    title = "hatari";
    description = "Runs Atari ST content with the hatari libretro core.";
    core = pkgs.libretro.hatari;
    coreFile = "${pkgs.libretro.hatari}/lib/retroarch/cores/hatari_libretro.so";
    systems = [ "atarist" ];
  };

  melonds = {
    title = "melonDS";
    description = "Runs Nintendo DS content with the melonDS libretro core.";
    core = pkgs.libretro.melonds;
    coreFile = "${pkgs.libretro.melonds}/lib/retroarch/cores/melonds_libretro.so";
    systems = [ "nds" ];
  };

  neocd = {
    title = "NeoCD";
    description = "Runs Neo Geo CD content with the NeoCD libretro core.";
    core = pkgs.libretro.neocd;
    coreFile = "${pkgs.libretro.neocd}/lib/retroarch/cores/neocd_libretro.so";
    systems = [ "ngcd" ];
  };

  opera = {
    title = "Opera";
    description = "Runs 3DO content with the Opera libretro core.";
    core = pkgs.libretro.opera;
    coreFile = "${pkgs.libretro.opera}/lib/retroarch/cores/opera_libretro.so";
    systems = [ "3do" ];
  };

  pcsx2 = {
    title = "LRPS2";
    description = "Runs PlayStation 2 content with the LRPS2 libretro core.";
    core = pkgs.libretro.pcsx2;
    coreFile = "${pkgs.libretro.pcsx2}/lib/retroarch/cores/pcsx2_libretro.so";
    systems = [ "ps2" ];
  };

  play = {
    title = "Play!";
    description = "Runs PlayStation 2 content with the Play! libretro core.";
    core = pkgs.libretro.play;
    coreFile = "${pkgs.libretro.play}/lib/retroarch/cores/play_libretro.so";
    systems = [ "ps2" ];
  };

  ppsspp = {
    title = "PPSSPP";
    description = "Runs PlayStation Portable content with the PPSSPP libretro core.";
    core = ppsspp;
    coreFile = "${ppsspp}/lib/retroarch/cores/ppsspp_libretro.so";
    systems = [ "psp" ];
  };

  prboom = {
    title = "PrBoom";
    description = "Runs Doom content with the PrBoom libretro core.";
    core = pkgs.libretro.prboom;
    coreFile = "${pkgs.libretro.prboom}/lib/retroarch/cores/prboom_libretro.so";
    systems = [ "doom" ];
  };

  prosystem = {
    title = "ProSystem";
    description = "Runs Atari 7800 content with the ProSystem libretro core.";
    core = pkgs.libretro.prosystem;
    coreFile = "${pkgs.libretro.prosystem}/lib/retroarch/cores/prosystem_libretro.so";
    systems = [ "atari7800" ];
  };

  puae = {
    title = "PUAE";
    description = "Runs Amiga content with the PUAE libretro core.";
    core = pkgs.libretro.puae;
    coreFile = "${pkgs.libretro.puae}/lib/retroarch/cores/puae_libretro.so";
    systems = [ "amiga" ];
  };

  same_cdi = {
    title = "SAME CDi (Git)";
    description = "Runs CD-i content with the SAME CDi (Git) libretro core.";
    core = pkgs.libretro.same_cdi;
    coreFile = "${pkgs.libretro.same_cdi}/lib/retroarch/cores/same_cdi_libretro.so";
    systems = [ "cdi" ];
  };

  scummvm = {
    title = "ScummVM";
    description = "Runs ScummVM content with the ScummVM libretro core.";
    core = pkgs.libretro.scummvm;
    coreFile = "${pkgs.libretro.scummvm}/lib/retroarch/cores/scummvm_libretro.so";
    systems = [ "scummvm" ];
  };

  thepowdertoy = {
    title = "ThePowderToy";
    description = "Runs The Powder Toy content with the ThePowderToy libretro core.";
    core = pkgs.libretro.thepowdertoy;
    coreFile = "${pkgs.libretro.thepowdertoy}/lib/retroarch/cores/thepowdertoy_libretro.so";
    systems = [ "powdertoy" ];
  };

  tic80 = {
    title = "TIC-80";
    description = "Runs TIC-80 content with the TIC-80 libretro core.";
    core = pkgs.libretro.tic80;
    coreFile = "${pkgs.libretro.tic80}/lib/retroarch/cores/tic80_libretro.so";
    systems = [ "tic80" ];
  };

  wasm4 = {
    title = "WASM-4";
    description = "Runs WASM-4 cartridges with its native libretro runtime.";
    core = wasm4;
    coreFile = "${wasm4}/lib/retroarch/cores/wasm4_libretro.so";
    systems = [ "wasm4" ];
  };

  lowresnx = {
    title = "LowRes NX";
    description = "Runs LowRes NX programs (virtual disk not supported).";
    core = lowresnx;
    coreFile = "${lowresnx}/lib/retroarch/cores/lowresnx_libretro.so";
    systems = [ "lowresnx" ];
  };

  pzretro = {
    title = "pzretro";
    description = "Runs original PuzzleScript source with embedded QuickJS.";
    core = pzretro;
    coreFile = "${pzretro}/lib/retroarch/cores/puzzlescript_libretro.so";
    systems = [ "puzzlescript" ];
  };

  vecx = {
    title = "vecx";
    description = "Runs Vectrex content with the vecx libretro core.";
    core = pkgs.libretro.vecx;
    coreFile = "${pkgs.libretro.vecx}/lib/retroarch/cores/vecx_libretro.so";
    systems = [ "vectrex" ];
  };

  vice-x128 = {
    title = "VICE x128";
    description = "Runs Commodore 128 content with the VICE x128 libretro core.";
    core = pkgs.libretro.vice-x128;
    coreFile = "${pkgs.libretro.vice-x128}/lib/retroarch/cores/vice_x128_libretro.so";
    systems = [ "c128" ];
  };

  vice-x64 = {
    title = "VICE x64";
    description = "Runs Commodore 64 content with the VICE x64 libretro core.";
    core = pkgs.libretro.vice-x64;
    coreFile = "${pkgs.libretro.vice-x64}/lib/retroarch/cores/vice_x64_libretro.so";
    systems = [ "c64" ];
  };

  vice-x64dtv = {
    title = "VICE x64dtv";
    description = "Runs Commodore 64 DTV content with the VICE x64dtv libretro core.";
    core = pkgs.libretro.vice-x64dtv;
    coreFile = "${pkgs.libretro.vice-x64dtv}/lib/retroarch/cores/vice_x64dtv_libretro.so";
    systems = [ "c64dtv" ];
  };

  vice-x64sc = {
    title = "VICE x64sc";
    description = "Runs Commodore 64 content with the VICE x64sc libretro core.";
    core = pkgs.libretro.vice-x64sc;
    coreFile = "${pkgs.libretro.vice-x64sc}/lib/retroarch/cores/vice_x64sc_libretro.so";
    systems = [ "c64" ];
  };

  vice-xcbm2 = {
    title = "VICE xcbm2";
    description = "Runs Commodore CBM-II content with the VICE xcbm2 libretro core.";
    core = pkgs.libretro.vice-xcbm2;
    coreFile = "${pkgs.libretro.vice-xcbm2}/lib/retroarch/cores/vice_xcbm2_libretro.so";
    systems = [ "cbm2" ];
  };

  vice-xcbm5x0 = {
    title = "VICE xcbm5x0";
    description = "Runs Commodore CBM-5x0 content with the VICE xcbm5x0 libretro core.";
    core = pkgs.libretro.vice-xcbm5x0;
    coreFile = "${pkgs.libretro.vice-xcbm5x0}/lib/retroarch/cores/vice_xcbm5x0_libretro.so";
    systems = [ "cbm5x0" ];
  };

  vice-xpet = {
    title = "VICE xpet";
    description = "Runs Commodore PET content with the VICE xpet libretro core.";
    core = pkgs.libretro.vice-xpet;
    coreFile = "${pkgs.libretro.vice-xpet}/lib/retroarch/cores/vice_xpet_libretro.so";
    systems = [ "pet" ];
  };

  vice-xplus4 = {
    title = "VICE xplus4";
    description = "Runs Commodore Plus/4 content with the VICE xplus4 libretro core.";
    core = pkgs.libretro.vice-xplus4;
    coreFile = "${pkgs.libretro.vice-xplus4}/lib/retroarch/cores/vice_xplus4_libretro.so";
    systems = [ "plus4" ];
  };

  vice-xscpu64 = {
    title = "VICE xscpu64";
    description = "Runs Commodore 64 SuperCPU content with the VICE xscpu64 libretro core.";
    core = pkgs.libretro.vice-xscpu64;
    coreFile = "${pkgs.libretro.vice-xscpu64}/lib/retroarch/cores/vice_xscpu64_libretro.so";
    systems = [ "c64supercpu" ];
  };

  vice-xvic = {
    title = "VICE xvic";
    description = "Runs Commodore VIC-20 content with the VICE xvic libretro core.";
    core = pkgs.libretro.vice-xvic;
    coreFile = "${pkgs.libretro.vice-xvic}/lib/retroarch/cores/vice_xvic_libretro.so";
    systems = [ "vic20" ];
  };

  virtualjaguar = {
    title = "Virtual Jaguar";
    description = "Runs Atari Jaguar content with the Virtual Jaguar libretro core.";
    core = pkgs.libretro.virtualjaguar;
    coreFile = "${pkgs.libretro.virtualjaguar}/lib/retroarch/cores/virtualjaguar_libretro.so";
    systems = [ "jaguar" ];
  };

  yabause = {
    title = "Yabause";
    description = "Runs Sega Saturn content with the Yabause libretro core.";
    core = pkgs.libretro.yabause;
    coreFile = "${pkgs.libretro.yabause}/lib/retroarch/cores/yabause_libretro.so";
    systems = [ "saturn" ];
  };

  beetle-gba = {
    title = "Beetle GBA";
    description = "Runs Game Boy Advance content with the Beetle GBA libretro core.";
    core = pkgs.libretro.beetle-gba;
    coreFile = "${pkgs.libretro.beetle-gba}/lib/retroarch/cores/mednafen_gba_libretro.so";
    systems = [ "gba" ];
  };

  beetle-pce = {
    title = "Beetle PCE";
    description = "Runs PC Engine, SuperGrafx and PC Engine CD content with the Beetle PCE libretro core.";
    core = pkgs.libretro.beetle-pce;
    coreFile = "${pkgs.libretro.beetle-pce}/lib/retroarch/cores/mednafen_pce_libretro.so";
    systems = [
      "pce"
      "supergrafx"
      "pcecd"
    ];
  };

  beetle-psx = {
    title = "Beetle PSX";
    description = "Runs PlayStation content with the Beetle PSX libretro core.";
    core = pkgs.libretro.beetle-psx;
    coreFile = "${pkgs.libretro.beetle-psx}/lib/retroarch/cores/mednafen_psx_libretro.so";
    systems = [ "psx" ];
  };

  beetle-psx-hw = {
    title = "Beetle PSX HW";
    description = "Runs PlayStation content with the Beetle PSX HW libretro core.";
    core = pkgs.libretro.beetle-psx-hw;
    coreFile = "${pkgs.libretro.beetle-psx-hw}/lib/retroarch/cores/mednafen_psx_hw_libretro.so";
    systems = [ "psx" ];
  };

  beetle-supafaust = {
    title = "Beetle Supafaust";
    description = "Runs Super Nintendo content with the Beetle Supafaust libretro core.";
    core = pkgs.libretro.beetle-supafaust;
    coreFile = "${pkgs.libretro.beetle-supafaust}/lib/retroarch/cores/mednafen_supafaust_libretro.so";
    systems = [ "snes" ];
  };

  beetle-supergrafx = {
    title = "Beetle SuperGrafx";
    description = "Runs SuperGrafx content with the Beetle SuperGrafx libretro core.";
    core = pkgs.libretro.beetle-supergrafx;
    coreFile = "${pkgs.libretro.beetle-supergrafx}/lib/retroarch/cores/mednafen_supergrafx_libretro.so";
    systems = [ "supergrafx" ];
  };

  blastem = {
    title = "BlastEm";
    description = "Runs Mega Drive, Sega 32X, Master System, Game Gear, SG-1000 and ColecoVision content with the BlastEm libretro core.";
    core = pkgs.libretro.blastem;
    coreFile = "${pkgs.libretro.blastem}/lib/retroarch/cores/blastem_libretro.so";
    systems = [
      "md"
      "sega32x"
      "sms"
      "gg"
      "sg1000"
      "colecovision"
    ];
  };

  bsnes-hd = {
    title = "bsnes-hd beta";
    description = "Runs Super Nintendo content with the bsnes-hd beta libretro core.";
    core = pkgs.libretro.bsnes-hd;
    coreFile = "${pkgs.libretro.bsnes-hd}/lib/retroarch/cores/bsnes_hd_beta_libretro.so";
    systems = [ "snes" ];
  };

  bsnes-mercury = {
    title = "bsnes-mercury Accuracy";
    description = "Runs Super Nintendo content with the bsnes-mercury Accuracy libretro core.";
    core = pkgs.libretro.bsnes-mercury;
    coreFile = "${pkgs.libretro.bsnes-mercury}/lib/retroarch/cores/bsnes_mercury_accuracy_libretro.so";
    systems = [ "snes" ];
  };

  bsnes-mercury-balanced = {
    title = "bsnes-mercury Balanced";
    description = "Runs Super Nintendo content with the bsnes-mercury Balanced libretro core.";
    core = pkgs.libretro.bsnes-mercury-balanced;
    coreFile = "${pkgs.libretro.bsnes-mercury-balanced}/lib/retroarch/cores/bsnes_mercury_balanced_libretro.so";
    systems = [ "snes" ];
  };

  bsnes-mercury-performance = {
    title = "bsnes-mercury Performance";
    description = "Runs Super Nintendo content with the bsnes-mercury Performance libretro core.";
    core = pkgs.libretro.bsnes-mercury-performance;
    coreFile = "${pkgs.libretro.bsnes-mercury-performance}/lib/retroarch/cores/bsnes_mercury_performance_libretro.so";
    systems = [ "snes" ];
  };

  gpsp = {
    title = "gpSP";
    description = "Runs Game Boy Advance content with the gpSP libretro core.";
    core = pkgs.libretro.gpsp;
    coreFile = "${pkgs.libretro.gpsp}/lib/retroarch/cores/gpsp_libretro.so";
    systems = [ "gba" ];
  };

  meteor = {
    title = "Meteor";
    description = "Runs Game Boy Advance content with the Meteor libretro core.";
    core = pkgs.libretro.meteor;
    coreFile = "${pkgs.libretro.meteor}/lib/retroarch/cores/meteor_libretro.so";
    systems = [ "gba" ];
  };

  nestopia = {
    title = "Nestopia";
    description = "Runs Nintendo Entertainment System content with the Nestopia libretro core.";
    core = pkgs.libretro.nestopia;
    coreFile = "${pkgs.libretro.nestopia}/lib/retroarch/cores/nestopia_libretro.so";
    systems = [
      "nes"
      "fds"
    ];
  };

  parallel-n64 = {
    title = "ParaLLEl N64";
    description = "Runs Nintendo 64 content with the ParaLLEl N64 libretro core.";
    core = pkgs.libretro.parallel-n64;
    coreFile = "${pkgs.libretro.parallel-n64}/lib/retroarch/cores/parallel_n64_libretro.so";
    systems = [ "n64" ];
  };

  quicknes = {
    title = "QuickNES";
    description = "Runs Nintendo Entertainment System content with the QuickNES libretro core.";
    core = pkgs.libretro.quicknes;
    coreFile = "${pkgs.libretro.quicknes}/lib/retroarch/cores/quicknes_libretro.so";
    systems = [ "nes" ];
  };

  sameboy = {
    title = "SameBoy";
    description = "Runs Game Boy and Game Boy Color content with the SameBoy libretro core.";
    core = pkgs.libretro.sameboy;
    coreFile = "${pkgs.libretro.sameboy}/lib/retroarch/cores/sameboy_libretro.so";
    systems = [
      "gb"
      "gbc"
    ];
  };

  smsplus-gx = {
    title = "SMS Plus GX";
    description = "Runs Master System and Game Gear content with the SMS Plus GX libretro core.";
    core = pkgs.libretro.smsplus-gx;
    coreFile = "${pkgs.libretro.smsplus-gx}/lib/retroarch/cores/smsplus_libretro.so";
    systems = [
      "sms"
      "gg"
    ];
  };

  snes9x = {
    title = "Snes9x";
    description = "Runs Super Nintendo content with the Snes9x libretro core.";
    core = pkgs.libretro.snes9x;
    coreFile = "${pkgs.libretro.snes9x}/lib/retroarch/cores/snes9x_libretro.so";
    systems = [ "snes" ];
  };

  snes9x2002 = {
    title = "Snes9x 2002";
    description = "Runs Super Nintendo content with the Snes9x 2002 libretro core.";
    core = pkgs.libretro.snes9x2002;
    coreFile = "${pkgs.libretro.snes9x2002}/lib/retroarch/cores/snes9x2002_libretro.so";
    systems = [ "snes" ];
  };

  snes9x2005 = {
    title = "Snes9x 2005";
    description = "Runs Super Nintendo content with the Snes9x 2005 libretro core.";
    core = pkgs.libretro.snes9x2005;
    coreFile = "${pkgs.libretro.snes9x2005}/lib/retroarch/cores/snes9x2005_libretro.so";
    systems = [ "snes" ];
  };

  snes9x2005-plus = {
    title = "Snes9x 2005 Plus";
    description = "Runs Super Nintendo content with the Snes9x 2005 Plus libretro core.";
    core = pkgs.libretro.snes9x2005-plus;
    coreFile = "${pkgs.libretro.snes9x2005-plus}/lib/retroarch/cores/snes9x2005_plus_libretro.so";
    systems = [ "snes" ];
  };

  stella2014 = {
    title = "Stella 2014";
    description = "Runs Atari 2600 content with the Stella 2014 libretro core.";
    core = pkgs.libretro.stella2014;
    coreFile = "${pkgs.libretro.stella2014}/lib/retroarch/cores/stella2014_libretro.so";
    systems = [ "atari2600" ];
  };

  swanstation = {
    title = "SwanStation";
    description = "Runs PlayStation content with the SwanStation libretro core.";
    core = pkgs.libretro.swanstation;
    coreFile = "${pkgs.libretro.swanstation}/lib/retroarch/cores/swanstation_libretro.so";
    systems = [ "psx" ];
  };

  tgbdual = {
    title = "TGB Dual";
    description = "Runs Game Boy and Game Boy Color content with the TGB Dual libretro core.";
    core = pkgs.libretro.tgbdual;
    coreFile = "${pkgs.libretro.tgbdual}/lib/retroarch/cores/tgbdual_libretro.so";
    systems = [
      "gb"
      "gbc"
    ];
  };

  vba-m = {
    title = "VBA-M";
    description = "Runs Game Boy Advance, Game Boy and Game Boy Color content with the VBA-M libretro core.";
    core = pkgs.libretro.vba-m;
    coreFile = "${pkgs.libretro.vba-m}/lib/retroarch/cores/vbam_libretro.so";
    systems = [
      "gba"
      "gb"
      "gbc"
    ];
  };

  vba-next = {
    title = "VBA Next";
    description = "Runs Game Boy Advance content with the VBA Next libretro core.";
    core = pkgs.libretro.vba-next;
    coreFile = "${pkgs.libretro.vba-next}/lib/retroarch/cores/vba_next_libretro.so";
    systems = [ "gba" ];
  };
}
