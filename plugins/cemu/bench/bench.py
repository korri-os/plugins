"""Administrative bench, using the portal's existing localhost /rpc treaty.

Wire authority: contracts/generated/korrid.ts (RpcRequest, SessionReserveRequest,
SessionStartRequest, SessionStopRequest, LaunchSettingsSnapshotRequest).
Never log the capability, or launch anything other than through korrid.
"""

import argparse
import csv
import fcntl
import json
import os
import re
import signal
import subprocess
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import cast

from gamepad import Gamepad, read_script
from metrics import fps_bins, summarize

Record = dict[str, object]


def record(value: object) -> Record:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("Expected a JSON object")
    return cast(Record, value)


class RpcError(RuntimeError):
    def __init__(self, failure: Record):
        self.code = str(failure.get("code"))
        super().__init__(f"{self.code}: {failure.get('message')}")


class Rpc:
    def __init__(self, port: int, capability_file: Path):
        self.url = f"http://127.0.0.1:{port}/rpc"
        self.capability = capability_file.read_text().strip()
        if not self.capability:
            raise ValueError("Empty capability")

    def call(self, method: str, payload: Record) -> Record:
        request = urllib.request.Request(
            self.url,
            json.dumps({"_tag": method, "payload": payload}).encode(),
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.capability}",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            result = record(json.load(response))
        if result.get("_tag") != method:
            raise ValueError("RPC response method mismatch")
        outcome = record(result.get("outcome"))
        if outcome.get("_tag") == "Err":
            raise RpcError(record(outcome.get("payload")))
        if outcome.get("_tag") != "Ok":
            raise ValueError("Unknown RPC outcome")
        return record(outcome.get("payload"))


def require_idle(rpc: Rpc) -> None:
    try:
        status = rpc.call("app.session.status", {})
        if status.get("active") or status.get("pendingLaunches"):
            raise RuntimeError("Refusing to disturb an active or pending launch")
    except RpcError as exc:
        if exc.code not in ("SessionCompleted", "NoActiveSession"):
            raise


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True, timeout=20).strip()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def processes() -> dict[int, Record]:
    result: dict[int, Record] = {}
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            result[int(proc.name)] = {
                "exe": os.readlink(proc / "exe"),
                "argv": (proc / "cmdline")
                .read_bytes()
                .decode(errors="replace")
                .split("\0")[:-1],
                "cgroup": (proc / "cgroup").read_text(),
            }
        except (OSError, ProcessLookupError):
            continue
    return result


def members(unit: str) -> dict[int, Record]:
    return {
        pid: item
        for pid, item in processes().items()
        if any(
            line.split(":", 2)[-1].endswith("/" + unit)
            for line in str(item["cgroup"]).splitlines()
        )
    }


def environment(pid: int) -> dict[str, str]:
    return dict(
        entry.split("=", 1)
        for entry in Path(f"/proc/{pid}/environ").read_bytes().decode().split("\0")
        if "=" in entry
    )


