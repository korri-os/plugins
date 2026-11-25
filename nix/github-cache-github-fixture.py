#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3
"""File-backed GitHub Release API for publisher subprocess tests. No network."""

import hashlib
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import parse_qs, urlsplit

root = Path(os.environ["RELEASE_FIXTURE"])
args = sys.argv[1:]
state = json.loads((root / "state.json").read_text())
if args[:2] == ["workflow", "run"]:
    assert args[2:] == ["cache-pages.yml", "--repo", "owner/plugins", "--ref", "main"]
    sys.exit(0)
if args[:2] == ["release", "create"]:
    assert args[args.index("--repo") + 1] == "owner/plugins"
    assert "--draft" in args and "--verify-tag" in args
    if state.get("fail_before_release_create"):
        sys.exit("release creation failed")
    identity = len(state["releases"]) + 1
    state["releases"].append(
        {
            "id": identity,
            "tag_name": args[2],
            "draft": True,
            "immutable": False,
        }
    )
    if state.get("list_lag"):
        # GitHub's release list can omit a fresh release for a while. Hide this
        # one from the next list_lag list requests.
        state.setdefault("hidden", {})[str(identity)] = state.pop("list_lag")
    (root / "state.json").write_text(json.dumps(state))
    if state.get("fail_after_release_create"):
        sys.exit("release appeared while creation failed")
    sys.exit(0)
assert args[:3] == ["api", "--hostname", "github.com"], args
args = args[3:]
method = "GET"
if args[:1] == ["--method"]:
    method, args = args[1], args[2:]
def read_error(key):
    if "read_errors" not in state:
        return
    state.setdefault("reads", []).append(key)
    failures = state["read_errors"].get(key, [])
    failure = failures.pop(0) if failures else None
    (root / "state.json").write_text(json.dumps(state))
    if isinstance(failure, dict):
        time.sleep(failure["sleep"])
    elif failure:
        sys.exit(failure)


def visible_releases():
    hidden = state.get("hidden", {})
    result = [r for r in state["releases"] if str(r["id"]) not in hidden]
    if hidden:
        for identity in list(hidden):
            hidden[identity] -= 1
            if hidden[identity] <= 0:
                del hidden[identity]
        if not hidden:
            del state["hidden"]
        (root / "state.json").write_text(json.dumps(state))
    return result


url = args[0]
if url == "graphql":
    fields = dict(value.split("=", 1) for value in args[2::2])
    assert fields["owner"] == "owner" and fields["name"] == "plugins"
    assert "assets" not in fields["query"]
    cursor = fields.get("cursor", "")
    read_error("graphql:" + cursor)
    offset = int(cursor or 0)
    records = visible_releases()
    batch = records[offset : offset + 100]
    print(json.dumps({"data": {"repository": {"releases": {
        "nodes": [{key: r[key] for key in ("id", "tag_name", "draft")} for r in batch],
        "pageInfo": {"hasNextPage": offset + 100 < len(records),
                     "endCursor": str(offset + 100)},
    }}}}))
    sys.exit(0)
if method == "GET":
    read_error(url)
parsed = urlsplit(url)
parts = parsed.path.lstrip("/").split("/")
assert parts[:3] == ["repos", "owner", "plugins"], parts
if parts[3] == "commits":
    result = {"sha": "1" * 40}
elif len(parts) == 4:
    assert parts[3] == "releases"
    if state.get("release_list_error"):
        sys.exit(state["release_list_error"])
    query = parse_qs(parsed.query)
    page = int(query["page"][0])
    page_size = int(query["per_page"][0])
    if page_size > state.get("release_page_limit", 100):
        sys.exit("gh: release list response too large (HTTP 504)")
    result = visible_releases()[(page - 1) * page_size : page * page_size]
elif parts[4] == "tags":
    result = next(r for r in state["releases"] if r["tag_name"] == parts[5])
    if result["draft"]:
        sys.exit("published release not found")
elif len(parts) == 5 and method == "GET":
    result = next(r for r in state["releases"] if r["id"] == int(parts[4]))
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
