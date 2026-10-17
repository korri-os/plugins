#!@python@/bin/python3
"""Launch a .qst with native state in an account-owned directory."""

import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile

ENGINE = "@engine@/bin/zplayer"
RESOURCES = Path("@engine@/share/zquestclassic")
# Korri's input daemon routes the device's own controls to this seat. The
# player selects its gamepad by this name, whatever Allegro's device order.
SEAT = "Korri Seat P1"
# Korri's seats report a wired Xbox 360 pad. In Linux's button order, upstream's
# defaults put Start on the left-stick click (10) and Extra2 on Start (8).
SEAT_BUTTONS = {"btn_s": 8, "btn_ex2": 10}
# Upstream resets this control scheme on every start.
RESET_SCHEME = "Default"


def prepare_resources(directory: Path) -> None:
    # Upstream looks up these files relative to cwd, alongside writable zc.cfg,
    # saves/, replays/ and logs. Link only immutable shipped resources, not state.
    for resource in RESOURCES.iterdir():
        target = directory / resource.name
        if target.is_symlink():
            previous = Path(os.readlink(target))
            if previous == resource:
                continue
            if not (
                str(previous).startswith("/nix/store/")
                and previous.parent.name == "zquestclassic"
                and previous.name == resource.name
            ):
                raise ValueError(f"Refusing to replace user resource: {target}")
        elif target.exists():
            raise ValueError(f"Refusing to replace user resource: {target}")
        # A changed package must not leave a half-updated resource link.
        with tempfile.TemporaryDirectory(prefix=".zquest-", dir=directory) as temp:
            link = Path(temp) / resource.name
            link.symlink_to(resource, target_is_directory=resource.is_dir())
            link.replace(target)


def _section(line: str) -> str | None:
    text = line.strip()
    if text.startswith("[") and text.endswith("]"):
        return text[1:-1].strip()
    return None


def _key(line: str) -> str | None:
    text = line.strip()
    name, separator, _ = text.partition("=")
    if not separator or text.startswith("#"):
        return None
    return name.strip()


def _lines(path: Path) -> list[str]:
    return path.read_text().splitlines() if path.exists() else []


def config_sections(path: Path) -> list[str]:
    sections = [_section(line) for line in _lines(path)]
    return list(dict.fromkeys(name for name in sections if name is not None))


def read_config(path: Path, section: str, key: str) -> str | None:
    current, value = "", None
    for line in _lines(path):
        name = _section(line)
        if name is not None:
            current = name
        elif current == section and _key(line) == key:
            value = line.partition("=")[2].strip()
    return value


def set_config(path: Path, section: str, values: dict[str, object]) -> None:
    """Set keys in a native config file and keep every other line."""
    lines = _lines(path)
    current, end, replaced = "", None, set()
    for index, line in enumerate(lines):
        name = _section(line)
        if name is not None:
            current = name
            if name == section:
                end = index + 1
            continue
        if current != section:
            continue
        if line.strip():
            end = index + 1
        key = _key(line)
        if key in values:
            lines[index] = f"{key} = {values[key]}"
            replaced.add(key)
    missing = [
        f"{key} = {value}" for key, value in values.items() if key not in replaced
    ]
    if missing and end is None:
        lines += [f"[{section}]", *missing]
    elif missing:
        lines[end:end] = missing
    # Replace whole files so an interrupted launch cannot truncate settings.
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as temporary:
        try:
            temporary.write("".join(f"{line}\n" for line in lines))
            temporary.close()
            if path.exists():
                os.chmod(temporary.name, stat.S_IMODE(path.stat().st_mode))
            os.replace(temporary.name, path)
        except BaseException:
            os.unlink(temporary.name)
            raise


def configure(directory: Path) -> None:
    """Apply Korri's handheld settings to the player's native configuration."""
    settings = directory / "zc.cfg"
    controls = directory / "controls.cfg"
    # Korri stops the game, and its devices have no pointer or keyboard to work
    # the system menu, so touch and the gamepad menu button must not open it.
    # Marking upstream's upload question as asked leaves replay_upload as is;
    # upstream's default is off, so this gives no consent.
    set_config(settings, "zeldadx", {"replay_upload_prompt": 1, "clicktofreeze": 0})
    # Upstream selects a quest's scheme, then the global scheme, then
    # "Default". It resets "Default" on start, so these keys go elsewhere.
    # "Custom" is the scheme upstream creates on its own first start.
    schemes = [name for name in config_sections(controls) if name != RESET_SCHEME]
    if read_config(settings, "Controls", "global_control_scheme") not in schemes:
        set_config(settings, "Controls", {"global_control_scheme": "Custom"})
        if "Custom" not in schemes:
            schemes.append("Custom")
    values: dict[str, object] = {"btn_menu": 0, "joystick_name": SEAT, **SEAT_BUTTONS}
    for scheme in schemes:
        set_config(controls, scheme, values)


def launch(quest: Path, directory: Path) -> None:
    quest = quest.resolve(strict=True)
    if quest.suffix.lower() != ".qst":
        raise ValueError("ZQuest Classic requires an unpacked .qst file.")
    # Nonblocking open lets special-file inputs fail instead of hanging on a FIFO.
    descriptor = os.open(quest, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("The quest must be a regular file.")
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    # User-approved identity: Core discovery/scanner.rs hashes the whole file.
    save_name = f"sha256:{digest}.sav"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = directory.resolve(strict=True)
    lock = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError(
                "ZQuest Classic is already running for this account."
            ) from None
        prepare_resources(directory)
        configure(directory)
        os.chdir(directory)
        # The native binary normally switches cwd into its read-only package.
        os.environ["ZC_DISABLE_CHDIR"] = "1"
        # Allegro's native config selects software MIDI. Autodetection crashes
        # upstream when a device has no ALSA sequencer, such as the Mini V2.
        os.environ["ALLEGRO"] = "@audio@"
        os.set_inheritable(lock, True)
        os.execv(ENGINE, [ENGINE, "-fullscreen", "-standalone", str(quest), save_name])
    finally:
        os.close(lock)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "quest", type=Path, help="Unpacked quest; keep companion music beside it"
    )
    parser.add_argument("directory", type=Path, help="Account-owned ZQuest directory")
    args = parser.parse_args()
    try:
        launch(args.quest, args.directory)
    except (OSError, ValueError) as error:
        print(f"zquest-classic: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
