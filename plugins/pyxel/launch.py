"""Native selected-file bootstrap. This does not restrict Python permissions."""

import sys
import zipfile
from pathlib import Path, PurePosixPath

import pyxel
from pyxel import cli


def validate_startup(content):
    """Match cli.py's one-directory startup marker, before any Python executes."""
    with zipfile.ZipFile(content) as archive:
        files = archive.infolist()
        names = [entry.filename for entry in files]
        if len(names) != len(set(names)):
            raise SystemExit("Ambiguous duplicate Pyxel archive entries")
        markers = [
            entry
            for entry in files
            if not entry.is_dir()
            and len(PurePosixPath(entry.filename).parts) == 2
            and PurePosixPath(entry.filename).name == pyxel.APP_STARTUP_SCRIPT_FILE
        ]
        if len(markers) != 1:
            raise SystemExit("Pyxel requires exactly one native startup marker")
        marker = markers[0]
        startup = PurePosixPath(archive.read(marker).decode("utf-8").strip())
        if (
            startup.is_absolute()
            or ".." in startup.parts
            or not startup.parts
            or "\\" in str(startup)
        ):
            raise SystemExit(
                "Pyxel startup marker must stay inside its selected application"
            )
        target = str(PurePosixPath(marker.filename).parent / startup)
        if target not in names or archive.getinfo(target).is_dir():
            raise SystemExit("Pyxel startup marker does not name an application file")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: korri-pyxel /absolute/selected.pyxapp")
    content = Path(sys.argv[1])
    if not content.is_absolute() or not content.is_file():
        raise SystemExit("Pyxel requires an existing absolute content file")
    if content.suffix.lower() != ".pyxapp":
        raise SystemExit("Pyxel requires .pyxapp content")

    validate_startup(content)

    # init() itself changes cwd to the *calling script's* directory. Never
    # wrap it: doing so would break native sibling-resource lookup. Apply
    # fullscreen at the three public presentation entry points instead.
    presented = False

    def fullscreen_on_first_frame(function):
        def present(*args, **kwargs):
            nonlocal presented
            if not presented:
                pyxel.fullscreen(True)
                presented = True
            return function(*args, **kwargs)

        return present

    for name in ("run", "show", "flip"):
        setattr(pyxel, name, fullscreen_on_first_frame(getattr(pyxel, name)))
    # Keep upstream startup marker, sibling-import, resource and argv behavior.
    sys.argv = ["pyxel", "play", str(content)]
    cli.cli()


if __name__ == "__main__":
    main()
