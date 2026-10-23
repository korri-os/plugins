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
from collections.abc import Callable
from pathlib import Path
from typing import cast

from controller_profile import ControllerProfile
from gamepad import Gamepad, gamepad_identity, read_script
from gameplay_gate import FrameCapture, GameplayGate, Reference
from input_observer import InputObserver
from input_replay import replay_script
from metrics import fps_bins, summarize
from reporting import fps_section, gate_section, not_measured_report
from save_proof import SaveProof, SaveReadWatch
from save_safety import SaveSafety

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

    def call(self, method: str, payload: Record, timeout_s: float = 30) -> Record:
        request = urllib.request.Request(
            self.url,
            json.dumps({"_tag": method, "payload": payload}).encode(),
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.capability}",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
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
        if exc.code == "HostLaunchFailed":
            # status can retain the previous game's terminal exit failure.
            # This code also covers observation errors, so never assume idle.
            confirm_native_idle()
        elif exc.code not in ("SessionCompleted", "NoActiveSession"):
            raise


def confirm_native_idle() -> None:
    units = subprocess.check_output(
        [
            "systemctl",
            "list-units",
            "--plain",
            "--no-legend",
            "--no-pager",
            "--state=active,activating,deactivating,reloading",
            "korri-game-*",
            "korri-acquire-*",
        ],
        text=True,
        timeout=5,
    )
    populated = any(
        path.read_text().strip()
        for path in Path("/sys/fs/cgroup/korri.slice/korri-games.slice").rglob(
            "cgroup.procs"
        )
    )
    verify_native_idle(units, populated)


def verify_native_idle(units: str, populated: bool) -> None:
    if units.strip() or populated:
        raise RuntimeError(
            "Previous launch failed but game activity remains; refusing new bench"
        )


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True, timeout=20).strip()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def aggregate_gate_sections(folder: Path) -> list[str]:
    lines = []
    for path in sorted(folder.glob("*/gate.json")):
        timings = record(json.loads(path.read_text())).get("timings", {})
        lines += [
            f"Run: {path.parent.name}",
            *gate_section(cast(dict[str, float | None], timings)),
        ]
    return lines or gate_section({})


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


def namespace_pid(status: str, host_pid: int) -> int:
    """Xwayland sees the service's PrivatePIDs namespace, not host /proc PIDs."""
    for line in status.splitlines():
        if line.startswith("NSpid:"):
            return int(line.split()[-1])
    return host_pid


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
        else " bubblewrap not observed; ADR 0015 implementation/acceptance is not proved by this run."
    )


def stop_exact(
    rpc: Rpc,
    launch: str,
    native_guard: Callable[[], None] = confirm_native_idle,
    recovery_seconds: float = 10,
    poll_seconds: float = 0.5,
) -> list[str]:
    for _ in range(20):
        try:
            result = rpc.call("app.session.stop", {"expectedLaunchId": launch})
        except RpcError as exc:
            if exc.code != "HostRecoveryBlocked":
                raise
            warning = str(exc)
            deadline = time.monotonic() + recovery_seconds
            while time.monotonic() < deadline:
                unblocked = False
                try:
                    status = rpc.call(
                        "app.session.status",
                        {},
                        timeout_s=max(0.1, deadline - time.monotonic()),
                    )
                    unblocked = not status.get("active") and not status.get(
                        "pendingLaunches"
                    )
                except RpcError as observed:
                    if observed.code in (
                        "HostLaunchFailed",
                        "SessionCompleted",
                        "NoActiveSession",
                    ):
                        unblocked = True
                    elif observed.code != "HostRecoveryBlocked":
                        raise
                if unblocked:
                    try:
                        native_guard()
                    except RuntimeError:
                        pass
                    else:
                        return [
                            warning
                            + "; resolved by korrid status recovery; systemd/cgroups idle"
                        ]
                time.sleep(poll_seconds)
            raise RuntimeError(
                f"{warning}; exact stop recovery did not clear; no journal/reset/restart was attempted"
            ) from exc
        if result.get("phase") == "stopped":
            return []
        time.sleep(poll_seconds)
    raise RuntimeError("Exact-session stop did not finish")


