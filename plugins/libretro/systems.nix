# One content definition per system, shared by every core that runs it.
# Extension lists are the union of the former per-core catalogue lists.
# Pairing scopes generic suffixes such as Mega Drive md to real content.
# Lynx o object files are not content. General archive suffixes are excluded.
# `externalIds` are the system's public ids (Core ADR 0090), each one checked
# against its authority's site on 2026-11-20; README "Public ids" names the
# sources. An authority with no checked id is left out.
{
  "3do" = {
    title = "3DO";
    content = {
      extensions = [
        "chd"
        "cue"
      ];
    };
  };

  "3ds" = {
    title = "Nintendo 3DS";
    content = {
      extensions = [
        "3ds"
        "3dsx"
        "axf"
        "cci"
        "cxi"
      ];
    };
  };

  amiga = {
    title = "Amiga";
    content = {
      extensions = [
        "adf"
        "adz"
        "dms"
        "fdi"
        "ipf"
        "hdf"
        "hdz"
        "lha"
        "slave"
        "info"
        "uae"
        "rp9"
      ];
    };
  };

  arcade = {
    title = "Arcade";
    externalIds = {
      wikidata = [ "Q192851" ];
      igdb = [ "52" ];
      mobygames = [ "arcade" ];
      thegamesdb = [ "23" ];
      screenscraper = [ "75" ];
      retroachievements = [ "27" ];
    };
    content = {
      extensions = [
        "cue"
        "ccd"
      ];
    };
  };

  atari2600 = {
    title = "Atari 2600";
    externalIds = {
      wikidata = [ "Q206261" ];
      igdb = [ "59" ];
      mobygames = [ "atari-2600" ];
      thegamesdb = [ "22" ];
      screenscraper = [ "26" ];
      retroachievements = [ "25" ];
      "no-intro" = [ "Atari - 2600" ];
    };
    content = {
      extensions = [ "a26" ];
    };
  };

  atari5200 = {
    title = "Atari 5200";
    content = {
      extensions = [ "a52" ];
    };
  };

  atari7800 = {
    title = "Atari 7800";
    externalIds = {
      wikidata = [ "Q753600" ];
      igdb = [ "60" ];
      mobygames = [ "atari-7800" ];
      thegamesdb = [ "27" ];
      screenscraper = [ "41" ];
      retroachievements = [ "51" ];
      "no-intro" = [ "Atari - 7800" ];
    };
    content = {
      extensions = [
        "a78"
        "cdf"
      ];
      # clrmamepro header detectors (a7800.xml):
      # https://mamedev.emulab.it/clrmamepro/docs/xmlheaders.txt
      evidence.bytes = [
        {
          offset = 1;
          hex = "415441524937383030";
        }
      ];
      header = [
        {
          size = 128;
          bytes = {
            offset = 1;
            hex = "415441524937383030";
          };
        }
      ];
    };
  };

  atari8bit = {
    title = "Atari 8-bit";
    content = {
      extensions = [
        "xfd"
        "atr"
        "dcm"
        "cas"
        "atx"
        "car"
        "xex"
      ];
    };
  };

  atarist = {
    title = "Atari ST";
    content = {
      extensions = [
        "st"
        "msa"
        "stx"
        "dim"
        "ipf"
        "gem"
        "ide"
      ];
    };
  };

  c128 = {
    title = "Commodore 128";
    content = {
      extensions = [
        "d64"
        "d71"
        "d80"
        "d81"
        "d82"
        "g64"
        "g41"
        "x64"
        "t64"
        "tap"
        "prg"
        "p00"
        "crt"
        "vfl"
        "vsf"
        "nib"
        "d2m"
        "d4m"
      ];
    };
  };

  c64 = {
    title = "Commodore 64";
    content = {
      extensions = [
        "d64"
        "d71"
        "d80"
        "d81"
        "d82"
        "g64"
        "g41"
        "x64"
        "t64"
        "tap"
        "prg"
        "p00"
        "crt"
        "vfl"
        "vsf"
        "nib"
        "d2m"
        "d4m"
      ];
    };
  };

  c64dtv = {
    title = "Commodore 64 DTV";
    content = {
      extensions = [
        "d64"
        "d71"
        "d80"
        "d81"
        "d82"
        "g64"
        "g41"
        "x64"
        "t64"
        "tap"
        "prg"
        "p00"
        "crt"
        "vfl"
        "vsf"
        "nib"
        "d2m"
        "d4m"
      ];
    };
  };

  c64supercpu = {
    title = "Commodore 64 SuperCPU";
    content = {
      extensions = [
        "d64"
        "d71"
        "d80"
        "d81"
        "d82"
        "g64"
        "g41"
        "x64"
        "t64"
        "tap"
        "prg"
        "p00"
        "crt"
        "vfl"
        "vsf"
        "nib"
        "d2m"
        "d4m"
      ];
    };
  };

  cbm2 = {
    title = "Commodore CBM-II";
    content = {
      extensions = [
        "d64"
        "d71"
        "d80"
        "d81"
        "d82"
        "g64"
        "g41"
        "x64"
        "t64"
        "tap"
        "prg"
        "p00"
        "crt"
        "vfl"
        "vsf"
        "nib"
        "d2m"
        "d4m"
      ];
    };
  };

  cbm5x0 = {
    title = "Commodore CBM-5x0";
    content = {
      extensions = [
        "d64"
        "d71"
        "d80"
        "d81"
        "d82"
        "g64"
        "g41"
        "x64"
        "t64"
        "tap"
        "prg"
        "p00"
        "crt"
        "vfl"
        "vsf"
        "nib"
        "d2m"
        "d4m"
      ];
    };
  };

  cdi = {
    title = "CD-i";
    content = {
      extensions = [
        "chd"
        "cue"
      ];
    };
  };

  colecovision = {
    title = "ColecoVision";
    content = {
      extensions = [ "col" ];
    };
  };

  doom = {
    title = "Doom";
    content = {
      extensions = [
        "wad"
        "iwad"
        "pwad"
        "pk3"
      ];
    };
  };

  dos = {
    title = "DOS";
    content = {
      extensions = [
        "bat"
        "conf"
        "dosz"
        "chd"
        "cue"
        "ins"
        "ima"
        "vhd"
        "jrc"
        "tc"
      ];
    };
  };

  dreamcast = {
    title = "Dreamcast";
    externalIds = {
      wikidata = [ "Q184198" ];
      igdb = [ "23" ];
      mobygames = [ "dreamcast" ];
      thegamesdb = [ "16" ];
      screenscraper = [ "23" ];
      retroachievements = [ "40" ];
    };
    content = {
      extensions = [
        "chd"
        "cdi"
        "cue"
        "gdi"
      ];
    };
  };

  fds = {
    title = "Famicom Disk System";
    externalIds = {
      wikidata = [ "Q135321" ];
      igdb = [ "51" ];
      thegamesdb = [ "4936" ];
      screenscraper = [ "106" ];
      retroachievements = [ "81" ];
      "no-intro" = [ "Nintendo - Family Computer Disk System" ];
    };
    content = {
      extensions = [ "fds" ];
      # clrmamepro header detectors (fds.xml):
      # https://mamedev.emulab.it/clrmamepro/docs/xmlheaders.txt
      evidence.bytes = [
        {
          offset = 0;
          hex = "4644531a";
        }
      ];
      header = [
        {
          size = 16;
          bytes = {
            offset = 0;
            hex = "4644531a";
          };
        }
      ];
    };
  };

  gameandwatch = {
    title = "Game & Watch";
    externalIds = {
      wikidata = [ "Q215034" ];
      igdb = [ "307" ];
      thegamesdb = [ "4950" ];
      screenscraper = [ "52" ];
      retroachievements = [ "60" ];
      "no-intro" = [ "Nintendo - Game & Watch" ];
    };
    content = {
      extensions = [ "mgw" ];
    };
  };

  gamecube = {
    title = "GameCube";
    content = {
      extensions = [ "gcm" ];
    };
  };

  gb = {
    title = "Game Boy";
    externalIds = {
      wikidata = [ "Q186437" ];
      igdb = [ "33" ];
      mobygames = [ "gameboy" ];
      thegamesdb = [ "4" ];
      screenscraper = [ "9" ];
      retroachievements = [ "4" ];
      "no-intro" = [ "Nintendo - Game Boy" ];
    };
    content = {
      extensions = [
        "gb"
        "dmg"
        "sgb"
      ];
    };
  };

  gba = {
    title = "Game Boy Advance";
    externalIds = {
      wikidata = [ "Q188642" ];
      igdb = [ "24" ];
      mobygames = [ "gameboy-advance" ];
      thegamesdb = [ "5" ];
      screenscraper = [ "12" ];
      retroachievements = [ "5" ];
      "no-intro" = [ "Nintendo - Game Boy Advance" ];
    };
    content = {
      extensions = [
        "gba"
        "agb"
      ];
      # First 16 bytes of the Nintendo logo at 004h in the GBA ROM header:
      # https://problemkaputt.de/gbatek.htm#gbacartridgeheader
      evidence.bytes = [
        {
          offset = 4;
          hex = "24ffae51699aa2213d84820a84e409ad";
        }
      ];
    };
  };

  gbc = {
    title = "Game Boy Color";
    externalIds = {
      wikidata = [ "Q203992" ];
      igdb = [ "22" ];
      mobygames = [ "gameboy-color" ];
      thegamesdb = [ "41" ];
      screenscraper = [ "10" ];
      retroachievements = [ "6" ];
      "no-intro" = [ "Nintendo - Game Boy Color" ];
    };
    content = {
      extensions = [
        "gbc"
        "cgb"
        "sgb"
      ];
    };
  };

  gg = {
    title = "Game Gear";
    externalIds = {
      wikidata = [ "Q751719" ];
      igdb = [ "35" ];
      mobygames = [ "game-gear" ];
      thegamesdb = [ "20" ];
      screenscraper = [ "21" ];
      retroachievements = [ "15" ];
      "no-intro" = [ "Sega - Game Gear" ];
    };
    content = {
      extensions = [ "gg" ];
    };
  };

  intellivision = {
    title = "Intellivision";
    content = {
      extensions = [ "int" ];
    };
  };

  jaguar = {
    title = "Atari Jaguar";
    content = {
      extensions = [
        "j64"
        "jag"
        "abs"
        "cof"
        "prg"
        "cue"
        "cdi"
        "chd"
      ];
    };
  };

  lynx = {
    title = "Lynx";
    externalIds = {
      wikidata = [ "Q753657" ];
      igdb = [ "61" ];
      mobygames = [ "lynx" ];
      thegamesdb = [ "4924" ];
      screenscraper = [ "28" ];
      retroachievements = [ "13" ];
      "no-intro" = [ "Atari - Lynx" ];
    };
    content = {
      extensions = [
        "lnx"
        "lyx"
        "bll"
      ];
      # clrmamepro header detectors (lynx.xml):
      # https://mamedev.emulab.it/clrmamepro/docs/xmlheaders.txt
      evidence.bytes = [
        {
          offset = 0;
          hex = "4c594e58";
        }
        {
          offset = 6;
          hex = "425339";
        }
      ];
      header = [
        {
          size = 64;
          bytes = {
            offset = 0;
            hex = "4c594e58";
          };
        }
        {
          size = 64;
          bytes = {
            offset = 6;
            hex = "425339";
          };
        }
      ];
    };
  };

  md = {
    title = "Mega Drive";
    externalIds = {
      wikidata = [ "Q10676" ];
      igdb = [ "29" ];
      mobygames = [ "genesis" ];
      thegamesdb = [ "18" "36" ];
      screenscraper = [ "1" ];
      retroachievements = [ "1" ];
      "no-intro" = [ "Sega - Mega Drive - Genesis" ];
    };
    content = {
      extensions = [
        "md"
        "gen"
        "smd"
        "68k"
        "sgd"
      ];
    };
  };

  msx = {
    title = "MSX";
    content = {
      extensions = [
        "mx1"
        "mx2"
        "dsk"
        "cas"
        "ri"
        "fdi"
      ];
    };
  };

  n64 = {
    title = "Nintendo 64";
    externalIds = {
      wikidata = [ "Q184839" ];
      igdb = [ "4" ];
      mobygames = [ "n64" ];
      thegamesdb = [ "3" ];
      screenscraper = [ "14" ];
      retroachievements = [ "2" ];
      "no-intro" = [ "Nintendo - Nintendo 64" ];
    };
    content = {
      extensions = [
        "z64"
        "n64"
        "v64"
        "ndd"
      ];
    };
  };

  nds = {
    title = "Nintendo DS";
    externalIds = {
      wikidata = [ "Q170323" ];
      igdb = [ "20" ];
      mobygames = [ "nintendo-ds" ];
      thegamesdb = [ "8" ];
      screenscraper = [ "15" ];
      retroachievements = [ "18" ];
      "no-intro" = [ "Nintendo - Nintendo DS" ];
    };
    panes = [
      "upper"
      "lower"
    ];
    arrangement = "upper-above-lower";
    content = {
      extensions = [
        "nds"
        "ids"
        "dsi"
      ];
    };
  };

  nes = {
    title = "Nintendo Entertainment System";
    externalIds = {
      wikidata = [ "Q172742" ];
      igdb = [ "18" "99" ];
      mobygames = [ "nes" ];
      thegamesdb = [ "7" ];
      screenscraper = [ "3" ];
      retroachievements = [ "7" ];
      "no-intro" = [ "Nintendo - Nintendo Entertainment System" ];
    };
    content = {
      extensions = [ "nes" ];
      # clrmamepro header detectors (nes.xml):
      # https://mamedev.emulab.it/clrmamepro/docs/xmlheaders.txt
      evidence.bytes = [
        {
          offset = 0;
          hex = "4e45531a";
        }
      ];
      header = [
        {
          size = 16;
          bytes = {
            offset = 0;
            hex = "4e45531a";
          };
        }
      ];
    };
  };

  ngcd = {
    title = "Neo Geo CD";
    content = {
      extensions = [
        "cue"
        "chd"
      ];
    };
  };

  ngp = {
    title = "Neo Geo Pocket";
    externalIds = {
      wikidata = [ "Q939881" "Q1977455" ];
      igdb = [ "119" "120" ];
      mobygames = [ "neo-geo-pocket" "neo-geo-pocket-color" ];
      thegamesdb = [ "4922" "4923" ];
      screenscraper = [ "25" "82" ];
      retroachievements = [ "14" ];
      "no-intro" = [ "SNK - NeoGeo Pocket" "SNK - NeoGeo Pocket Color" ];
    };
    content = {
      extensions = [
        "ngp"
        "ngc"
        "ngpc"
        "npc"
      ];
    };
  };

  pc98 = {
    title = "PC-98";
    content = {
      extensions = [
        "d88"
        "fdi"
        "hdi"
        "hdm"
        "nhd"
        "xdf"
      ];
    };
  };

  pce = {
    title = "PC Engine";
    externalIds = {
      wikidata = [ "Q1057377" ];
      igdb = [ "86" ];
      mobygames = [ "turbo-grafx" ];
      thegamesdb = [ "34" ];
      screenscraper = [ "31" ];
      retroachievements = [ "8" ];
      "no-intro" = [ "NEC - PC Engine - TurboGrafx-16" ];
    };
    content = {
      extensions = [ "pce" ];
    };
  };

  pcecd = {
    title = "PC Engine CD";
    content = {
      extensions = [
        "cue"
        "ccd"
        "chd"
        "toc"
      ];
    };
  };

  pcfx = {
    title = "PC-FX";
    content = {
      extensions = [
        "cue"
        "ccd"
        "toc"
        "chd"
      ];
    };
  };

  pet = {
    title = "Commodore PET";
    content = {
      extensions = [
        "d64"
        "d71"
        "d80"
        "d81"
        "d82"
        "g64"
        "g41"
        "x64"
        "t64"
        "tap"
        "prg"
        "p00"
        "crt"
        "vfl"
        "vsf"
        "nib"
        "d2m"
        "d4m"
      ];
    };
  };

  pico8 = {
    title = "PICO-8";
    externalIds = {
      wikidata = [ "Q28456260" ];
      screenscraper = [ "234" ];
    };
    content = {
      # Upstream accepts png, but only compound cartridge PNGs belong here.
      extensions = [
        "p8"
        "p8.png"
      ];
    };
  };

  plus4 = {
    title = "Commodore Plus/4";
    content = {
      extensions = [
        "d64"
        "d71"
        "d80"
        "d81"
        "d82"
        "g64"
        "g41"
        "x64"
        "t64"
        "tap"
        "prg"
        "p00"
        "crt"
        "vfl"
        "vsf"
        "nib"
        "d2m"
        "d4m"
      ];
    };
  };

  powdertoy = {
    title = "The Powder Toy";
    content = {
      extensions = [ "cps" ];
    };
  };

  ps2 = {
    title = "PlayStation 2";
    content = {
      extensions = [
        "ciso"
        "cue"
        "chd"
      ];
    };
  };

  psp = {
    title = "PlayStation Portable";
    content = {
      extensions = [
        "prx"
        "pbp"
        "chd"
      ];
    };
  };

  psx = {
    title = "PlayStation";
    externalIds = {
      wikidata = [ "Q10677" ];
      igdb = [ "7" ];
      mobygames = [ "playstation" ];
      thegamesdb = [ "10" ];
      screenscraper = [ "57" ];
      retroachievements = [ "12" ];
    };
    content = {
      extensions = [
        "cue"
        "chd"
        "m3u"
        "pbp"
        "ccd"
        "toc"
        "psexe"
        "mds"
        "psf"
      ];
    };
  };

  rpgmaker = {
    title = "RPG Maker";
    content = {
      extensions = [
        "ldb"
        "lzh"
        "easyrpg"
      ];
    };
  };

  saturn = {
    title = "Sega Saturn";
    content = {
      extensions = [
        "ccd"
        "chd"
        "cue"
        "toc"
        "mds"
      ];
    };
  };

  scummvm = {
    title = "ScummVM";
    content = {
      extensions = [ "scummvm" ];
    };
  };

  sega32x = {
    title = "Sega 32X";
    externalIds = {
      wikidata = [ "Q1063978" ];
      igdb = [ "30" ];
      mobygames = [ "sega-32x" ];
      thegamesdb = [ "33" ];
      screenscraper = [ "19" ];
      retroachievements = [ "10" ];
      "no-intro" = [ "Sega - 32X" ];
    };
    content = {
      extensions = [ "32x" ];
    };
  };

  sg1000 = {
    title = "SG-1000";
    externalIds = {
      wikidata = [ "Q1136956" ];
      igdb = [ "84" ];
      mobygames = [ "sg-1000" ];
      thegamesdb = [ "4949" ];
      screenscraper = [ "109" ];
      retroachievements = [ "33" ];
      "no-intro" = [ "Sega - SG-1000" ];
    };
    content = {
      extensions = [
        "sg"
        "sc"
        "sf"
        "sg1"
        "sc3"
        "sf7"
      ];
    };
  };

  sms = {
    title = "Master System";
    externalIds = {
      wikidata = [ "Q209868" ];
      igdb = [ "64" ];
      mobygames = [ "sega-master-system" ];
      thegamesdb = [ "35" ];
      screenscraper = [ "2" ];
      retroachievements = [ "11" ];
      "no-intro" = [ "Sega - Master System - Mark III" ];
    };
    content = {
      extensions = [ "sms" ];
    };
  };

  snes = {
    title = "Super Nintendo";
    externalIds = {
      wikidata = [ "Q183259" ];
      igdb = [ "19" "58" ];
      mobygames = [ "snes" ];
      thegamesdb = [ "6" ];
      screenscraper = [ "4" ];
      retroachievements = [ "3" ];
      "no-intro" = [ "Nintendo - Super Nintendo Entertainment System" ];
    };
    content = {
      extensions = [
        "sfc"
        "smc"
        "swc"
        "gd3"
        "gd7"
        "dx2"
        "bsx"
        "fig"
        "bs"
        "bml"
        "st"
      ];
      # clrmamepro header detectors (snes.xml):
      # https://mamedev.emulab.it/clrmamepro/docs/xmlheaders.txt
      header = [
        {
          size = 512;
          remainder = {
            divisor = 1024;
            value = 512;
          };
        }
      ];
    };
  };

  supergrafx = {
    title = "SuperGrafx";
    content = {
      extensions = [ "sgx" ];
    };
  };

  wasm4 = {
    title = "WASM-4";
    content.extensions = [ "wasm" ];
  };

  lowresnx = {
    title = "LowRes NX";
    content.extensions = [ "nx" ];
  };

  puzzlescript = {
    title = "PuzzleScript";
    content.extensions = [ "pz" ];
  };

  tic80 = {
    title = "TIC-80";
    content = {
      extensions = [ "tic" ];
    };
  };

  vb = {
    title = "Virtual Boy";
    content = {
      extensions = [
        "vb"
        "vboy"
      ];
    };
  };

  vectrex = {
    title = "Vectrex";
    content = {
      extensions = [ "vec" ];
    };
  };

  vic20 = {
    title = "Commodore VIC-20";
    content = {
      extensions = [
        "d64"
        "d71"
        "d80"
        "d81"
        "d82"
        "g64"
        "g41"
        "x64"
        "t64"
        "tap"
        "prg"
        "p00"
        "crt"
        "vfl"
        "vsf"
        "nib"
        "d2m"
        "d4m"
        "20"
        "40"
        "60"
        "a0"
        "b0"
      ];
    };
  };

  wii = {
    title = "Wii";
    content = {
      extensions = [
        "wbfs"
        "wad"
        "rvz"
        "wia"
      ];
    };
  };

  wswan = {
    title = "WonderSwan";
    externalIds = {
      wikidata = [ "Q1065792" "Q1048035" ];
      igdb = [ "57" "123" ];
      mobygames = [ "wonderswan" "wonderswan-color" ];
      thegamesdb = [ "4925" "4926" ];
      screenscraper = [ "45" "46" ];
      retroachievements = [ "53" ];
      "no-intro" = [ "Bandai - WonderSwan" "Bandai - WonderSwan Color" ];
    };
    content = {
      extensions = [
        "ws"
        "wsc"
        "pc2"
        "pcv2"
      ];
    };
  };

  zx81 = {
    title = "ZX81";
    content = {
      extensions = [
        "p"
        "tzx"
        "t81"
      ];
    };
  };

  zxspectrum = {
    title = "ZX Spectrum";
    content = {
      extensions = [
        "z80"
        "sna"
        "tap"
        "tzx"
        "szx"
      ];
    };
  };

}
