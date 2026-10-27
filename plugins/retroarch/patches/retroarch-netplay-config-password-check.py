"""Run the packaged frontend twice: authenticate, then reject a wrong secret.

The original deterministic core needs no third-party game or hardware. Both
frontends use menu_driver=null, as the deployed Korri runner does.
"""

import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

program, core = sys.argv[1:]
root = Path.cwd()
content = root / "game.bin"
content.write_bytes(b"Korri original protocol fixture")


def wait_for(path, text, process, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if text in path.read_text():
            return
        assert process.poll() is None, path.read_text()
        time.sleep(0.05)
    raise AssertionError(f"Missing {text!r}:\n{path.read_text()}")


def check(password, accepted):
    directory = root / ("accepted" if accepted else "refused")
    directory.mkdir()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    processes = []
    files = []
    try:
        for role, secret in (("host", "correctSecret"), ("client", password)):
            config = directory / f"{role}.cfg"
            config.write_text(f'''
video_driver = "sdl2"
audio_driver = "null"
input_driver = "sdl2"
input_joypad_driver = "sdl2"
menu_driver = "null"
pause_nonactive = "false"
video_fullscreen = "false"
video_vsync = "true"
config_save_on_exit = "false"
savestate_auto_load = "false"
savestate_auto_save = "false"
netplay_ip_port = "{port}"
netplay_public_announce = "false"
netplay_nat_traversal = "false"
netplay_use_mitm_server = "false"
netplay_password = "{secret}"
netplay_request_device_p2 = "true"
''')
            log = directory / f"{role}.log"
            output = log.open("w")
            files.append(output)
            args = ["--host"] if role == "host" else ["--connect", "127.0.0.1", "--port", str(port)]
            process = subprocess.Popen(
                [program, "-v", "--config", str(config), "-L", core, *args, str(content)],
                stdout=output, stderr=subprocess.STDOUT, env={**os.environ, "HOME": str(directory)},
            )
            processes.append(process)
            if role == "host":
                wait_for(log, "netplay-check frame=120", process)
        host_log = directory / "host.log"
        client_log = directory / "client.log"
        if accepted:
            wait_for(client_log, '[Netplay] Connected to', processes[1])
            wait_for(client_log, 'netplay-check synced=', processes[1])
            time.sleep(5)
            frames = [int(n) for n in re.findall(r"netplay-check frame=(\d+)", client_log.read_text())]
            assert len(set(frames)) >= 2, client_log.read_text()
            assert all(p.poll() is None for p in processes), client_log.read_text()
            assert "wrong password" not in host_log.read_text()
            print(f"Configured headless password accepted; client advanced: {frames}")
        else:
            wait_for(host_log, "wrong password", processes[0])
            assert '[Netplay] Connected to' not in client_log.read_text()
            print("Wrong headless password refused by the native host handshake")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for output in files:
            output.close()


check("correctSecret", True)
check("wrongSecret", False)
