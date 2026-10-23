"""Read-only Linux process identity and telemetry. Never write policy sysfs."""

import os
from pathlib import Path

from rpc import Record


def processes() -> dict[int, Record]:
    found: dict[int, Record] = {}
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            found[int(proc.name)] = {
                "exe": os.readlink(proc / "exe"),
                "cgroup": (proc / "cgroup").read_text(),
                # starttime differentiates PID reuse. comm can contain spaces/parens.
                "start_ticks": (proc / "stat")
                .read_text()
                .rsplit(")", 1)[1]
                .split()[19],
            }
        except (OSError, IndexError):
            continue
    return found


def members(unit: str) -> dict[int, Record]:
    return {
        pid: item
        for pid, item in processes().items()
        if any(
            line.split(":", 2)[-1].rstrip("/").endswith("/" + unit)
            for line in str(item["cgroup"]).splitlines()
        )
    }


def number(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def telemetry(tree: dict[int, Record]) -> dict[str, int | None]:
    values: dict[str, int | None] = {}
    for policy in Path("/sys/devices/system/cpu/cpufreq").glob("policy*"):
        values[f"cpu/{policy.name}/kHz"] = number(policy / "scaling_cur_freq")
    for gpu in Path("/sys/class/devfreq").glob("*gpu*"):
        values[f"gpu/{gpu.name}/Hz"] = number(gpu / "cur_freq")
    for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
        try:
            name = (zone / "type").read_text().strip()
        except OSError:
            name = zone.name
        values[f"thermal/{zone.name}/{name}/mC"] = number(zone / "temp")
    rss, swap = [], []
    for pid in tree:
        try:
            status = Path(f"/proc/{pid}/status").read_text().splitlines()
        except OSError:
            continue
        for line in status:
            if line.startswith("VmRSS:"):
                rss.append(int(line.split()[1]))
            if line.startswith("VmSwap:"):
                swap.append(int(line.split()[1]))
    values["session/rss_kB"] = sum(rss) if rss else None
    values["session/swap_kB"] = sum(swap) if swap else None
    return values


def renderer_context(pid: int) -> tuple[dict[str, str], int, int, int]:
    """Join the mount namespace, retaining only native X authentication selectors.

    XRes sees the renderer's PID in Xwayland's private PID namespace, not the
    host PID used by nsenter. Do not retain or log the rest of its environment.
    """
    proc = Path(f"/proc/{pid}")
    environment = os.environ.copy()
    for selector in ("DISPLAY", "XAUTHORITY", "XDG_RUNTIME_DIR"):
        environment.pop(selector, None)
    for entry in (proc / "environ").read_bytes().split(b"\0"):
        key, _, value = entry.partition(b"=")
        if key in (b"DISPLAY", b"XAUTHORITY", b"XDG_RUNTIME_DIR"):
            environment[os.fsdecode(key)] = os.fsdecode(value)
    namespace_pid = pid
    for line in (proc / "status").read_text().splitlines():
        if line.startswith("NSpid:"):
            namespace_pid = int(line.split()[-1])
    stat = proc.stat()
    return environment, namespace_pid, stat.st_uid, stat.st_gid
