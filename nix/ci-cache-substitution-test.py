#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 nix
"""Read two published input-addressed outputs into empty isolated Nix stores.

Usage: ci-cache-substitution-test.py CORE_STORE_OUTPUT PUBLISHER_STORE_OUTPUT
Choose input-addressed outputs with no references in the public caches.
Never builds, publishes, signs the host store, or disables signature verification.
Also exports the
reads to temporary file caches and proves unsigned/wrong-key imports fail.
"""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def run(*args, env, check=True):
    return subprocess.run(args, env=env, text=True, capture_output=True, check=check)


def local_store(root):
    return f"local?root={root}"


def registered(store, env):
    return set(run("nix", "path-info", "--store", store, "--all", env=env).stdout.splitlines())


def copy(source, destination, path, env):
    assert not registered(destination, env), "destination store was not empty"
    result = run("nix", "copy", "--from", source, "--to", destination, path, env=env, check=False)
    return result


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    spec = importlib.util.spec_from_file_location(
        "trust_plugin_caches", ROOT / ".github/workflows/trust-plugin-caches.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        env = os.environ | {
            "NIX_CONF_DIR": str(root / "config"),
            "NIX_USER_CONF_FILES": "/dev/null",
            "XDG_CACHE_HOME": str(root / "lookup-cache"),
            "NIX_CONFIG": "experimental-features = nix-command flakes\nbuild-users-group =\n",
        }
        settings = helper.cache_settings(ROOT, env, include_core=True)
        env = helper.configured_environment(settings, env)
        assert len(settings["substituters"]) == 3, "expected stock, Core, and publisher cache owners"
        for index, (url, path) in enumerate(zip(settings["substituters"][1:], sys.argv[1:])):
            metadata_url = url + Path(path).name.split("-", 1)[0] + ".narinfo"
            metadata = urllib.request.urlopen(metadata_url, timeout=60).read().decode()
            assert "\nCA:" not in metadata, "test needs input-addressed outputs, not signature-exempt CA outputs"
            assert f"StorePath: {path}\n" in metadata
            references = next((line.partition(":")[2].strip() for line in metadata.splitlines()
                               if line.startswith("References:")), "")
            assert not references, "choose an output without references to isolate signature refusals"
            destination = local_store(root / f"signed-{index}")
            result = copy(url, destination, path, env)
            if result.returncode:
                sys.exit(result.stderr)
            assert path in registered(destination, env)
            run("nix", "store", "verify", "--store", destination, path, env=env)
            print(f"PASS: signed substitute from {url} into empty isolated store: {path}", flush=True)

            unsigned = root / f"unsigned-{index}"
            run("nix", "copy", "--from", destination, "--to", unsigned.as_uri(), path, env=env)
            for note in unsigned.glob("*.narinfo"):
                note.write_text("\n".join(line for line in note.read_text().splitlines()
                                          if not line.startswith("Sig:")) + "\n")
            key, public = root / f"key-{index}", root / f"public-{index}"
            run("nix-store", "--generate-binary-cache-key", "refusal-test-1", str(key), str(public), env=env)
            key.chmod(0o600)
            run("nix", "store", "sign", "--store", destination, "--recursive", "--key-file", str(key), path, env=env)
            wrong = root / f"wrong-{index}"
            run("nix", "copy", "--from", destination, "--to", wrong.as_uri(), path, env=env)
            for note in wrong.glob("*.narinfo"):
                lines = note.read_text().splitlines()
                assert any(line.startswith("Sig: refusal-test-1:") for line in lines)
                note.write_text("\n".join(line for line in lines
                                          if not line.startswith("Sig:") or line.startswith("Sig: refusal-test-1:")) + "\n")
            for label, source in (("unsigned", unsigned), ("wrong-key", wrong)):
                refused_store = local_store(root / f"refused-{label}-{index}")
                refused = copy(source.as_uri(), refused_store, path, env)
                assert refused.returncode != 0, f"{label} output was accepted"
                assert "signature" in refused.stderr.lower(), refused.stderr
                assert not registered(refused_store, env), f"{label} left registered outputs"
                print(f"PASS: {label} refused with require-sigs=true: {path}", flush=True)
        print("Coverage: two real cached outputs only; this is not proof all CI closures are cached.")


if __name__ == "__main__":
    main()
