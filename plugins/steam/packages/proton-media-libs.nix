# The libraries Proton's own media files load by soname and a NixOS FHS does
# not have (korri#594, found on aka 2026-11-24). Proton-CachyOS is built for
# Valve's Steam Linux Runtime, which provides them; the engine runner starts
# Proton with no runtime container. Wine's media backend (winedmo.so) and
# Proton's bundled FFmpeg and GStreamer plugins need:
#   libvdpau.so.1                  as in nixpkgs
#   libbz2.so.1.0                  nixpkgs' bzip2 under Debian's file name
#   libvpx.so.9                    libvpx 1.14; nixpkgs has 1.17 (libvpx.so.12)
#   libtheoradec.so.1, libtheoraenc.so.1
#                                  libtheora 1.1; nixpkgs has 1.2 (.so.2)
# Without them winedmo.so does not load, a game's video does not play, and a
# game that opens with a video stays black (Your Average Bear, BalanCity).
# The older two are built from their own releases, never renamed copies: the
# newer ABIs differ.
p: [
  # bzip2: Proton's files ask for the file name libbz2.so.1.0, as Debian
  # names the library. nixpkgs' library has the soname libbz2.so.1, and the
  # FHS loader finds libraries by soname through its cache, so that file name
  # in /usr/lib did not help (seen on aka: "libbz2.so.1.0: cannot open shared
  # object file" with the file there). The session program puts this folder
  # on LD_LIBRARY_PATH, where the loader looks by file name. It holds this
  # one library, so nothing else changes its search order.
  (p.runCommand "korri-proton-compat-libs" { } ''
    mkdir -p "$out/lib/korri-proton-compat"
    ln -s ${p.bzip2.out}/lib/libbz2.so.1.0.8 "$out/lib/korri-proton-compat/libbz2.so.1.0"
  '')
  p.libvdpau
  (p.libvpx.overrideAttrs (_: {
    version = "1.14.1";
    src = p.fetchFromGitHub {
      owner = "webmproject";
      repo = "libvpx";
      rev = "v1.14.1";
      hash = "sha256-Pfg7g4y/dqn2VKDQU1LnTJQSj1Tont9/8Je6ShDb2GQ=";
    };
    patches = [ ];
  }))
  (p.libtheora.overrideAttrs (old: {
    version = "1.1.1";
    src = p.fetchurl {
      url = "https://downloads.xiph.org/releases/theora/libtheora-1.1.1.tar.bz2";
      hash = "sha256-tq4e4vo9QqxIkofT7DTFiFcwsSlvCAGuV3o1GT06/7w=";
    };
    patches = [ ];
    # The release tarball ships its configure script; its configure.ac does
    # not regenerate with a current autoconf.
    nativeBuildInputs = builtins.filter (
      input: (input.name or "") != (p.autoreconfHook.name or "autoreconf-hook")
    ) (old.nativeBuildInputs or [ ]);
    configureFlags = (old.configureFlags or [ ]) ++ [
      "--disable-examples"
      "--disable-spec"
    ];
  }))
]
