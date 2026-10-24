# Pyxel native runner

`@korri:pyxel/pyxel` runs the selected local `.pyxapp` cartridge, including
multi-module applications. It does not search or download games. The separate
provider is `@korri:pyxelgallery`. Plain `.py` projects are **not** identified,
routed, or accepted. There is no single-example restriction on local carts.

The format comes from Pyxel 2.9.9 `cli.py`: a ZIP with one application directory
and `.pyxapp_startup_script`, whose text names the startup file relative to that
directory. The runner rejects missing, ambiguous, duplicate, absolute,
traversing and absent-target startup declarations before executing code. It
retains the upstream extraction, sibling imports and resource behavior. ZIP
magic `504b0304` is weak format evidence, not proof of valid or trusted Python.

Pyxel `init` changes cwd to the extracted script directory. The bootstrap must
not wrap `init`, because native `inspect.stack()` uses its caller to find that
directory. It calls native `fullscreen(True)` on first `run`, `show` or `flip`
instead. The original fixture verifies native sibling lookup and framebuffer
pixels; checks also inspect the actual X11 fullscreen property.

`resource.rs::user_data_dir` writes `HOME/.pyxel/<vendor>/<app>`, lowercasing and
sanitizing the two names. Korri sets HOME to the supplied account/game save root
and declares that root for save sync. **Relative project writes are temporary**
inside the upstream extracted application; they are not durable saves. Games
that write arbitrary absolute paths can ignore this save convention. Start is
not Pyxel's default quit key. Escape exits. A game can define its own controls.

This is ordinary Python execution under Korri's existing native-game process
policy. It is **not a filesystem or network sandbox**. Local input validation
is not a security boundary against malicious Python. Do not run arbitrary
showcase/downloaded code during automated acceptance. The opt-in live probe
requires the separately reviewed Space Rescue archive hash, or an explicit
reviewed hash supplied through `KORRI_PYXEL_REVIEWED_SHA256`.

## Source and notices

`package.nix` reuses the publisher's pinned nixpkgs `pyxel` 2.9.9 native package,
not a target build or a downloaded Python showcase. The version assertion makes
an update require startup-semantics review. Its source is
`kitao/pyxel` tag `v2.9.9`, NAR hash
`sha256-rz29OHlrAP+OPxMlYwyGdVMLDt7bFtVTcTh8PA3V6WI=`, with Cargo vendor hash
`sha256-IBjnYZ9H0KImX1Lf21F0j0dB++fXo4vt+wzQ4EDUI+g=`. Nixpkgs owns both
pins. The filtered native runtime includes Pyxel's MIT LICENSE and README in
`lib/python*/site-packages/pyxel/`. This does not license third-party carts.
The cached upstream package contains seven third-party sample carts. The
runtime copies its module and resources without the entire `examples` tree or
bytecode carrying upstream store paths. `disallowedReferences` refuses a hidden
reference to the unfiltered upstream output. No game is shipped. `fixture.py`
is original CC0 test code only.

## Integration and focused checks

Import `./default.nix { inherit pkgs mkPlugin; }` for `package` (native bootstrap)
and `plugin` (ordinary signed-plugin candidate). The source filter ships only
`plugin.ts`, never its tests. Parent publisher wiring exports these as `pyxel`
and `korri-plugin-pyxel`.

`./check.nix { inherit pkgs contract; package = pyxel.plugin; }` runs strict
TypeScript, launch refusals and real native multi-module `.pyxapp` execution.
It uses Xvfb/Openbox and software Mesa on the **build host**. It checks
fullscreen, native frame progress, an injected SDL Start event, Escape/clean
exit, unchanged read-only media, native save persistence across restarts and
account isolation. Malformed startup-marker fixtures cannot execute the
original outside/sibling fixture. These tests do not prove hardware mapping.

The optional `./probe.nix { inherit pkgs; }` produces:

```
korri-pyxel-native-probe PLUGIN_PACKAGE ARCHITECTURE KORRID ACQUIRED_CONTENT
```

It calls the supplied `korrid plugin-run` on that exact package and reviewed
content. The default acceptance hash is Space Rescue v2.9.9:
`250ababacc8f8b50a0e12c30e966b81e6aea1d8559e065a9a734baf59ba82be9`.
It does not assert other downloaded carts are compatible. This probe is a
separate build-host tool, not part of the plugin's runtime closure.

No target installation, publication or physical display/audio/controller,
performance or return-to-portal acceptance follows from these checks. Devices
must download approved prebuilt outputs with signatures; never compile there.

The live probe retains an actual X11 window screenshot `pyxel.png` and native
output `pyxel-load.log`. Set `KORRI_NATIVE_PROOF_DIR` to choose their directory.
Otherwise external mode prints a retained temporary directory. Inspect the image
for the reviewed game's actual title/content; process-alive is not gameplay
acceptance. The original fixture check exercises PNG capture too.
