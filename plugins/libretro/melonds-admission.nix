# Reuse the locked Core's compiled library, just like its published-game-launch
# gate. No Core source edit, device installation, or emulator execution.
{
  package,
  korridPackage,
  coreSource,
}:
korridPackage.overrideAttrs (old: {
  pname = "korri-melonds-admission";
  cargoArtifacts = korridPackage.buildArtifacts;
  outputs = [ "out" ];
  doNotPostBuildInstallCargoBinaries = true;
  buildPhase = ''
    runHook preBuild
    runHook postBuild
  '';
  installPhase = ''
    runHook preInstall
    touch "$out"
    runHook postInstall
  '';
  postInstall = "";
  KORRI_MELONDS_PACKAGE = package;
  postPatch = (old.postPatch or "") + ''
    cp ${./melonds-admission.rs} tests/melonds_admission.rs
    # Cargo integration checks also compile Core's probe binaries. Supply the
    # same reviewed fixtures as Core's published-game-launch-check.nix.
    mkdir -p ../../docs/research
    cp -R ${coreSource}/docs/research/retroarch-plugin-route ../../docs/research/retroarch-plugin-route
    cp -R ${coreSource}/docs/research/android-app-plugin-schema-checkpoint ../../docs/research/android-app-plugin-schema-checkpoint
  '';
  checkPhase = ''
    runHook preCheck
    cargo test --release --locked --offline --test melonds_admission -- --nocapture
    runHook postCheck
  '';
})
