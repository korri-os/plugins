#!/usr/bin/env nix
#! nix shell nixpkgs#python3 --command python3
"""Check real packaged quest startup, not gameplay or physical acceptance."""

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def main():
    engine, payload = sys.argv[1:]
    for name in ["perlshaws-problems.solarus", "voadi.solarus"]:
        quest = Path(payload) / "cartridges" / name
        if not quest.is_file():
            raise ValueError("missing packaged quest: " + name)
        with tempfile.TemporaryDirectory() as directory:
            account = Path(directory)
            log = account / "startup.log"
            with log.open("wb") as stream:
                process = subprocess.Popen(
                    [engine, "-no-video", "-no-audio", str(quest)],
                    cwd=account,
                    env={**os.environ, "HOME": str(account)},
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )
                try:
                    process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    pass
                else:
                    raise ValueError(
                        f"quest exited during startup: {name}: {log.read_text(errors='replace')}"
                    )
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
            diagnostics = log.read_text(errors="replace")
            error_file = account / "error.txt"
            if error_file.exists():
                diagnostics += error_file.read_text(errors="replace")
            if re.search(r"\b(?:Error|Fatal):|No quest was found", diagnostics):
                raise ValueError(f"quest startup diagnostics: {name}: {diagnostics}")
            print(
                f"Verified packaged headless startup without script diagnostics: {name}"
            )


if __name__ == "__main__":
    main()