def run(rpc: Rpc, args: argparse.Namespace, folder: Path, name: str) -> None:
    folder.mkdir(parents=True, exist_ok=False)
    os.chmod(folder, 0o700)
    try:
        reference = Reference.load(args.reference)
        if reference.game != args.game:
            raise ValueError("Reference belongs to a different game")
        _run(rpc, args, folder, name, reference)
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        subprocess.SubprocessError,
        KeyboardInterrupt,
    ) as exc:
        if (folder / "fps.json").exists():
            (folder / "fps.json").unlink()
        if not (folder / "report.md").exists():
            timings = (
                record(json.loads((folder / "gate.json").read_text())).get(
                    "timings", {}
                )
                if (folder / "gate.json").exists()
                else {}
            )
            (folder / "report.md").write_text(
                not_measured_report(
                    str(exc) or type(exc).__name__,
                    cast(dict[str, float | None], timings),
                    "See save-safety.json and cleanup.json if present; no safety claim without verification.",
                )
            )
        raise


def _run(
    rpc: Rpc, args: argparse.Namespace, folder: Path, name: str, reference: Reference
) -> None:
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
        "korrid": os.readlink(
            f"/proc/{command('systemctl', 'show', 'korrid', '-p', 'MainPID', '--value')}/exe"
        ),
    }
    write_json(folder / "device.json", identity)
    launch = ""
    started = False
    pad: Gamepad | None = None
    input_observer: InputObserver | None = None
    controller_profile: ControllerProfile | None = None
    observer: subprocess.Popen[str] | None = None
    save_watch: SaveReadWatch | None = None
    frames_file = (folder / "present.csv").open("w")
    observer_log = (folder / "observer.log").open("w")
    error = ""
    cleanup_error = ""
    stop_warnings: list[str] = []
    tree: dict[int, Record] = {}
    window = 0
    measurement_start = 0.0
    journal_since = f"@{time.time():.6f}"
    wall_start_ns = time.time_ns()
    cemu_evidence = "Not applicable: non-Cemu validation launch."
    rows: list[Record] = []
    gate = GameplayGate(reference, started=time.monotonic(), timeout=args.gate_timeout)
    capture = FrameCapture(
        reference, args.capture_user, args.runtime_dir, args.wayland_display
    )
    safety = SaveSafety(rpc, args.game, args.runner, args.save_objects, folder)
    try:
        require_idle(rpc)
        confirm_native_idle()
        foreign = [
            item
            for item in before.values()
            if any(
                token in Path(str(item["exe"])).name.lower()
                for token in ("eden", "gamescope", "cemu")
            )
        ]
        if foreign:
            raise RuntimeError(
                "Foreign Eden/Gamescope/Cemu process exists; refusing bench"
            )
        safety.preflight()
        if script:
            input_observer = InputObserver(folder)
            input_observer.begin()
        safety.verify_before_launch()
        reservation = rpc.call("app.session.reserve", {"gameId": args.game})
        launch = str(reservation["launchId"])
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", launch):
            raise ValueError("Unsafe launch ID")
        write_json(folder / "reservation.json", reservation)
        if args.controller_profile:
            controller_profile = ControllerProfile(
                args.controller_profile, args.controller_template, folder
            )
            controller_profile.apply()
        gate = GameplayGate(
            reference, started=time.monotonic(), timeout=args.gate_timeout
        )
        response = rpc.call(
            "app.session.start",
            {"gameId": args.game, "runnerId": args.runner, "expectedLaunchId": launch},
        )
        started = True
        write_json(folder / "launch.json", response)
        if script:
            # Hotplug only after korrid has started the real game session.
            pad = Gamepad()
            time.sleep(2)  # normal udev/InputPlumber/inputd discovery
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
                str(
                    namespace_pid(
                        Path(f"/proc/{renderer}/status").read_text(), renderer
                    )
                ),
            ],
            env=env,
            stdout=frames_file,
            stderr=observer_log,
            text=True,
        )

        def observe() -> None:
            if observer is None or observer.poll() is not None or not members(unit):
                raise RuntimeError("Game/observer exited during gameplay gate")
            statistics = capture.capture()
            now = time.monotonic()
            label = gate.observe(statistics, now)
            write_json(
                folder / "gate.json", {"phase": gate.phase, "timings": gate.timings}
            )
            with (folder / "frames.jsonl").open("a") as frames:
                frames.write(
                    json.dumps(
                        {
                            "at": now - gate.started,
                            "label": label,
                            "statistics": statistics,
                        }
                    )
                    + "\n"
                )

        while not gate.title_ready:
            observe()
            if not gate.title_ready:
                time.sleep(args.gate_poll)
        if getattr(args, "before_input", None):
            args.before_input(tree)
        if args.require_save_read:
            SaveProof(args.save_root, folder).verify_declaration(tree)
            save_watch = SaveReadWatch(
                args.save_root,
                {
                    pid
                    for pid, item in tree.items()
                    if Path(str(item["exe"])).name == "Cemu"
                },
            )
        gate.begin_input(time.monotonic())
        with (folder / "input-replay.jsonl").open("w") as replay:
            replay_script(
                script,
                pad.send if pad else lambda _: None,
                observe,
                lambda: gate.timings["loadingAt"] is not None,
                lambda: gate.check_timeout(time.monotonic()),
                replay,
                repeat_until_loading=args.repeat_input_until_loading,
                poll_seconds=args.gate_poll,
            )
        while not gate.ready:
            observe()
            if not gate.ready:
                time.sleep(args.gate_poll)
        if save_watch:
            reads = save_watch.collect()
            write_json(folder / "save-read.json", reads)
            save_watch.close()
            save_watch = None
            if str(args.require_save_read) not in reads:
                raise RuntimeError(
                    "Required actual Cemu game_data.sav read was not observed"
                )
        if getattr(args, "save_action", None):
            args.save_action(pad, capture, tree)
        if reference.classify(capture.capture()) != "gameplay":
            raise RuntimeError("Gameplay no longer matches before warmup starts")
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
                if input_observer:
                    input_observer.collect()
                output.write(json.dumps(row) + "\n")
                output.flush()
                next_sample += 1
                time.sleep(max(0, min(end, next_sample) - time.monotonic()))
        gate.finish(capture.capture(), time.monotonic())
        write_json(folder / "gate.json", {"phase": gate.phase, "timings": gate.timings})
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        subprocess.SubprocessError,
        KeyboardInterrupt,
    ) as exc:
        error = str(exc) or type(exc).__name__
    finally:
        if save_watch:
            save_watch.close()
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
                    stop_warnings.extend(stop_exact(rpc, launch))
                else:
                    # A timed-out start may have succeeded. Stop only our exact identity.
                    try:
                        stop_warnings.extend(stop_exact(rpc, launch))
                    except RpcError:
                        rpc.call("app.session.cancel", {"expectedLaunchId": launch})
            except (
                OSError,
                ValueError,
                RuntimeError,
                subprocess.SubprocessError,
            ) as exc:
                cleanup_error = str(exc)
        if input_observer:
            try:
                # Capture ownership while our uinput source still exists, even
                # when startup failed before the first telemetry sample.
                input_observer.collect()
            except (
                OSError,
                ValueError,
                TypeError,
                RuntimeError,
                subprocess.SubprocessError,
            ) as exc:
                cleanup_error = cleanup_error or str(exc)
        if pad:
            try:
                pad.close()
            except OSError as exc:
                cleanup_error = cleanup_error or str(exc)
        if input_observer:
            try:
                input_observer.close()
                if script and not any(
                    event["seat"] == "Korri Seat P2"
                    and event["type"] in (1, 3)
                    and event["value"] != 0
                    for event in input_observer.events
                ):
                    error = (
                        error
                        or "uinput script did not reach Korri Seat P2; navigation is unproven"
                    )
            except (
                OSError,
                ValueError,
                TypeError,
                RuntimeError,
                subprocess.SubprocessError,
            ) as exc:
                cleanup_error = cleanup_error or str(exc)
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
        if controller_profile:
            try:
                if remaining:
                    raise RuntimeError(
                        "Game still active; defer controller-profile restore until exact session stops"
                    )
                controller_profile.restore()
            except (OSError, ValueError, TypeError, RuntimeError) as exc:
                cleanup_error = cleanup_error or str(exc)
        if (
            launch
            and not remaining
            and not new_wrappers
            and not cleanup_error
            and not getattr(args, "defer_save_restore", False)
        ):
            try:
                require_idle(rpc)
                confirm_native_idle()
                safety.restore()
            except (
                OSError,
                ValueError,
                TypeError,
                RuntimeError,
                subprocess.SubprocessError,
            ) as exc:
                cleanup_error = str(exc)
        elif launch and (remaining or new_wrappers or cleanup_error):
            cleanup_error = (
                cleanup_error
                or "Save restore deferred: exact session is not conclusively stopped"
            )
        write_json(folder / "gate.json", {"phase": gate.phase, "timings": gate.timings})
        cleanup: Record = {
            "exactCgroupRemaining": remaining,
            "newGameOrWrapperProcesses": new_wrappers,
            "error": cleanup_error,
            "stopWarnings": stop_warnings,
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
            if args.cemu_log.stat().st_mtime_ns < wall_start_ns:
                error = error or "Cemu log is stale: it was not written by this launch"
            log = args.cemu_log.read_text(errors="replace")
            (folder / "cemu.log").write_text(log)
            evidence = [
                line
                for line in log.splitlines()
                if re.search(r"vulkan|driver|cpu.*mode|recompiler", line, re.IGNORECASE)
            ]
            (folder / "cemu-evidence.txt").write_text("\n".join(evidence) + "\n")
            cemu_evidence = "```text\n" + "\n".join(evidence) + "\n```"
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
                        int(row_data["ust_us"]) / 1_000_000,
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
        if not error:
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
            f"Status: {'not measured: ' + error if error else 'PASS'}",
            "",
            f"Game: `{args.game}`; runner: `{args.runner}`; launch: `{launch}`.",
            f"System: `{identity['system']}`; kernel `{identity['kernel']}`.",
            f"Running korrid: `{identity['korrid']}`.",
            f"Warmup: {args.warmup} s after verified gameplay and input completion; requested sample: {args.seconds} s.",
            f"Spot: {args.spot}. Script execution is not proof of visual position.",
            "",
            *gate_section(gate.timings),
            "## Save safety",
            "",
            safety.summary(),
            "",
            *fps_section(error, stats),
            "## Launch and cleanup",
            "",
            wrapping(tree),
            "Launch settings: `settings.json`; actual command chain: `processes.json`, `unit.txt`.",
            f"Exact cgroup empty: {not remaining}; new game/Gamescope processes absent: {not new_wrappers}.",
            f"Cleanup error: {cleanup_error or 'none'}. System and boot unchanged: {cleanup['systemUnchanged']} / {cleanup['bootUnchanged']}.",
            f"Exact-stop warnings: {stop_warnings or 'none'}.",
            "No sysfs, system or generation writes by the bench.",
            f"Cemu-native controller profile: {controller_profile.state if controller_profile else 'not changed'}. See `controller-profile.json` when used.",
            "A/B selects existing launch profiles through RPC and restores the original selection.",
            "Korri performs its normal play-log/save effects. uinput device is destroyed.",
            f"InputPlumber runtime management: { {key: input_observer.state.get(key) for key in ('before', 'after', 'managementUnchanged', 'compositesRestored', 'builtinUnchanged', 'seatP1Unchanged')} if input_observer else 'not changed (no input script)' }. See `input-observer.json` and `seat-events.json`.",
            f"Bench-only synthetic gamepad identity: `{gamepad_identity()}`.",
            "InputPlumber 0.75.2 src/input/manager.rs:1232-1267 admits virtual Bluetooth (bus 0005); installed 60-xbox_one_gamepad.yaml matches 045e:02d1 and sets auto_manage:true. This is a test route, not a product route.",
            "Seat P2 event admission does not prove game navigation; RetroArch normally reserves P1.",
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
        report += ["", "| clock | min | median | max |", "|---|---:|---:|---:|"]
        for key in sorted(
            {key for row in rows for key in row if key.startswith(("cpu/", "gpu/"))}
        ):
            clocks = [
                value
                for row in rows
                if row["phase"] == "measurement"
                for item, value in row.items()
                if item == key and isinstance(value, int)
            ]
            if clocks:
                report.append(
                    f"| {key} | {min(clocks)} | {summarize(clocks)['median']} | {max(clocks)} |"
                )
        report += [
            "",
            "## Cemu evidence",
            "",
            cemu_evidence,
            "",
        ]
        (folder / "report.md").write_text(
            not_measured_report(error, gate.timings, safety.summary())
            if error
            else "\n".join(report)
        )
    if error:
        raise RuntimeError(f"{error}; report: {folder / 'report.md'}")
    print(folder / "report.md", flush=True)


def run_ab(rpc: Rpc, args: argparse.Namespace) -> None:
    require_idle(rpc)
    original = rpc.call("app.launch-settings.snapshot", {"gameId": args.game})
    selected = original.get("selectedProfile")
    args.output.mkdir(parents=True, exist_ok=False)
    os.chmod(args.output, 0o700)
    write_json(args.output / "profiles-before.json", original)
    expected_revision = record(original["revisions"])["games"]
    try:
        for index, variant in enumerate((args.a, args.b), 1):
            name, profile = variant.split("=", 1)
            if not name or not profile:
                raise ValueError("A/B name and profile must be nonempty")
            snapshot = rpc.call("app.launch-settings.snapshot", {"gameId": args.game})
            if record(snapshot["revisions"])["games"] != expected_revision:
                raise RuntimeError(
                    "Concurrent library edit: refusing to overwrite profile selection"
                )
            payload: Record = {
                "gameId": args.game,
                "expectedRevision": expected_revision,
            }
            if profile != "-":
                payload["profileId"] = profile
            changed = rpc.call("app.launch-settings.profile.select", payload)
            expected_revision = changed["games"]
            run(rpc, args, args.output / str(index), name)
    finally:
        snapshot = rpc.call("app.launch-settings.snapshot", {"gameId": args.game})
        write_json(args.output / "profiles-before-restore.json", snapshot)
        if record(snapshot["revisions"])["games"] != expected_revision:
            raise RuntimeError(
                "Concurrent library edit: profile restore needs administrator review"
            )
        payload = {
            "gameId": args.game,
            "expectedRevision": expected_revision,
        }
        if selected is not None:
            payload["profileId"] = selected
        rpc.call("app.launch-settings.profile.select", payload)
        restored = rpc.call("app.launch-settings.snapshot", {"gameId": args.game})
        write_json(args.output / "profiles-restored.json", restored)
        if restored.get("selectedProfile") != selected:
            raise RuntimeError("Original profile selection was not restored")
    summary = [
        "# A/B",
        "",
        "Original launch profile restored; see `profiles-restored.json`.",
        "",
        "| variant | median | p10 | p1 | min | report |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for index, variant in enumerate((args.a, args.b), 1):
        stats = record(json.loads((args.output / str(index) / "fps.json").read_text()))
        summary.append(
            f"| {variant.split('=', 1)[0]} | {stats['median']} | {stats['p10']} | {stats['p1']} | {stats['min']} | [{index}]({index}/report.md) |"
        )
    summary += ["", *aggregate_gate_sections(args.output)]
    (args.output / "report.md").write_text("\n".join(summary) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["run", "soak", "ab", "save-proof"])
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
    parser.add_argument(
        "--reference",
        type=Path,
        required=True,
        help="Per-game numeric title/loading/gameplay reference",
    )
    parser.add_argument(
        "--gate-timeout",
        type=float,
        default=120,
        help="Deadline for each game-state gate in seconds",
    )
    parser.add_argument("--gate-poll", type=float, default=1)
    parser.add_argument("--capture-user", default="korri")
    parser.add_argument("--runtime-dir", type=Path, default=Path("/run/user/1000"))
    parser.add_argument("--wayland-display", default="korri-wayland")
    parser.add_argument(
        "--save-objects", type=Path, default=Path("/var/lib/korrid/saves/objects")
    )
    parser.add_argument("--spot", default="Unspecified; validation launch only")
    parser.add_argument("--cemu-log", type=Path)
    parser.add_argument(
        "--save-root",
        type=Path,
        help="Exact saveRoot from real launch declaration, for save proof/read verification",
    )
    parser.add_argument(
        "--controller-profile",
        type=Path,
        help="Existing Cemu controllerProfiles/*.xml in the test account",
    )
    parser.add_argument(
        "--controller-template",
        type=Path,
        help="Cemu-created bench profile selecting P2; copied for this run and restored",
    )
    parser.add_argument(
        "--repeat-input-until-loading",
        action="store_true",
        help="Repeat the native advance script until loading is observed, at most 60 seconds",
    )
    parser.add_argument(
        "--require-save-read",
        type=Path,
        help="Require actual Cemu read of this path relative to --save-root before warmup",
    )
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
        or not 5 <= args.gate_timeout <= 600
        or not 0.2 <= args.gate_poll <= 5
    ):
        parser.error("Invalid port or duration")
    if args.mode == "soak":
        args.seconds = args.minutes * 60
    if not args.process_name or "/" in args.process_name:
        parser.error("process-name must be a nonempty basename fragment")
    if bool(args.controller_profile) != bool(args.controller_template) or (
        args.controller_profile and not args.cemu_log
    ):
        parser.error(
            "Controller replacement requires both profile paths and --cemu-log"
        )
    if args.repeat_input_until_loading and not args.input_script:
        parser.error("--repeat-input-until-loading requires --input-script")
    if args.require_save_read and (
        not args.save_root
        or args.require_save_read.is_absolute()
        or ".." in args.require_save_read.parts
    ):
        parser.error(
            "--require-save-read needs --save-root and a safe relative file path"
        )
    if args.input_script:
        read_script(args.input_script)  # validate before creating any device or session
    rpc = Rpc(args.port, args.capability_file)
    # One bench per device. The lock file contains no capability or runtime state.
    with Path("/run/korri-cemu-bench.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.mode == "save-proof":
            if not args.save_root or not args.input_script:
                parser.error("save-proof requires --save-root and --input-script")
            require_idle(rpc)
            confirm_native_idle()
            args.output.mkdir(parents=True, exist_ok=False)
            os.chmod(args.output, 0o700)
            safety = SaveSafety(
                rpc, args.game, args.runner, args.save_objects, args.output
            )
            proof = SaveProof(args.save_root, args.output)
            failure = ""
            try:
                safety.preflight()
                args.defer_save_restore = True
                args.warmup, args.seconds = 1, 1
                args.save_action = proof.save
                run(rpc, args, args.output / "write", "save route")
                args.save_action = proof.verify_loaded
                args.before_input = proof.watch_reads
                run(rpc, args, args.output / "reload", "load newly written save")
            except (
                OSError,
                ValueError,
                TypeError,
                RuntimeError,
                subprocess.SubprocessError,
                KeyboardInterrupt,
            ) as exc:
                failure = str(exc) or type(exc).__name__
            finally:
                if proof.watch:
                    proof.watch.close()
                try:
                    require_idle(rpc)
                    confirm_native_idle()
                    safety.restore()
                except (
                    OSError,
                    ValueError,
                    TypeError,
                    RuntimeError,
                    subprocess.SubprocessError,
                ) as exc:
                    failure = failure or str(exc)
                (args.output / "report.md").write_text(
                    "\n".join(
                        [
                            "# In-game save proof",
                            "",
                            "Status: "
                            + (
                                "unproven: " + failure
                                if failure
                                else "PASS: new game_data.sav written, read by Cemu after relaunch, and gameplay gated"
                            ),
                            "",
                            safety.summary(),
                            "",
                            *aggregate_gate_sections(args.output),
                        ]
                    )
                )
                if failure:
                    for result in args.output.rglob("fps.json"):
                        result.unlink()
                    for result in args.output.glob("*/report.md"):
                        timing_file = result.parent / "gate.json"
                        timings = (
                            record(json.loads(timing_file.read_text())).get(
                                "timings", {}
                            )
                            if timing_file.exists()
                            else {}
                        )
                        result.write_text(
                            not_measured_report(
                                failure,
                                cast(dict[str, float | None], timings),
                                safety.summary(),
                            )
                        )
            if failure:
                raise RuntimeError(failure)
            print(args.output / "report.md", flush=True)
            return
        if args.mode != "ab":
            run(rpc, args, args.output, args.variant)
            return
        if not args.a or not args.b or "=" not in args.a or "=" not in args.b:
            parser.error("ab requires --a NAME=PROFILE --b NAME=PROFILE")
        try:
            run_ab(rpc, args)
        except (
            OSError,
            ValueError,
            TypeError,
            RuntimeError,
            subprocess.SubprocessError,
            KeyboardInterrupt,
        ) as exc:
            if args.output.is_dir():
                (args.output / "report.md").write_text(
                    not_measured_report(
                        str(exc) or type(exc).__name__,
                        {},
                        "See per-run save-safety.json and profiles-before-restore.json; profile restoration must be verified.",
                    )
                    + "\n".join(aggregate_gate_sections(args.output))
                )
            raise


if __name__ == "__main__":

    def interrupted(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    main()
