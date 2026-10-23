import unittest

from input_observer import external_gamepads


class AdmissionTests(unittest.TestCase):
    def test_only_builtin_and_known_virtual_outputs_are_allowed(self):
        devices = [
            {
                "event": "event3",
                "name": "AYN Odin2 Gamepad",
                "gamepad": True,
                "phys": "builtin",
                "sysfs": "/devices/platform/input3",
            },
            {
                "event": "event6",
                "name": "Korri Seat P1",
                "gamepad": True,
                "phys": "korri/input-seat/p1",
                "sysfs": "/devices/virtual/input/input6",
            },
            {
                "event": "event10",
                "name": "Microsoft X-Box 360 pad",
                "gamepad": True,
                "phys": "",
                "sysfs": "/devices/virtual/input/input10",
            },
            {
                "event": "event0",
                "name": "pmic_pwrkey",
                "gamepad": False,
                "phys": "",
                "sysfs": "/devices/platform/input0",
            },
        ]
        self.assertEqual(external_gamepads(devices, ["/dev/input/event3"]), [])
        external = {
            "event": "event16",
            "name": "Xbox Wireless Controller",
            "gamepad": True,
            "phys": "usb/input0",
            "sysfs": "/devices/pci/usb/input16",
        }
        self.assertEqual(
            external_gamepads(devices + [external], ["/dev/input/event3"]), [external]
        )
        # Unknown virtual pads must not silently escape the admission preflight.
        unknown = {**external, "phys": "", "sysfs": "/devices/virtual/input/input16"}
        self.assertEqual(
            external_gamepads(devices + [unknown], ["/dev/input/event3"]), [unknown]
        )


if __name__ == "__main__":
    unittest.main()
