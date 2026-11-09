#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3
"""Fetch the artifacts of the passed dry run of this exact batch.

Publication ships the dry run's own signed artifacts instead of rebuilding
them. Two checks make those artifacts publishable. GitHub, not job code,
reports the run's workflow, branch, actors, outcome and title, and the title is
GitHub's own rendering of the dispatch inputs (`run-name`). Each artifact must
then match the digest GitHub recorded when the dry run uploaded it.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

WORKFLOW = ".github/workflows/plugin-repository.yml"
OWNER = "simonwjackson"
JOBS = {
    "build (x86_64-linux, ubuntu-24.04)",
    "build (aarch64-linux, ubuntu-24.04-arm)",
    "lifecycle",
    "assemble",
}
ARTIFACTS = {"cache-x86_64-linux", "cache-aarch64-linux", "merged-catalog"}


def run_name(tag, source_sha, packages):
    """Must match `run-name` in plugin-repository.yml character for character."""
    return f"Dry run {tag} at {source_sha}: {packages}"


def check(repo, run, jobs, artifacts, tag, source_sha, packages):
    """Return the refusal reasons; an empty list means the run may be published."""
    problems = []

    def expect(label, actual, wanted):
        if actual != wanted:
            problems.append(f"{label} is {actual!r}, expected {wanted!r}")

    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        problems.append("expected_source_sha must be a full commit SHA")
    expect("repository", run.get("repository", {}).get("full_name"), repo)
    expect("workflow", run.get("path"), WORKFLOW)
    expect("event", run.get("event"), "workflow_dispatch")
    expect("branch", run.get("head_branch"), "main")
    expect("status", run.get("status"), "completed")
    expect("conclusion", run.get("conclusion"), "success")
    expect("actor", (run.get("actor") or {}).get("login"), OWNER)
    expect("triggering actor", (run.get("triggering_actor") or {}).get("login"), OWNER)
    expect("title", run.get("display_title"), run_name(tag, source_sha, packages))

    # A skipped job also leaves the run successful; require every job to pass.
    outcomes = {job["name"]: job.get("conclusion") for job in jobs}
    for name in sorted(JOBS - outcomes.keys()):
        problems.append(f"job {name!r} is missing")
    for name, outcome in sorted(outcomes.items()):
        if name not in JOBS:
            problems.append(f"unexpected job {name!r}")
        elif outcome != "success":
            problems.append(f"job {name!r} concluded {outcome!r}")

    found = {}
    for artifact in artifacts:
        if artifact["name"] in found:
            problems.append(f"artifact {artifact['name']!r} appears twice")
        found[artifact["name"]] = artifact
    for name in sorted(ARTIFACTS):
        artifact = found.get(name)
        if artifact is None:
            problems.append(f"artifact {name!r} is missing")
        elif artifact.get("expired"):
            problems.append(f"artifact {name!r} has expired; dispatch a new dry run")
    return problems


def unpack(archive, digest, target):
    """Extract a downloaded artifact only if it has GitHub's recorded digest."""
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest or ""):
        raise ValueError("artifact has no recorded SHA-256 digest")
    hasher = hashlib.sha256()
    with open(archive, "rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            hasher.update(block)
    if "sha256:" + hasher.hexdigest() != digest:
        raise ValueError(f"artifact digest mismatch: {archive.name}")
    target.mkdir(parents=True)
    root = target.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            destination = (target / member.filename).resolve()
            if not destination.is_relative_to(root) or destination == root:
                raise ValueError(f"artifact entry leaves its folder: {member.filename}")
        bundle.extractall(target)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(url, token=None, accept="application/vnd.github+json"):
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def api(path, token):
    with urllib.request.urlopen(
        request(f"https://api.github.com/{path}", token), timeout=60
    ) as response:
        return json.load(response)


def download(repo, artifact, token, archive):
    # GitHub answers with a redirect to signed storage. Follow it without the
    # token: the storage URL carries its own authorization.
    opener = urllib.request.build_opener(_NoRedirect)
    url = f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact['id']}/zip"
    try:
        opener.open(request(url, token), timeout=60)
        raise ValueError(f"expected a redirect for artifact {artifact['name']}")
    except urllib.error.HTTPError as redirect:
        if redirect.code not in (301, 302, 303, 307, 308):
            raise
        location = redirect.headers["Location"]
    with urllib.request.urlopen(location, timeout=600) as response:
        with open(archive, "xb") as target:
            shutil.copyfileobj(response, target, 1 << 20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--packages", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]{1,20}", args.run_id):
        sys.exit("dry_run_id must be a numeric workflow run ID")
    if args.output.exists() or args.output.is_symlink():
        sys.exit("the artifact folder must not exist yet")
    token = os.environ["GITHUB_TOKEN"]
    base = f"repos/{args.repo}/actions/runs/{args.run_id}"
    run = api(base, token)
    # The latest attempt only: an earlier failed attempt is not evidence.
    jobs = api(f"{base}/jobs?filter=latest&per_page=100", token)["jobs"]
    artifacts = api(f"{base}/artifacts?per_page=100", token)["artifacts"]
    problems = check(
        args.repo, run, jobs, artifacts, args.tag, args.source_sha, args.packages
    )
    if problems:
        sys.exit("Refusing to publish this dry run:\n- " + "\n- ".join(problems))
    print(f"Dry run {args.run_id} (attempt {run.get('run_attempt')}) passed for this batch")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as temporary:
        staged = Path(temporary) / "artifacts"
        for artifact in sorted(artifacts, key=lambda item: item["name"]):
            if artifact["name"] not in ARTIFACTS:
                continue
            archive = Path(temporary) / f"{artifact['name']}.zip"
            download(args.repo, artifact, token, archive)
            unpack(archive, artifact.get("digest"), staged / artifact["name"])
            print(f"{artifact['name']}: {artifact['digest']} verified")
        staged.rename(args.output)


if __name__ == "__main__":
    main()
