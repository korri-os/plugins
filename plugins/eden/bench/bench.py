"""Administrative FPS collector. Launch/stop only through the library RPC."""

import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path

from eden import evidence, map_signal, native_config, selected_backend
from input import read_events, replay
from linux import members, processes, renderer_context, telemetry
from metrics import fps_window, read_presentations, summarize
from rpc import Record, Rpc, RpcFailure

EMULATORS = ("eden", "cemu", "retroarch", "ryujinx")


def process_name_matches(executable: str, allowed_names: tuple[str, ...]) -> bool:
    basename = Path(executable).name.lower()
    return any(name in basename for name in allowed_names)


def stop(rpc: Rpc, launch: str) -> None:
    for _ in range(40):
        try:
            result = rpc.call("app.session.stop", {"expectedLaunchId": launch})
        except RpcFailure as exc:
            if exc.code in ("NoActiveSession", "SessionCompleted"):
                return
            if exc.code == "StaleLaunchIdentity":
                result = rpc.call("app.session.cancel", {"expectedLaunchId": launch})
            else:
                raise
        if result.get("phase") == "stopped":
            return
        time.sleep(0.25)
    raise RuntimeError("Exact session stop timed out")


def collect(args: argparse.Namespace) -> None:
    events = read_events(args.input_script) if args.input_script else []
    if args.eden_log and args.eden_log.exists():
        raise ValueError(
            "Archive the previous Eden log; require a new log for this launch"
        )
    before = processes()
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    launch, failure, cleanup_failure, unit = "", "", "", ""
    reservation_requested = False
    rows: list[dict[str, int | None]] = []
    stats: dict[str, float] = {}
    proof: list[str] = []
    backend = (
        "not applicable (non-Eden validation)" if not args.eden_log else "unproven"
    )
    selection: Record = {}
    runtime: list[Record] = []
    config: Path | None = None
    seen: dict[int, Record] = {}
    chain = {"gamescope": False, "bubblewrap": False}
    renderer = 0
    observer: subprocess.Popen[bytes] | None = None
    rpc: Rpc | None = None
    values: list[int] = []
    window = 0
    started_ns = time.time_ns()
    csv_path = args.output / "present.csv"
    csv_output = csv_path.open("wb")
    observer_log = (args.output / "observer.log").open("wb")
    try:
        if any(
            process_name_matches(str(item["exe"]), EMULATORS)
            for item in before.values()
        ):
            raise RuntimeError("An emulator is running; wait for the other worker")
        rpc = Rpc(args.port, args.capability_file)
        rpc.require_idle()
        reservation_requested = True
        reserved = rpc.call("app.session.reserve", {"gameId": args.game})
        launch = str(reserved.get("launchId", ""))
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", launch):
            raise ValueError("Invalid reserved launch identity")
        unit = f"korri-game-{launch}.service"
        rpc.call(
            "app.session.start",
            {"gameId": args.game, "runnerId": args.runner, "expectedLaunchId": launch},
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            tree = members(unit)
            seen.update(tree)
            chain["gamescope"] |= any(
                "gamescope" in Path(str(item["exe"])).name for item in tree.values()
            )
            chain["bubblewrap"] |= any(
                "bwrap" in Path(str(item["exe"])).name for item in tree.values()
            )
            for pid, item in tree.items():
                if args.process_name.lower() in Path(str(item["exe"])).name.lower():
                    context = renderer_context(pid)
                    if context[0].get("DISPLAY"):
                        renderer = pid
                        break
            if renderer:
                break
            time.sleep(0.25)
        if not renderer or not chain["gamescope"]:
            raise RuntimeError("No exact-session X11 renderer under Gamescope")
        environment, namespace_pid, uid, gid = renderer_context(renderer)
        renderer_identity = tree[renderer]
        if args.eden_log:
            config = native_config(renderer)
            selection = selected_backend(config, args.eden_title_id)
        observer = subprocess.Popen(
            [
                "nsenter",
                "--target",
                str(renderer),
                "--mount",
                "--setuid",
                str(uid),
                "--setgid",
                str(gid),
                "--",
                os.environ["KORRI_EDEN_PRESENT_OBSERVER"],
                str(namespace_pid),
            ],
            env=environment,
            stdout=csv_output,
            stderr=observer_log,
        )
        if events:
            replay(events, lambda: bool(members(unit)))
        measurement_start = time.monotonic() + 100
        end = measurement_start + args.seconds
        with (args.output / "telemetry.jsonl").open("w") as output:
            while time.monotonic() < end:
                if observer.poll() is not None:
                    raise RuntimeError("X Present observer exited; see observer.log")
                tree = members(unit)
                seen.update(tree)
                if tree.get(renderer) != renderer_identity:
                    raise RuntimeError("Exact renderer exited or was replaced")
                now = time.monotonic()
                row = telemetry(tree)
                rows.append(row)
                output.write(
                    json.dumps(
                        {
                            "monotonic_s": now,
                            "phase": "measurement"
                            if now >= measurement_start
                            else "warmup",
                            **row,
                        }
                    )
                    + "\n"
                )
                output.flush()
                if args.eden_log and now >= measurement_start:
                    runtime.append(
                        {
                            "pid": renderer,
                            "monotonic_s": now,
                            **map_signal(Path(f"/proc/{renderer}/maps").read_text()),
                        }
                    )
                time.sleep(min(1, max(0, end - time.monotonic())))
        # Drain delivery latency; UST, not receipt time, bounds the measurement.
        time.sleep(0.15)
        observer.terminate()
        observer.wait(timeout=3)
        csv_output.flush()
        window, values = fps_window(
            read_presentations(csv_path), measurement_start, args.seconds
        )
        stats = summarize(values)
        (args.output / "fps.json").write_text(
            json.dumps(
                {
                    "source": "X11 Present CompleteNotify/Pixmap",
                    "start_monotonic_s": measurement_start,
                    "seconds": args.seconds,
                    "window": window,
                    "fps_bins": values,
                    **stats,
                },
                indent=2,
            )
            + "\n"
        )
        if args.eden_log:
            if not config or selected_backend(config, args.eden_title_id) != selection:
                raise ValueError("Native backend selection changed during the run")
            proof, backend = evidence(args.eden_log, started_ns, selection, runtime)
            if backend.startswith("unproven"):
                raise ValueError("Backend evidence unproven; see backend.json")
    # Any failure becomes the report's failure line; cleanup below must still run.
    except (Exception, KeyboardInterrupt) as exc:  # noqa: BLE001
        failure = str(exc) or type(exc).__name__
    finally:
        if observer and observer.poll() is None:
            observer.terminate()
            try:
                observer.wait(timeout=3)
            except subprocess.TimeoutExpired:
                observer.kill()
                observer.wait()
                cleanup_failure = "Owned observer required SIGKILL"
        csv_output.close()
        observer_log.close()
        if rpc and launch and unit:
            try:
                stop(rpc, launch)
                rpc.require_idle(own_launches={launch})
            # A cleanup error is recorded in the report, never raised past it.
            except Exception as exc:  # noqa: BLE001
                cleanup_failure = str(exc)
        elif reservation_requested:
            cleanup_failure = (
                "Reservation identity unknown; inspect session status before retrying"
            )
        deadline = time.monotonic() + 5
        remaining = members(unit) if unit else {}
        while remaining and time.monotonic() < deadline:
            time.sleep(0.1)
            remaining = members(unit)
        leftovers = {
            pid: item
            for pid, item in processes().items()
            if item != before.get(pid)
            and process_name_matches(
                str(item["exe"]), (*EMULATORS, "gamescope", "bwrap")
            )
        }
        cleanup = {
            "remaining_cgroup": remaining,
            "new_emulators_or_wrappers": leftovers,
            "observer_remaining": bool(observer and observer.poll() is None),
            "error": cleanup_failure,
        }
        idle_observations = rpc.idle_observations if rpc else []
        (args.output / "idle.json").write_text(
            json.dumps(idle_observations, indent=2) + "\n"
        )
        (args.output / "cleanup.json").write_text(json.dumps(cleanup, indent=2) + "\n")
        (args.output / "processes.json").write_text(json.dumps(seen, indent=2) + "\n")
        (args.output / "backend.json").write_text(
            json.dumps(
                {"backend": backend, "selection": selection, "runtime": runtime},
                indent=2,
            )
            + "\n"
        )
        if remaining or leftovers or cleanup_failure or cleanup["observer_remaining"]:
            failure = failure or "Cleanup incomplete; no global kill attempted"
        peaks: dict[str, int] = {}
        floors: dict[str, int] = {}
        for row in rows:
            for name, value in row.items():
                if value is not None:
                    peaks[name] = max(peaks.get(name, value), value)
                    floors[name] = min(floors.get(name, value), value)
        report = [
            f"# {os.uname().nodename}: Eden bench",
            "",
            f"Status: {'FAILED: ' + failure if failure else 'PASS (collection; no Bonneton/navigation acceptance claim)'}",
            f"Game `{args.game}`; runner `{args.runner}`; launch `{launch}`.",
            f"Booted system: `{os.path.realpath('/run/booted-system')}`; kernel `{os.uname().release}`.",
            "",
            "## Measurement",
            "",
            "Source: game-window X11 Present CompleteNotify/Pixmap; Skip excluded. Neither Eden's counter nor MangoHud.",
            "XRes server-owned PID selects only this renderer's windows inside Gamescope's Xwayland.",
            "Discard 100 s after input replay; one-second FPS bins, zero bins included; nearest-rank p10/p1.",
            "This counts game presentations to Gamescope, not compositor Hz, simulation speed or physical panel scanout.",
            f"Window: {window}; duration: {args.seconds} s; bins: {len(values)}.",
            f"Input script: {'replayed (position unverified)' if events else 'none; trivial launch only'}.",
            "",
            "| median FPS | p10 FPS | p1 FPS |",
            "|---:|---:|---:|",
            "| "
            + " | ".join(
                f"{stats[name]:.2f}" if name in stats else "unavailable"
                for name in ("median", "p10", "p1")
            )
            + " |",
            "",
            "## Launch and cleanup",
            "",
            f"Korrid exact session: `{unit}`; renderer host PID: {renderer}. Gamescope observed: {chain['gamescope']}.",
            "Bubblewrap: "
            + (
                "observed (not a security acceptance test)."
                if chain["bubblewrap"]
                else "absent — core gap korri-os/korri#184 (ADR 0015 unimplemented). Not sandbox acceptance, not a bench failure."
            ),
            f"Exact cgroup empty: {not remaining}; no new emulator/wrapper leftovers: {not leftovers}; observer remaining: {cleanup['observer_remaining']}.",
            f"Cleanup error: {cleanup_failure or 'none'}. See cleanup.json and processes.json.",
            "No env injection, wrapper bypass, policy writes, plugin installation or global kills. Normal korrid play/save effects apply.",
            "Raw evidence on device: present.csv, observer.log, telemetry.jsonl, fps.json, cleanup.json, processes.json, idle.json.",
            "",
            "## Retained earlier launch status",
            "",
            *(
                [
                    "The following earlier status was checked against native state, not silently ignored.",
                    "```json",
                    json.dumps(idle_observations, indent=2),
                    "```",
                ]
                if idle_observations
                else ["No retained HostLaunchFailed was accepted as idle."]
            ),
            "",
            "## CPU/GPU clocks, temperature and memory",
            "",
            "One-second read-only samples; peaks include warmup. Null sensors omitted, not replaced with zero.",
            "RSS/swap sum the exact-session processes; shared RSS may be counted more than once.",
            "",
            "| metric (native unit) | minimum | peak |",
            "|---|---:|---:|",
            *[f"| {name} | {floors[name]} | {peaks[name]} |" for name in sorted(peaks)],
            "",
            "## Eden backend evidence",
            "",
            f"Backend: {backend}. See backend.json.",
            *(
                proof
                or ["No Eden log: trivial non-Eden launch or evidence unavailable."]
            ),
            "",
        ]
        (args.output / "report.md").write_text("\n".join(report))
    if failure:
        raise RuntimeError(f"{failure}; report: {args.output / 'report.md'}")
    print(args.output / "report.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "soak"))
    parser.add_argument("--game", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--process-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input-script", type=Path)
    parser.add_argument("--eden-log", type=Path)
    parser.add_argument("--eden-title-id", default="0100000000010000")
    parser.add_argument("--port", type=int, default=39217)
    parser.add_argument(
        "--capability-file",
        type=Path,
        default=Path("/run/korri-portal-credentials/KORRID_RPC_CAPABILITY"),
    )
    parser.add_argument("--minutes", type=int, default=15)
    args = parser.parse_args()
    if (
        not args.process_name
        or "/" in args.process_name
        or not 1 <= args.minutes <= 1440
        or not 1 <= args.port <= 65535
    ):
        parser.error("Invalid renderer basename, duration or localhost port")
    if not re.fullmatch(r"[0-9A-Fa-f]{16}", args.eden_title_id):
        parser.error("Expected a real 16-digit Switch title ID")
    if "eden" in args.process_name.lower() and not args.eden_log:
        parser.error("Eden runs require --eden-log for backend evidence")
    args.seconds = args.minutes * 60 if args.mode == "soak" else 180
    with Path("/run/korri-emulator-bench.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        collect(args)


if __name__ == "__main__":

    def interrupt(_signal: int, _frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    main()
