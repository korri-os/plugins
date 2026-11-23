# korri-steam-host from its Rust source and one engine map (ADR 0083).
# `engineMap` is a folder that holds `<system>/engine.map` for each system: the
# public empty maps, or the private maps of the pinned engine (flake input
# `steam-engine-map`). The host is built from the map of the system it runs on.
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
  # The map on its own, named by its content. The `steam-engine-map` input's
  # default is a relative path, so its outPath is a subfolder of the whole
  # publisher source: interpolating it directly made every publisher file a
  # build input of the host (the plugin churn check's helper case).
  # One system's map only: a change to the other system's map does not
  # rebuild this host.
  mapRoot = if builtins.isAttrs engineMap then engineMap.outPath else engineMap;
  map = builtins.path {
    name = "korri-steam-engine-map";
    path = mapRoot + "/${pkgs.stdenv.hostPlatform.system}";
    filter = path: _: baseNameOf path == "engine.map";
  };
in
pkgs.rustPlatform.buildRustPackage {
  pname = "korri-steam-host";
  version = "0.1.0";
  src = source;
  cargoLock.lockFile = ../engine-host/Cargo.lock;
  env.KORRI_STEAM_ENGINE_MAP = "${map}/engine.map";
  # The unit tests run in packages/engine-check.nix on the build host, with
  # both maps; a cross build cannot run them.
  doCheck = false;
  strictDeps = true;
  meta.mainProgram = "korri-steam-host";
}