def read_number(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def telemetry() -> Record:
    values: Record = {}
    for policy in sorted(Path("/sys/devices/system/cpu/cpufreq").glob("policy*")):
        values[f"cpu/{policy.name}/kHz"] = read_number(policy / "scaling_cur_freq")
    for gpu in sorted(Path("/sys/class/devfreq").glob("*gpu*")):
        values[f"gpu/{gpu.name}/Hz"] = read_number(gpu / "cur_freq")
    for zone in sorted(Path("/sys/class/thermal").glob("thermal_zone*")):
        values[f"temp/{zone.name}/{(zone / 'type').read_text().strip()}/mC"] = (
            read_number(zone / "temp")
        )
    return values


def wrapping(tree: dict[int, Record]) -> str:
    paths = [str(item["exe"]) for item in tree.values()]
    gamescope = any("gamescope" in path for path in paths)
    bwrap = any("bwrap" in path for path in paths)
    return f"Gamescope observed: {gamescope}; bubblewrap observed: {bwrap}." + (
        ""
        if bwrap
        else " bubblewrap absent: device image predates ADR 0015; strict ADR 0015 acceptance pending."
    )


def stop_exact(rpc: Rpc, launch: str) -> None:
    for _ in range(20):
        result = rpc.call("app.session.stop", {"expectedLaunchId": launch})
        if result.get("phase") == "stopped":
            return
        time.sleep(0.5)
    raise RuntimeError("Exact-session stop did not finish")


def run(rpc: Rpc, args: argparse.Namespace, folder: Path, name: str) -> None:
    folder.mkdir(parents=True, exist_ok=False)
    os.chmod(folder, 0o700)
    script = read_script(args.input_script) if args.input_script else []
    if args.input_script:
        (folder / "input.events").write_bytes(args.input_script.read_bytes())
    before = processes()
    write_json(
        folder / "settings.json",
        rpc.call("app.launch-settings.snapshot", {"gameId": args.game}),
    )
    write_json(
        folder / "routes.json",
        rpc.call("app.local-games.routes", {"gameId": args.game}),
    )
    identity = {
        "system": os.path.realpath("/run/current-system"),
        "systemProfile": os.path.realpath("/nix/var/nix/profiles/system"),
        "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "kernel": os.uname().release,
        "host": os.uname().nodename,
    }
    write_json(folder / "device.json", identity)
    launch = ""
    started = False
    pad: Gamepad | None = None
    observer: subprocess.Popen[str] | None = None
    frames_file = (folder / "present.csv").open("w")
    observer_log = (folder / "observer.log").open("w")
    error = ""
    cleanup_error = ""
    tree: dict[int, Record] = {}
    window = 0
    measurement_start = 0.0
    journal_since = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    rows: list[Record] = []
    try:
        require_idle(rpc)
        if script:
            pad = Gamepad()
            time.sleep(2)  # allow normal udev/InputPlumber/inputd discovery
        reservation = rpc.call("app.session.reserve", {"gameId": args.game})
        launch = str(reservation["launchId"])
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", launch):
            raise ValueError("Unsafe launch ID")
        write_json(folder / "reservation.json", reservation)
        response = rpc.call(
            "app.session.start",
            {"gameId": args.game, "runnerId": args.runner, "expectedLaunchId": launch},
        )
        started = True
        write_json(folder / "launch.json", response)
        unit = f"korri-game-{launch}.service"
        renderer = 0
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            tree = members(unit)
            candidates = [
                pid
                for pid, item in tree.items()
                if args.process_name.lower() in Path(str(item["exe"])).name.lower()
            ]
            for pid in candidates:
                if environment(pid).get("DISPLAY"):
                    renderer = pid
            if renderer:
                break
            time.sleep(0.25)
        if not renderer:
            raise RuntimeError(
                "No X11 renderer in the exact launch cgroup; native Wayland needs another FPS observer"
            )
        tree = members(unit)
        write_json(folder / "processes.json", tree)
        (folder / "unit.txt").write_text(
            command(
                "systemctl",
                "show",
                unit,
                "-p",
                "ControlGroup",
                "-p",
                "ExecStart",
                "-p",
                "Environment",
            )
        )
        env = os.environ.copy()
        render_env = environment(renderer)
        for key in ("DISPLAY", "XAUTHORITY", "XDG_RUNTIME_DIR"):
            if key in render_env:
                env[key] = render_env[key]
        observer = subprocess.Popen(
            [
                "nsenter",
                "--target",
                str(renderer),
                "--mount",
                "--setuid",
                str(Path(f"/proc/{renderer}").stat().st_uid),
                "--setgid",
                str(Path(f"/proc/{renderer}").stat().st_gid),
                "--",
                os.environ["KORRI_BENCH_PRESENT_WATCH"],
                str(renderer),
            ],
            env=env,
            stdout=frames_file,
            stderr=observer_log,
            text=True,
        )
        time.sleep(args.input_delay)
        script_start = time.monotonic()
        for event in script:
            time.sleep(max(0, script_start + event[0] - time.monotonic()))
            if pad:
                pad.send(event)
        warmup_start = time.monotonic()
        measurement_start = warmup_start + args.warmup
        end = measurement_start + args.seconds
        next_sample = warmup_start
        with (folder / "telemetry.jsonl").open("w") as output:
            while time.monotonic() < end:
                if observer.poll() is not None:
                    raise RuntimeError("X Present observer exited; see observer.log")
                if not members(unit):
                    raise RuntimeError("Game exited before measurement completed")
                now = time.monotonic()
                row: Record = {
                    "monotonic_s": now,
                    "phase": "warmup" if now < measurement_start else "measurement",
                    **telemetry(),
                }
                rows.append(row)
                output.write(json.dumps(row) + "\n")
                output.flush()
                next_sample += 1
                time.sleep(max(0, min(end, next_sample) - time.monotonic()))
    except (
        OSError,
        ValueError,
        RuntimeError,
        subprocess.SubprocessError,
        KeyboardInterrupt,
    ) as exc:
        error = str(exc) or type(exc).__name__
    finally:
        if observer:
            observer.terminate()
            try:
                observer.wait(timeout=5)
            except subprocess.TimeoutExpired:
                observer.kill()
                observer.wait()
        frames_file.close()
        observer_log.close()
        if launch:
            try:
                if started:
                    stop_exact(rpc, launch)
                else:
                    # A timed-out start may have succeeded. Stop only our exact identity.
                    try:
                        stop_exact(rpc, launch)
                    except RpcError:
                        rpc.call("app.session.cancel", {"expectedLaunchId": launch})
            except (
                OSError,
                ValueError,
                RuntimeError,
                subprocess.SubprocessError,
            ) as exc:
                cleanup_error = str(exc)
        if pad:
            pad.close()
        time.sleep(0.5)
        after = processes()
        remaining = members(f"korri-game-{launch}.service") if launch else {}
        new_wrappers = {
            pid: item
            for pid, item in after.items()
            if pid not in before
            and any(
                token in Path(str(item["exe"])).name.lower()
                for token in ("cemu", "gamescope", args.process_name.lower())
            )
        }
        cleanup: Record = {
            "exactCgroupRemaining": remaining,
            "newGameOrWrapperProcesses": new_wrappers,
            "error": cleanup_error,
            "bootUnchanged": identity["bootId"]
            == Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "systemUnchanged": identity["system"]
            == os.path.realpath("/run/current-system"),
        }
        write_json(folder / "cleanup.json", cleanup)
        if remaining or new_wrappers or cleanup_error:
            error = (
                error
                or "Cleanup failed; inspect cleanup.json (no global kill was attempted)"
            )
        if launch:
            journal = subprocess.run(
                [
                    "journalctl",
                    "--no-pager",
                    "-o",
                    "cat",
                    "--since",
                    journal_since,
                    "-u",
                    f"korri-game-{launch}.service",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )
            (folder / "session.log").write_text(journal.stdout)
        if args.cemu_log and args.cemu_log.is_file():
            log = args.cemu_log.read_text(errors="replace")
            (folder / "cemu.log").write_text(log)
            evidence = [
                line
                for line in log.splitlines()
                if re.search(r"vulkan|driver|cpu.*mode|recompiler", line, re.IGNORECASE)
            ]
            (folder / "cemu-evidence.txt").write_text("\n".join(evidence) + "\n")
            for pattern in (r"vulkan", r"driver", r"recompiler|cpu.*mode"):
                if not re.search(pattern, "\n".join(evidence), re.IGNORECASE):
                    error = error or f"Cemu evidence missing: {pattern}"
        elif args.cemu_log:
            error = error or "Cemu log missing"
        events: list[tuple[float, int, int]] = []
        with (folder / "present.csv").open() as source:
            for row_data in csv.DictReader(source):
                events.append(
                    (
                        float(row_data["monotonic_s"]),
                        int(row_data["window"]),
                        int(row_data["mode"]),
                    )
                )
        # Pin the dominant game window from warmup; never combine UI and renderer windows.
        window_counts = Counter(
            win
            for stamp, win, mode in events
            if mode != 2 and stamp < measurement_start
        )
        if window_counts:
            window = window_counts.most_common(1)[0][0]
        if not window:
            error = error or "No game Present completions during warmup"
        values = fps_bins(events, window, measurement_start, args.seconds)
        if not sum(values):
            error = error or "No game presentations in the measurement window"
        stats = summarize(values)
        write_json(
            folder / "fps.json",
            {
                "window": window,
                "measurementStart": measurement_start,
                "seconds": args.seconds,
                "fps": values,
                **stats,
            },
        )
        peaks: dict[str, int] = {}
        for row in rows:
            for key, value in row.items():
                if key.startswith("temp/") and isinstance(value, int):
                    peaks[key] = max(peaks.get(key, value), value)
        report = [
            f"# {identity['host']}: {name}",
            "",
            f"Status: {'FAILED: ' + error if error else 'PASS'}",
            "",
            f"Game: `{args.game}`; runner: `{args.runner}`; launch: `{launch}`.",
            f"System: `{identity['system']}`; kernel `{identity['kernel']}`.",
            f"Warmup: {args.warmup} s after input script; measured: {args.seconds} s.",
            f"Spot: {args.spot}. Script execution is not proof of visual position.",
            "",
            "## FPS",
            "",
            "Source: X11 Present CompleteNotify, kind Pixmap, Skip excluded, one game window.",
            "Counts game presentations to Gamescope's Xwayland, not repeated compositor refreshes.",
            "This does not prove physical panel scanout or emulated game simulation rate.",
            f"Window: {window}; one-second FPS bins; p10/p1 use nearest rank; zero bins included.",
            "",
            "| median | p10 | p1 | min |",
            "|---:|---:|---:|---:|",
            f"| {stats['median']:.2f} | {stats['p10']:.2f} | {stats['p1']:.2f} | {stats['min']:.2f} |",
            "",
            "## Launch and cleanup",
            "",
            wrapping(tree),
            "Launch settings: `settings.json`; actual command chain: `processes.json`, `unit.txt`.",
            f"Exact cgroup empty: {not remaining}; new game/Gamescope processes absent: {not new_wrappers}.",
            f"Cleanup error: {cleanup_error or 'none'}. System and boot unchanged: {cleanup['systemUnchanged']} / {cleanup['bootUnchanged']}.",
            "No sysfs, system, emulator configuration or generation writes by the bench.",
            "A/B selects existing launch profiles through RPC and restores the original selection.",
            "Korri performs its normal play-log/save effects. uinput device is destroyed.",
            "",
            "## CPU / GPU and thermals",
            "",
            "One-second CPU policy kHz, GPU Hz, and all zones: `telemetry.jsonl`.",
            "Unreadable zones are null, not zero. Peaks include warmup.",
            "",
            "| zone | peak °C |",
            "|---|---:|",
        ]
        report += [
            f"| {key.removeprefix('temp/').removesuffix('/mC')} | {value / 1000:.3f} |"
            for key, value in sorted(peaks.items())
        ]
        report += [
            "",
            "## Cemu evidence",
            "",
            "See `cemu-evidence.txt` and `cemu.log`."
            if args.cemu_log
            else "Not applicable: non-Cemu validation launch.",
            "",
        ]
        (folder / "report.md").write_text("\n".join(report))
    if error:
        raise RuntimeError(f"{error}; report: {folder / 'report.md'}")
    print(folder / "report.md", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["run", "soak", "ab"])
    parser.add_argument("--game", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument(
        "--process-name",
        required=True,
        help="Renderer executable basename fragment (e.g. retroarch or Cemu)",
    )
    parser.add_argument("--output", type=Path, required=True, help="New run directory")
    parser.add_argument("--port", type=int, default=39217)
    parser.add_argument(
        "--capability-file",
        type=Path,
        default=Path("/run/korri-portal-credentials/KORRID_RPC_CAPABILITY"),
    )
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument(
        "--minutes", type=int, default=15, help="Soak measurement minutes, after warmup"
    )
    parser.add_argument(
        "--input-script", type=Path, help="Native evemu event text; gamepad events only"
    )
    parser.add_argument("--input-delay", type=float, default=5)
    parser.add_argument("--spot", default="Unspecified; validation launch only")
    parser.add_argument("--cemu-log", type=Path)
    parser.add_argument("--variant", default="baseline")
    parser.add_argument(
        "--a", help="A/B NAME=existing-launch-profile-id (use '-' for no profile)"
    )
    parser.add_argument("--b", help="A/B NAME=existing-launch-profile-id")
    args = parser.parse_args()
    if (
        not 1 <= args.port <= 65535
        or not 1 <= args.seconds <= 86400
        or not 1 <= args.minutes <= 1440
        or not 1 <= args.warmup <= 3600
        or not 0 <= args.input_delay <= 3600
    ):
        parser.error("Invalid port or duration")
    if args.mode == "soak":
        args.seconds = args.minutes * 60
    if not args.process_name or "/" in args.process_name:
        parser.error("process-name must be a nonempty basename fragment")
    if args.input_script:
        read_script(args.input_script)  # validate before creating any device or session
    rpc = Rpc(args.port, args.capability_file)
    # One bench per device. The lock file contains no capability or runtime state.
    with Path("/run/korri-cemu-bench.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.mode != "ab":
            run(rpc, args, args.output, args.variant)
            return
        if not args.a or not args.b or "=" not in args.a or "=" not in args.b:
            parser.error("ab requires --a NAME=PROFILE --b NAME=PROFILE")
        original = rpc.call("app.launch-settings.snapshot", {"gameId": args.game})
        selected = original.get("selectedProfile")
        args.output.mkdir(parents=True, exist_ok=False)
        try:
            for index, variant in enumerate((args.a, args.b), 1):
                name, profile = variant.split("=", 1)
                if not name or not profile:
                    raise ValueError("A/B name and profile must be nonempty")
                snapshot = rpc.call(
                    "app.launch-settings.snapshot", {"gameId": args.game}
                )
                payload: Record = {
                    "gameId": args.game,
                    "expectedRevision": record(snapshot["revisions"])["games"],
                }
                if profile != "-":
                    payload["profileId"] = profile
                rpc.call("app.launch-settings.profile.select", payload)
                run(rpc, args, args.output / str(index), name)
        finally:
            snapshot = rpc.call("app.launch-settings.snapshot", {"gameId": args.game})
            payload = {
                "gameId": args.game,
                "expectedRevision": record(snapshot["revisions"])["games"],
            }
            if selected is not None:
                payload["profileId"] = selected
            rpc.call("app.launch-settings.profile.select", payload)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    main()
