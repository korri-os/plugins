"""Refuse every dry run that is not the passed run of exactly this batch."""

import copy
import hashlib
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location(
    "dry_run", Path(__file__).parent.parent / ".github/workflows/dry-run.py"
)
dry_run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dry_run)

REPO = "korri-os/plugins"
SHA = "97c28031b06cb854aaf67d6f7cc842763d3858b9"
TAG = "build-97c28031b06c-steam-launch-steps"
PACKAGES = "korri-plugin-steam"


def passed_run():
    return {
        "repository": {"full_name": REPO},
        "path": ".github/workflows/plugin-repository.yml",
        "event": "workflow_dispatch",
        "head_branch": "main",
        "status": "completed",
        "conclusion": "success",
        "actor": {"login": "simonwjackson"},
        "triggering_actor": {"login": "simonwjackson"},
        "display_title": f"Dry run {TAG} at {SHA}: {PACKAGES}",
    }


def passed_jobs():
    return [{"name": name, "conclusion": "success"} for name in sorted(dry_run.JOBS)]


def artifacts():
    return [
        {"name": name, "expired": False, "digest": "sha256:" + "0" * 64}
        for name in sorted(dry_run.ARTIFACTS)
    ]


def check(run=None, jobs=None, found=None, tag=TAG, sha=SHA, packages=PACKAGES):
    return dry_run.check(
        REPO,
        passed_run() if run is None else run,
        passed_jobs() if jobs is None else jobs,
        artifacts() if found is None else found,
        tag,
        sha,
        packages,
    )


class DryRun(unittest.TestCase):
    def test_accepts_the_passed_dry_run_of_this_batch(self):
        self.assertEqual(check(), [])

    def test_run_name_matches_the_workflow(self):
        workflow = (
            Path(__file__).parent.parent / ".github/workflows/plugin-repository.yml"
        ).read_text()
        line = re.search(r"^run-name: (.*)$", workflow, re.M).group(1)
        rendered = (
            line.strip('"')
            .replace("${{ inputs.tag }}", TAG)
            .replace("${{ inputs.expected_source_sha }}", SHA)
            .replace("${{ inputs.packages }}", PACKAGES)
        )
        self.assertEqual(rendered, dry_run.run_name(TAG, SHA, PACKAGES))

    def test_job_names_match_the_workflow(self):
        workflow = (
            Path(__file__).parent.parent / ".github/workflows/plugin-repository.yml"
        ).read_text()
        jobs = set(re.findall(r"^  ([a-z]+):$", workflow, re.M))
        self.assertEqual(jobs, {"build", "lifecycle", "assemble"})

    def test_refuses_another_batch(self):
        for kwargs in (
            {"tag": "build-other"},
            {"sha": "1" * 40},
            {"packages": "korri-plugin-steam korri-plugin-fex"},
            {"packages": "korri-plugin-steam "},
        ):
            with self.subTest(kwargs=kwargs):
                self.assertTrue(any("title" in p for p in check(**kwargs)))

    def test_refuses_a_short_sha(self):
        self.assertIn("full commit SHA", " ".join(check(sha=SHA[:12])))

    def test_refuses_a_run_that_is_not_a_passed_owner_dry_run(self):
        changes = {
            "repository": {"full_name": "someone/plugins"},
            "path": ".github/workflows/plugin-checks.yml",
            "event": "push",
            "head_branch": "feature",
            "status": "in_progress",
            "conclusion": "failure",
            "actor": {"login": "someone"},
            "triggering_actor": {"login": "someone"},
        }
        for key, value in changes.items():
            with self.subTest(key=key):
                run = passed_run()
                run[key] = value
                self.assertTrue(check(run=run))

    def test_refuses_skipped_failed_missing_or_extra_jobs(self):
        skipped = passed_jobs()
        skipped[0]["conclusion"] = "skipped"
        missing = passed_jobs()[1:]
        extra = passed_jobs() + [{"name": "publish", "conclusion": "success"}]
        for jobs in (skipped, missing, extra):
            with self.subTest(jobs=jobs):
                self.assertTrue(check(jobs=jobs))

    def test_refuses_missing_duplicate_or_expired_artifacts(self):
        expired = artifacts()
        expired[0]["expired"] = True
        missing = artifacts()[1:]
        duplicate = artifacts() + [copy.deepcopy(artifacts()[0])]
        for found in (expired, missing, duplicate):
            with self.subTest(found=found):
                self.assertTrue(check(found=found))


class Unpack(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.archive = self.folder / "cache.zip"

    def zip(self, entries):
        with zipfile.ZipFile(self.archive, "w") as bundle:
            for name, data in entries.items():
                bundle.writestr(name, data)
        return "sha256:" + hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def test_extracts_an_archive_with_the_recorded_digest(self):
        digest = self.zip({"revision.txt": SHA + "\n", "nars/a.nar": b"nar"})
        dry_run.unpack(self.archive, digest, self.folder / "out")
        self.assertEqual((self.folder / "out/nars/a.nar").read_bytes(), b"nar")

    def test_refuses_changed_bytes_or_a_missing_digest(self):
        digest = self.zip({"revision.txt": SHA + "\n"})
        with self.archive.open("ab") as archive:
            archive.write(b"x")
        for recorded in (digest, None, "sha1:" + "0" * 40):
            with self.subTest(recorded=recorded):
                with self.assertRaises(ValueError):
                    dry_run.unpack(self.archive, recorded, self.folder / "out")
        self.assertFalse((self.folder / "out").exists())

    def test_refuses_an_entry_outside_its_folder(self):
        digest = self.zip({"../escape.txt": "x"})
        with self.assertRaises(ValueError):
            dry_run.unpack(self.archive, digest, self.folder / "out")
        self.assertFalse((self.folder / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()
