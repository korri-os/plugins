import unittest

from bench import EMULATORS, process_name_matches


class ProcessNameTests(unittest.TestCase):
    def test_allowed_name_matches_basename_case_insensitively(self):
        self.assertTrue(
            process_name_matches("/nix/store/runtime/bin/.Eden-wrapped", EMULATORS)
        )
        self.assertFalse(
            process_name_matches("/nix/store/eden-tools/bin/sleep", EMULATORS)
        )

    def test_cleanup_policy_includes_wrappers_but_launch_policy_does_not(self):
        for name in ("gamescope", "bwrap"):
            executable = f"/nix/store/runtime/bin/{name}"
            self.assertFalse(process_name_matches(executable, EMULATORS))
            self.assertTrue(
                process_name_matches(executable, (*EMULATORS, "gamescope", "bwrap"))
            )

    def test_caller_controls_allowed_names(self):
        executable = "/nix/store/runtime/bin/retroarch"
        self.assertFalse(process_name_matches(executable, ("eden",)))
        self.assertTrue(process_name_matches(executable, ("retroarch",)))


if __name__ == "__main__":
    unittest.main()
