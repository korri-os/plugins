#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3
"""File-backed GitHub Release API for publisher subprocess tests. No network."""

import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

root = Path(os.environ["RELEASE_FIXTURE"])
args = sys.argv[1:]
state = json.loads((root / "state.json").read_text())
if args[:2] == ["release", "create"]:
    assert args[args.index("--repo") + 1] == "owner/plugins"
    assert "--draft" in args and "--verify-tag" in args
    state["releases"].append(
        {
            "id": len(state["releases"]) + 1,
            "tag_name": args[2],
            "draft": True,
            "immutable": False,
        }
    )
    (root / "state.json").write_text(json.dumps(state))
    sys.exit(0)
assert args[:3] == ["api", "--hostname", "github.com"], args
args = args[3:]
method = "GET"
if args[:1] == ["--method"]:
    method, args = args[1], args[2:]
url = args[0]
parsed = urlsplit(url)
parts = parsed.path.lstrip("/").split("/")
assert parts[:3] == ["repos", "owner", "plugins"], parts
if parts[3] == "commits":
    result = {"sha": "1" * 40}
elif len(parts) == 4:
    assert parts[3] == "releases"
    page = int(parse_qs(parsed.query)["page"][0])
    result = state["releases"][(page - 1) * 100 : page * 100]
elif parts[4] == "tags":
    result = next(r for r in state["releases"] if r["tag_name"] == parts[5])
    if result["draft"]:
        sys.exit("published release not found")
elif parts[4] == "assets":
    sys.stdout.buffer.write((root / parts[5]).read_bytes())
    sys.exit(0)
elif method == "PATCH":
    result = next(r for r in state["releases"] if r["id"] == int(parts[4]))
    assert args[args.index("--field") + 1] == "draft=false"
    result.update(draft=False, immutable=True)
    (root / "state.json").write_text(json.dumps(state))
else:
    identity = int(parts[4])
    assert parts[5] == "assets"
    if method == "POST":
        data = Path(args[args.index("--input") + 1]).read_bytes()
        name = parse_qs(parsed.query)["name"][0]
        if any(a["name"] == name and a["release"] == identity for a in state["assets"]):
            sys.exit("asset already exists")
        asset_id = len(state["assets"]) + 10
        result = {
            "id": asset_id,
            "name": name,
            "state": "uploaded",
            "size": len(data),
            "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
            "release": identity,
        }
        state["assets"].append(result)
        (root / str(asset_id)).write_bytes(data)
        (root / "state.json").write_text(json.dumps(state))
        if state.get("fail_after_upload"):
            sys.exit("connection lost after server accepted the upload")
    else:
        page = int(parse_qs(parsed.query)["page"][0])
        result = [a for a in state["assets"] if a["release"] == identity][
            (page - 1) * 100 : page * 100
        ]
if isinstance(result, list) and result and "release" in result[0]:
    # Other clients can download between requests. That does not change bytes.
    result = [dict(asset, download_count=os.getpid()) for asset in result]
print(json.dumps(result))
