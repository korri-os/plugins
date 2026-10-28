"""Start hosting during play, as korrid does, and keep the running game.

korrid sends NETPLAY_HOST_TOGGLE to a RetroArch that already plays content.
The holder must keep its frame count: no core unload, no content reload. A
client that joins then starts from the holder's state, which the host sends
as a savestate. The original deterministic core needs no game ROMs, and both
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
root = Path.cwd() / "host-during-play"
root.mkdir()
content = root / "game.bin"
content.write_bytes(b"Korri original protocol fixture")


def free_port(kind):
    with socket.socket(socket.AF_INET, kind) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def frames(log):
    return [int(n) for n in re.findall(r"netplay-check frame=(\d+)", log.read_text())]


def wait_for(log, process, predicate, what, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate(log.read_text()):
            return
        assert process.poll() is None, log.read_text()
        time.sleep(0.05)
    raise AssertionError(f"Missing {what}:\n{log.read_text()}")


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


netplay_port = free_port(socket.SOCK_STREAM)
command_port = free_port(socket.SOCK_DGRAM)
processes = []
files = []
try:
    for role in ("host", "client"):
        config = root / f"{role}.cfg"
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
network_cmd_enable = "{"true" if role == "host" else "false"}"
network_cmd_port = "{command_port}"
netplay_ip_port = "{netplay_port}"
netplay_public_announce = "false"
netplay_nat_traversal = "false"
netplay_use_mitm_server = "false"
netplay_password = "sessionSecret"
netplay_request_device_p2 = "true"
''')

    host_log = root / "host.log"
    output = host_log.open("w")
    files.append(output)
    # The holder plays first, with no netplay at all.
    host = subprocess.Popen(
        [program, "-v", "--config", str(root / "host.cfg"), "-L", core, str(content)],
        stdout=output,
        stderr=subprocess.STDOUT,
        env={**os.environ, "HOME": str(root)},
    )
    processes.append(host)
    wait_for(
        host_log, host, lambda text: "netplay-check frame=360" in text, "frame 360"
    )
    assert not listening(netplay_port), "Host listened before the toggle"
    played = max(frames(host_log))

    # korrid's exact command, on RetroArch's command port.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control:
        control.sendto(b"NETPLAY_HOST_TOGGLE\n", ("127.0.0.1", command_port))
    deadline = time.monotonic() + 10
    while not listening(netplay_port):
        assert time.monotonic() < deadline, (
            f"Host never listened:\n{host_log.read_text()}"
        )
        assert host.poll() is None, host_log.read_text()
        time.sleep(0.05)

    client_log = root / "client.log"
    output = client_log.open("w")
    files.append(output)
    client = subprocess.Popen(
        [
            program,
            "-v",
            "--config",
            str(root / "client.cfg"),
            "-L",
            core,
            "--connect",
            "127.0.0.1",
            "--port",
            str(netplay_port),
            str(content),
        ],
        stdout=output,
        stderr=subprocess.STDOUT,
        env={**os.environ, "HOME": str(root)},
    )
    processes.append(client)
    wait_for(
        client_log, client, lambda text: "netplay-check synced=" in text, "client sync"
    )
    time.sleep(4)

    host_text = host_log.read_text()
    host_frames = frames(host_log)
    assert "[Lobby] Loading core" not in host_text, (
        f"Host reloaded its core:\n{host_text}"
    )
    assert host_frames == sorted(host_frames), (
        f"Host frame count went back: {host_frames}"
    )
    assert max(host_frames) > played, f"Host stopped advancing: {host_frames}"
    synced = [
        int(n)
        for n in re.findall(r"netplay-check synced=(\d+)", client_log.read_text())
    ]
    assert synced and synced[0] > played, (
        f"Client did not start from the holder's state: synced={synced}, played={played}"
    )
    client_frames = frames(client_log)
    assert client_frames and min(client_frames) > played, (
        f"Client did not continue the holder's game: {client_frames}"
    )
    assert all(p.poll() is None for p in processes), client_log.read_text()
    print(
        f"Hosting began during play at frame {played}; host kept running "
        f"{host_frames[-3:]}; client joined at {synced[0]} and advanced {client_frames[-3:]}"
    )
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
