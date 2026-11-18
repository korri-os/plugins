# korri-steam-host from its Rust source and one engine map (ADR 0083).
# `engineMap` is a folder that holds engine.map: the public empty map, or the
# private map of the pinned engine (flake input `steam-engine-map`).
{
  pkgs,
  engineMap,
}:
let
  source = pkgs.lib.fileset.toSource {
    root = ../engine-host;
    fileset = pkgs.lib.fileset.unions [
      ../engine-host/Cargo.toml
      ../engine-host/Cargo.lock
      ../engine-host/build.rs
      ../engine-host/src
      ../engine-host/map
    ];
  };
in
pkgs.rustPlatform.buildRustPackage {
  pname = "korri-steam-host";
  version = "0.1.0";
  src = source;
  cargoLock.lockFile = ../engine-host/Cargo.lock;
  env.KORRI_STEAM_ENGINE_MAP = "${engineMap}/engine.map";
  # The unit tests run in packages/engine-check.nix on the build host, with
  # both maps; a cross build cannot run them.
  doCheck = false;
  strictDeps = true;
  meta.mainProgram = "korri-steam-host";
}
