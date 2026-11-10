"""Privacy and AppID boundaries of Steam's native log refusal reporting."""
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).parent


class SteamFailureTests(unittest.TestCase):
    def reason(self, lines, appid="401710"):
        result = subprocess.run(
            ["bash", "-c", 'source "$1"; steam_failure_reason "$2"',
             "bash", str(HERE / "steam-failure.sh"), appid],
            input=lines, text=True, capture_output=True, check=True,
        )
        return result.stdout.strip()

    def test_launch_and_download_errors_are_short_and_plain(self):
        cases = {
            'LaunchApp failed with error "No subscription"': "Steam: this game is not owned by the signed-in account",
            'LaunchApp failed with error "Invalid platform"': "Steam: this game is not available for this device",
            'LaunchApp failed with error "Missing executable"': "Steam: the game executable is missing",
            'update canceled : Disk read failure': "Steam: the game update failed because Steam could not read from disk",
            'update canceled : No connection': "Steam: the game update failed because the connection failed",
            'update canceled : Disk write failure': "Steam: the game update failed because Steam could not write to disk",
            'update canceled : Not enough disk space': "Steam: the game update failed because there is not enough disk space",
            'update canceled : Content servers unreachable': "Steam: the game update failed because the content servers are unreachable",
            'update canceled : Corrupt update files': "Steam: the game update failed because the downloaded files are corrupt",
            'LaunchApp failed with error "AppUpdateRequired"': "Steam: this game needs an update",
            'LaunchApp failed with error "opaque-token"': "Steam: Steam reported a launch error",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                actual = self.reason(f'[2026-11-10 12:00:00] GameAction [AppID 401710, ActionID 1] : {message}\n')
                self.assertEqual(actual, expected)
                self.assertLessEqual(len(actual), 160)

    def test_app_state_is_a_reason_only_when_session_fails(self):
        self.assertEqual(self.reason('AppID 401710 state changed : Update Required,Update Queued,\n'),
                         "Steam: this game needs an update")

    def test_fully_installed_clears_the_update_required_state(self):
        self.assertEqual(self.reason('AppID 401710 state changed : Update Required,\n'
                                     'AppID 401710 state changed : Fully Installed,\n'), "")

    def test_another_app_unscoped_errors_and_suspended_updates_are_ignored(self):
        for line in (
            'AppID 4017100 update canceled : Disk write failure',
            'AppID 1401710 update canceled : Disk write failure',
            'GameAction [AppID 400, ActionID 1] : LaunchApp failed with error "No subscription"',
            'Content server connection failed for account 123456789',
            'AppID 401710 update canceled : Priority (Suspended)',
            'AppID 401710 update canceled : Disabled (Suspended)',
            'AppID 401710 no longer tracking PID 1234, exit code -1',
        ):
            with self.subTest(line=line):
                self.assertEqual(self.reason(line), "")

    def test_raw_log_text_cannot_escape_into_the_status(self):
        line = ('GameAction [AppID 401710, ActionID 987654321] : LaunchApp failed with error '
                '"Missing executable /home/account/123456789/game.exe"\n')
        self.assertEqual(self.reason(line), "Steam: the game executable is missing")

    def test_specific_failure_wins_over_update_required_state(self):
        self.assertEqual(self.reason('AppID 401710 update canceled : Disk write failure\n'
                                     'AppID 401710 state changed : Update Required,\n'),
                         "Steam: the game update failed because Steam could not write to disk")


if __name__ == "__main__":
    unittest.main()
