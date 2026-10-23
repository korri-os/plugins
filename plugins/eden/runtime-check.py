"""Real Eden startup and native path configuration; no keys, firmware or games."""
import configparser
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

package, upstream, evidence = map(Path, sys.argv[1:])
evidence.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="eden-runtime-") as work:
    root = Path(work)
    # The GUI does not implement --help/--version. The bundled CLI does.
    probe = subprocess.run([upstream / "bin/eden-cli", "--version"],
                           env=dict(os.environ, HOME=work), capture_output=True,
                           text=True, timeout=15)
    assert probe.returncode == 0, probe.stderr
    assert "Eden" in probe.stdout, probe.stdout
    (evidence / "version.txt").write_text(probe.stdout)
    for account in ("Player One", "Player Two"):
        home = root / account
        home.mkdir()
        # A portable tree must not divert Eden away from the supplied XDG roots.
        (home / "user").mkdir()
        config = home / ".config/eden/qt-config.ini"
        config.parent.mkdir(parents=True)
        config.write_text("[Renderer]\nresolution_setup=2\nresolution_setup\\default=false\n"
                          "[Data%20Storage]\nnand_directory=/wrong\nsave_directory=/wrong\n")
        for game in ("first", "second"):
            saves = root / "saves" / account / game
            trace = root / f"{account}-{game}.trace"
            log = root / f"{account}-{game}.log"
            env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
                       XDG_DATA_HOME=str(home / ".local/share"),
                       XDG_CACHE_HOME=str(home / ".cache"), EDEN_SAVE_ROOT=str(saves),
                       QT_QPA_PLATFORMTHEME="xdgdesktopportal")
            env.pop("QT_QPA_PLATFORM", None)
            with log.open("w") as output:
                child = subprocess.Popen([
                    "strace", "-f", "-e", "trace=file", "-o", str(trace),
                    str(package / "bin/eden"),
                ], cwd=home, env=env, stdout=output, stderr=subprocess.STDOUT,
                    start_new_session=True)
                try:
                    deadline = time.monotonic() + 20
                    while time.monotonic() < deadline:
                        assert child.poll() is None, log.read_text()
                        text = trace.read_text() if trace.exists() else ""
                        # Ignore crudini's own reads/writes and the previous game's
                        # INI. Wait for the real Qt frontend to load and save it.
                        frontends = {line.split()[0] for line in text.splitlines()
                                     if 'execve(' in line and '/bin/..eden-wrapped-wrapped"' in line}
                        native_writes = any(line.split()[0] in frontends
                                            and str(config) in line and "O_WRONLY" in line
                                            for line in text.splitlines())
                        if native_writes and config.stat().st_size > 5000:
                            break
                        time.sleep(0.2)
                    else:
                        raise AssertionError(f"Eden startup timed out: {log.read_text()}")
                finally:
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait(timeout=5)
            (evidence / log.name).write_text(log.read_text())
            (evidence / trace.name).write_text(trace.read_text())
            settings = configparser.ConfigParser(interpolation=None)
            settings.read(config)
            # Check the group Eden actually consumes and writes, not the wrapper's
            # own discarded input. Config::BeginGroup calls AdjustKey: space -> %20.
            assert settings["Data%20Storage"]["nand_directory"].strip('"') == str(home / ".local/share/eden/nand")
            assert settings["Data%20Storage"]["save_directory"].strip('"') == str(saves / "nand"), dict(settings["Data%20Storage"])
            assert settings["Data%20Storage"]["save_directory\\default"] == "false"
            assert not settings.has_section("Data Storage")
            assert settings["Renderer"]["resolution_setup"] == "2"
            assert (saves / "nand/user/save").is_dir()
            assert (home / ".local/share/eden/keys").is_dir()
            assert not list((home / "user").iterdir())
            assert str(config) in text
            assert not any("/wrong" in line for line in text.splitlines() if "mkdir" in line)
    print("Eden real CLI/GUI, two-account isolation and native path retargeting passed")
