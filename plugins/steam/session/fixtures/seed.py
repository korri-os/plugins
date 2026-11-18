"""A steam-arm64-seed fixture: records what the seed sees, then installs a client."""
import json
import os
import sys
from pathlib import Path

home = Path(os.environ["STEAM_HOME"])
if "--relink" in sys.argv:
    # The real --relink is exercised by test_bootstrap.py.
    with (home / "relinks").open("a") as stream:
        stream.write("relink\n")
    sys.exit(0)
(home / "seed.json").write_text(json.dumps({"FEX_ROOTFS": os.environ.get("FEX_ROOTFS")}))
client = home / "steamrtarm64/steam"
client.parent.mkdir(parents=True, exist_ok=True)
client.touch()
client.chmod(0o755)
