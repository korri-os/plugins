"""Exercise the packaged wrapper and real Cemu startup; no ROM or device needed."""
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

package = Path(sys.argv[1])
evidence = Path(sys.argv[2])
evidence.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="cemu-runtime-") as work:
    root = Path(work)
    env = dict(os.environ, HOME=str(root), XDG_CONFIG_HOME=str(root / ".config"),
               XDG_DATA_HOME=str(root / ".local/share"), XDG_CACHE_HOME=str(root / ".cache"))
    env.pop("APPIMAGE", None)
    help_run = subprocess.run([package / "bin/cemu", "--help"], env=env,
                              capture_output=True, text=True, timeout=15)
    assert help_run.returncode == 0, help_run.stderr
    assert "--mlc" in help_run.stdout, help_run.stdout
    assert not (root / ".config").exists(), "help changed account state"
    config = root / ".config/Cemu/settings.xml"
    packs = root / ".local/share/Cemu/graphicPacks/downloadedGraphicPacks"
    mlc = root / "saves/mlc01"
    for attempt in range(2):
        trace = root / f"startup-{attempt}.trace"
        log = root / f"startup-{attempt}.log"
        with log.open("w") as output:
            child = subprocess.Popen([
                "strace", "-f", "-e", "trace=file", "-o", str(trace),
                str(package / "bin/cemu"), "--verbose", "--mlc", str(mlc),
            ], env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if child.poll() is not None:
                        raise AssertionError(f"Cemu exited {child.returncode}: {log.read_text()}")
                    text = trace.read_text() if trace.exists() else ""
                    pack_reads = any(str(packs) in line and 'rules.txt"' in line
                                     and "O_RDONLY" in line for line in text.splitlines())
                    if pack_reads and (mlc / "usr/save").exists():
                        break
                    time.sleep(0.2)
                else:
                    raise AssertionError(f"Cemu did not load offline packs: {log.read_text()}")
            finally:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                child.wait(timeout=10)
        shutil.copyfile(log, evidence / log.name)
        shutil.copyfile(trace, evidence / trace.name)
        assert config.is_file()
        assert packs.is_dir() and not packs.is_symlink()
        assert (packs / "version.txt").read_text() == "graphicPacks989.zip"
        assert list(packs.glob("**/*BreathOfTheWild*")) or list(packs.glob("*BreathOfTheWild*"))
        assert pack_reads, "Cemu did not open account-local pack rules"
        for line in trace.read_text().splitlines():
            if str(package) in line:
                assert not any(flag in line for flag in ("O_WRONLY", "O_RDWR", "O_CREAT")), line
        if attempt == 0:
            settings = ET.parse(config).getroot()
            assert settings.findtext("gp_download") == "false"
            assert settings.findtext("Graphic/api") == "1"
            assert settings.findtext("fullscreen") == "true"
            # The next launch must preserve a person's edits to both native files.
            config.write_text(config.read_text().replace("<fullscreen>true</fullscreen>", "<fullscreen>false</fullscreen>"))
            (packs / "user-note.txt").write_text("preserve me")
        else:
            assert ET.parse(config).getroot().findtext("fullscreen") == "false"
            assert (packs / "user-note.txt").read_text() == "preserve me"
    assert not list(package.glob("bin/portable"))
print("Cemu real CLI, offline pack loading, native configuration and seed preservation passed")
