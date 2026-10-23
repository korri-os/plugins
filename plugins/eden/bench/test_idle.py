import tempfile
import unittest
from pathlib import Path

from rpc import IdleProofError, RpcFailure, retained_idle_proof

PRIOR = "a" * 32
MESSAGE = f"host launch {PRIOR} failed: game unit failed with exit status 1"


class RetainedIdleTests(unittest.TestCase):
    def test_prior_failure_and_empty_native_state_is_idle_with_verbatim_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "cgroup.procs").write_text("")
            proof = retained_idle_proof(
                RpcFailure("HostLaunchFailed", MESSAGE), set(), "", root
            )
            self.assertTrue(proof["acceptedAsIdle"])
            self.assertTrue(proof["outsideThisRun"])
            self.assertEqual(proof["launchId"], PRIOR)
            self.assertEqual(
                proof["retainedStatus"],
                {"code": "HostLaunchFailed", "message": MESSAGE},
            )

    def test_any_native_active_unit_fails_even_with_empty_cgroup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "cgroup.procs").write_text("")
            for unit in (
                "korri-game-other.service active",
                "korri-acquire-other.service activating",
            ):
                with self.assertRaises(IdleProofError):
                    retained_idle_proof(
                        RpcFailure("HostLaunchFailed", MESSAGE), set(), unit, root
                    )

    def test_populated_root_or_descendant_cgroup_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "cgroup.procs").write_text("123\n")
            with self.assertRaises(IdleProofError):
                retained_idle_proof(
                    RpcFailure("HostLaunchFailed", MESSAGE), set(), "", root
                )
            (root / "cgroup.procs").write_text("")
            (root / "child").mkdir()
            (root / "child/cgroup.procs").write_text("456\n")
            with self.assertRaises(IdleProofError):
                retained_idle_proof(
                    RpcFailure("HostLaunchFailed", MESSAGE), set(), "", root
                )

    def test_our_failed_launch_is_never_accepted_as_idle(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "cgroup.procs").write_text("")
            with self.assertRaisesRegex(IdleProofError, "Our own"):
                retained_idle_proof(
                    RpcFailure("HostLaunchFailed", MESSAGE), {PRIOR}, "", root
                )

    def test_unreadable_native_state_is_unknown_not_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            # A real read failure, including when the tests run as root.
            (root / "cgroup.procs").mkdir()
            with self.assertRaisesRegex(IdleProofError, "unreadable"):
                retained_idle_proof(
                    RpcFailure("HostLaunchFailed", MESSAGE), set(), "", root
                )

    def test_unidentified_failure_is_not_assumed_terminal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "cgroup.procs").write_text("")
            with self.assertRaises(IdleProofError):
                retained_idle_proof(
                    RpcFailure("HostLaunchFailed", "native observation failed"),
                    set(),
                    "",
                    root,
                )


if __name__ == "__main__":
    unittest.main()
