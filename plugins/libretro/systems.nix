# One content definition per system, shared by every core that runs it.
# Extension lists are the union of the former per-core catalogue lists.
# Pairing scopes generic suffixes such as Mega Drive md to real content.
# Lynx o object files are not content. General archive suffixes are excluded.
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
    content = {
      extensions = [
        "cue"
        "ccd"
      ];
    };
  };

  atari2600 = {
    title = "Atari 2600";
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
    content = {
      extensions = [ "32x" ];
    };
  };

  sg1000 = {
    title = "SG-1000";
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
    content = {
      extensions = [ "sms" ];
    };
  };

  snes = {
    title = "Super Nintendo";
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
