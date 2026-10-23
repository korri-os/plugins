"""Eden 0.2.1 evidence, derived from the pinned source. No invented log lines."""

import configparser
import os
import re
from pathlib import Path

from rpc import Record

NATIVE_DEFAULT = "native default (requires effective run log)"

FALLBACKS = (
    "Fastmem is required to natively execute code in a performant manner, falling back to Dynarmic",
    "Program does not utilize 39-bit address space, unable to natively execute code",
    "is incompatible with 4K paging",
    "Using private mappings instead of shared ones",
)


def native_config(pid: int) -> Path:
    # Read only the two native path selectors; never retain the environment.
    entries = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    selectors = {}
    for entry in entries:
        key, _, value = entry.partition(b"=")
        if key in (b"XDG_CONFIG_HOME", b"HOME"):
            selectors[key] = os.fsdecode(value)
    root = selectors.get(b"XDG_CONFIG_HOME")
    if not root:
        root = str(Path(selectors[b"HOME"]) / ".config")
    return Path(root) / "eden/qt-config.ini"


def selected_backend(config: Path, title: str) -> Record:
    if not re.fullmatch(r"[0-9A-Fa-f]{16}", title):
        raise ValueError("Expected a real 16-digit Switch title ID")
    main = configparser.ConfigParser(interpolation=None)
    if not main.read(config):
        raise ValueError("Native launch configuration is unreadable")
    chosen, path = main, config
    custom = config.parent / "custom" / f"{title.upper()}.ini"
    if custom.exists():
        per_game = configparser.ConfigParser(interpolation=None)
        per_game.read(custom)
        if not per_game.getboolean("Cpu", "cpu_backend\\use_global", fallback=True):
            chosen, path = per_game, custom
    # Native defaults ignore the stored value. Only this run's effective log
    # may resolve them; never guess HAS_NCE from the host or another manifest.
    if chosen.getboolean("Cpu", "cpu_backend\\default", fallback=True):
        selected = NATIVE_DEFAULT
    else:
        selected = {"0": "Dynarmic", "1": "NCE"}.get(
            chosen.get("Cpu", "cpu_backend", fallback=""), "unproven"
        )
    return {"config": str(path), "selected": selected}


def map_signal(text: str) -> Record:
    host_memory, code_cache = [], []
    for line in text.splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) < 5:
            continue
        address, permissions = fields[0], fields[1]
        if "x" not in permissions:
            continue
        if "memfd:HostMemory" in line:
            host_memory.append(line)
        # oaknut::CodeBlock uses anonymous RWX on Linux. Dynarmic's full
        # arm64 cache is 128 MiB per core. VMAs may merge. This is a signal,
        # not a uniquely named mapping; other JITs can use anonymous RWX too.
        start, end = (int(part, 16) for part in address.split("-"))
        if (
            len(fields) == 5
            and permissions.startswith("rwx")
            and end - start >= 128 * 1024 * 1024
        ):
            code_cache.append(line)
    return {"executableHostMemory": host_memory, "anonymousLargeRwx": code_cache}


def evidence(
    path: Path, started_ns: int, selection: Record, runtime: list[Record]
) -> tuple[list[str], str]:
    if not path.is_file() or path.stat().st_mtime_ns < started_ns:
        raise ValueError("Eden evidence log missing or stale")
    selected = []
    refused = []
    logged_backend = ""
    for line in path.read_text(errors="replace").splitlines():
        if re.search(r"Render\.Vulkan.*\b(?:Driver|Device|Vulkan):", line):
            selected.append(line)
        match = re.search(r"Cpu\.cpu_backend: (Nce|Dynarmic)\b", line)
        if match:
            logged_backend = "NCE" if match[1] == "Nce" else "Dynarmic"
            selected.append(line)
        if any(warning in line for warning in FALLBACKS):
            # Retain only the known source string, never arbitrary diagnostics.
            refused += [warning for warning in FALLBACKS if warning in line]
    if not re.search(r"Render\.Vulkan.*Vulkan:", "\n".join(selected)):
        raise ValueError("No explicit Vulkan renderer evidence")
    if not re.search(r"Render\.Vulkan.*Driver:", "\n".join(selected)):
        raise ValueError("No explicit Vulkan driver evidence")
    backend = str(selection["selected"])
    from_default = backend == NATIVE_DEFAULT
    if from_default:
        backend = logged_backend
    if (
        refused
        or backend not in ("NCE", "Dynarmic")
        or backend != logged_backend
        or not runtime
    ):
        return (
            selected + refused,
            "unproven (selection/log/runtime disagree or NCE refused)",
        )
    basis = (
        "selected from fresh effective log for native default"
        if from_default
        else "selected"
    )
    if backend == "NCE" and all(
        row.get("executableHostMemory") and not row.get("anonymousLargeRwx")
        for row in runtime
    ):
        return (
            selected,
            f"NCE (inferred: {basis}, not refused, executable HostMemory, no large Dynarmic-like RWX cache)",
        )
    if backend == "Dynarmic" and all(row.get("anonymousLargeRwx") for row in runtime):
        return (
            selected,
            f"Dynarmic (inferred: {basis}, not refused, anonymous RWX code-cache-sized mapping)",
        )
    return selected, "unproven (runtime mapping signal absent or ambiguous)"
