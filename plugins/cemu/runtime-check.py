"""Exercise the packaged wrapper and real Cemu startup; no ROM or device needed."""

import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

package = Path(sys.argv[1])
assert (
    ET.parse(package / "share/Cemu/settings.xml")
    .getroot()
    .findtext("Graphic/AsyncCompile")
    == "false"
)
evidence = Path(sys.argv[2])
evidence.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="cemu-runtime-") as work:
    root = Path(work)
    # Core's account scaffold inherits setgid. Its game unit denies chmod with
    # setid bits (RestrictSUIDSGID), even when chmod only retains inherited bits.
    # Nix's own build sandbox also rejects setting these bits. Exercise this
    # additional case outside that sandbox with --setgid-account.
    if "--setgid-account" in sys.argv[3:]:
        root.chmod(0o2770)
    env = dict(
        os.environ,
        HOME=str(root),
        XDG_CONFIG_HOME=str(root / ".config"),
        XDG_DATA_HOME=str(root / ".local/share"),
        XDG_CACHE_HOME=str(root / ".cache"),
    )
    env.pop("APPIMAGE", None)
    help_run = subprocess.run(
        [package / "bin/cemu", "--help"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert help_run.returncode == 0, help_run.stderr
    assert "--mlc" in help_run.stdout, help_run.stdout
    assert not (root / ".config").exists(), "help changed account state"
    config = root / ".config/Cemu/settings.xml"
    packs = root / ".local/share/Cemu/graphicPacks/downloadedGraphicPacks"
    mlc = root / "saves/mlc01"
    for attempt in range(2):
        if attempt == 1:
            # Gamescope 3.16.18 sets this even with --expose-wayland. The
            # wrapper must select X11 over an inherited Wayland preference.
            env["GAMESCOPE_WAYLAND_DISPLAY"] = "cemu-runtime-check"
            env["GDK_BACKEND"] = "wayland"
        trace = root / f"startup-{attempt}.trace"
        log = root / f"startup-{attempt}.log"
        with log.open("w") as output:
            child = subprocess.Popen(
                [
                    "strace",
                    "-f",
                    "-e",
                    "trace=file,fchmod",
                    "-o",
                    str(trace),
                    str(package / "bin/cemu"),
                    "--verbose",
                    "--mlc",
                    str(mlc),
                ],
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if child.poll() is not None:
                        raise AssertionError(
                            f"Cemu exited {child.returncode}: {log.read_text()}"
                        )
                    text = trace.read_text() if trace.exists() else ""
                    pack_reads = any(
                        str(packs) in line
                        and 'rules.txt"' in line
                        and "O_RDONLY" in line
                        for line in text.splitlines()
                    )
                    if pack_reads and (mlc / "usr/save").exists():
                        break
                    time.sleep(0.2)
                else:
                    raise AssertionError(
                        f"Cemu did not load offline packs: {log.read_text()}"
                    )
            finally:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                child.wait(timeout=10)
        shutil.copyfile(log, evidence / log.name)
        shutil.copyfile(trace, evidence / trace.name)
        for line in trace.read_text().splitlines():
            mode = re.search(
                r"(?:chmod|fchmod|fchmodat)\(.*?, (0[0-7]+)(?:, [^)]*)?\)", line
            )
            assert mode is None or not int(mode[1], 8) & 0o6000, (
                "startup requests setid permissions denied by the game unit: " + line
            )
        assert config.is_file()
        assert packs.is_dir() and not packs.is_symlink()
        assert (packs / "version.txt").read_text() == "graphicPacks989.zip"
        assert list(packs.glob("**/*BreathOfTheWild*")) or list(
            packs.glob("*BreathOfTheWild*")
        )
        assert pack_reads, "Cemu did not open account-local pack rules"
        for line in trace.read_text().splitlines():
            if str(package) in line:
                assert not any(
                    flag in line for flag in ("O_WRONLY", "O_RDWR", "O_CREAT")
                ), line
        if attempt == 0:
            settings = ET.parse(config).getroot()
            assert settings.findtext("gp_download") == "false"
            assert settings.findtext("Graphic/api") == "1"
            assert settings.findtext("Graphic/AsyncCompile") == "false"
            assert settings.findtext("fullscreen") == "true"
            assert settings.findtext("Audio/api") == "3"
            assert settings.findtext("Audio/TVDevice") == "default"
            # The next launch must preserve a person's edits to both native files.
            config.write_text(
                config.read_text()
                .replace(
                    "<fullscreen>true</fullscreen>", "<fullscreen>false</fullscreen>"
                )
                .replace(
                    "<AsyncCompile>false</AsyncCompile>",
                    "<AsyncCompile>true</AsyncCompile>",
                )
            )
            (packs / "user-note.txt").write_text("preserve me")
        else:
            assert ET.parse(config).getroot().findtext("fullscreen") == "false"
            assert ET.parse(config).getroot().findtext("Graphic/AsyncCompile") == "true"
            assert (packs / "user-note.txt").read_text() == "preserve me"
    assert not list(package.glob("bin/portable"))
print(
    "Cemu real CLI, offline pack loading, native configuration and seed preservation passed"
)
