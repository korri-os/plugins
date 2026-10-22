"""Use Core's real admission evaluator and sandbox/executor, never install a plugin."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

package, host, korrid, record = sys.argv[1:]
manifest = json.loads((Path(package) / "manifest.json").read_text())
assert manifest["publisher"] == {"namespace": "@korri"}
assert manifest["sources"] == ["plugin.ts"]
assert manifest["files"] == {"cemu": manifest["packages"]["cemu"] + "/bin/cemu"}
assert manifest["services"] == {} and manifest["ports"] == {}
receipt = json.loads(subprocess.check_output([
    host, "seed", package, "https://cache.example.invalid"], text=True, timeout=30))
assert receipt["id"] == "@korri:cemu"
assert receipt["desired"] == {"state": "Enabled"}
with tempfile.TemporaryDirectory(prefix="cemu-contract-") as work:
    for account in ("Player One", "Player Two"):
        home = str(Path(work) / account)
        saves = str(Path(work) / account / "saves/game")
        content = "/games/Title '; $(exit 21).wua"
        launch = dict(runnerId="@korri:cemu/cemu", program=record, contentPath=content,
                      accountRoot=home, saveRoot=saves, cacheRoot=work + "/cache",
                      files=manifest["files"], artifacts={})
        def run(value):
            return subprocess.run([korrid, "plugin-run", package + "/plugin.ts", json.dumps(value),
                                   '{"modifiers":[]}', "fixture"],
                                  capture_output=True, text=True, timeout=30)
        result = run(launch)
        assert result.returncode == 0, result.stderr
        assert result.stdout.split("\0") == ["-f", "-g", content, "--mlc", saves + "/mlc01",
                                              home, home + "/.local/share", home, ""]
        assert Path(saves + "/mlc01/usr/save").is_dir()
        for invalid in [dict(runnerId="wrong"), dict(corePath="/core.so"),
                        dict(contentPath="relative"), dict(saveRoot="relative"),
                        dict(overrides={"settings": {"fullscreen": False}})]:
            rejected = run(launch | invalid)
            assert rejected.returncode != 0 and not rejected.stdout
print("Cemu manifest, host admission and real sandbox launch passed for two accounts")
