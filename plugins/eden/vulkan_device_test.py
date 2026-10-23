"""Native Vulkan selection contract, with real temporary INI files and crudini."""

import configparser
import sys
import tempfile
import unittest
from pathlib import Path

from vulkan_device import Device, configure, eden_order, read_devices

CRUDINI = sys.argv.pop(1)
TURNIP = Device(
    "Turnip Adreno (TM) 740",
    0x5143,
    "PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU",
    "DRIVER_ID_MESA_TURNIP",
)
SOFTWARE = Device(
    "llvmpipe (LLVM 21.1.8, 128 bits)",
    0x10005,
    "PHYSICAL_DEVICE_TYPE_CPU",
    "DRIVER_ID_MESA_LLVMPIPE",
)


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.work = tempfile.TemporaryDirectory()
        self.config = Path(self.work.name) / "account with spaces/qt-config.ini"
        self.config.parent.mkdir()
        self.seed(0, True)

    def tearDown(self) -> None:
        self.work.cleanup()

    def seed(self, index: int, default: bool) -> None:
        self.config.write_text(
            f"[Renderer]\nvulkan_device={index}\nvulkan_device\\default={str(default).lower()}\n"
            "resolution_setup=2\n[Data Storage]\nsave_directory=/keep this\n"
        )

    def test_turnip_plus_software_uses_eden_index_not_raw_index(self) -> None:
        self.assertEqual(eden_order([TURNIP, SOFTWARE]), [SOFTWARE, TURNIP])
        self.assertEqual(configure(self.config, [TURNIP, SOFTWARE], CRUDINI), (1, True))
        native = configparser.ConfigParser(interpolation=None)
        native.read(self.config)
        self.assertEqual(native.getint("Renderer", "vulkan_device"), 1)
        self.assertFalse(native.getboolean("Renderer", "vulkan_device\\default"))
        self.assertEqual(native.get("Renderer", "resolution_setup"), "2")
        self.assertEqual(native.get("Data Storage", "save_directory"), "/keep this")

    def test_turnip_alone_uses_zero(self) -> None:
        self.assertEqual(configure(self.config, [TURNIP], CRUDINI), (0, True))

    def test_software_alone_fails_without_writing(self) -> None:
        before = self.config.read_bytes()
        with self.assertRaisesRegex(ValueError, "no Adreno/Turnip"):
            configure(self.config, [SOFTWARE], CRUDINI)
        self.assertEqual(before, self.config.read_bytes())

    def test_explicit_valid_user_value_is_byte_preserved(self) -> None:
        self.seed(1, False)
        before = self.config.read_bytes()
        self.assertEqual(
            configure(self.config, [TURNIP, SOFTWARE], CRUDINI), (1, False)
        )
        self.assertEqual(before, self.config.read_bytes())

    def test_explicit_software_choice_fails_without_rewriting_it(self) -> None:
        self.seed(0, False)
        before = self.config.read_bytes()
        with self.assertRaisesRegex(ValueError, "not Adreno/Turnip"):
            configure(self.config, [TURNIP, SOFTWARE], CRUDINI)
        self.assertEqual(before, self.config.read_bytes())

    def test_native_default_zero_is_moved_even_if_a_user_selected_zero(self) -> None:
        # Eden records equality to its default, not whether a person picked it.
        self.seed(0, True)
        self.assertEqual(configure(self.config, [TURNIP, SOFTWARE], CRUDINI), (1, True))

    def test_missing_and_invalid_properties_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "no device properties"):
            read_devices("Devices:\n========\n")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            read_devices("GPU0:\n deviceName = incomplete\n")

    def test_native_summary_properties(self) -> None:
        summary = "Vulkan Instance Version: 1.4.363\nDevices:\n========\n"
        for index, device in enumerate([TURNIP, SOFTWARE]):
            summary += (
                f"GPU{index}:\n vendorID = {hex(device.vendor)}\n"
                f" deviceType = {device.kind}\n deviceName = {device.name}\n"
                f" driverID = {device.driver}\n"
            )
        self.assertEqual(read_devices(summary), [TURNIP, SOFTWARE])

    def test_vendor_and_discrete_sort_matches_pinned_eden_contract(self) -> None:
        nvidia = Device(
            "Nvidia GPU", 0x10DE, "PHYSICAL_DEVICE_TYPE_DISCRETE_GPU", "nvidia"
        )
        amd = Device("AMD GPU", 0x1002, "PHYSICAL_DEVICE_TYPE_DISCRETE_GPU", "amd")
        intel = Device(
            "Intel GPU", 0x8086, "PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU", "intel"
        )
        dozen = Device(
            "Microsoft Direct3D12", 0x10DE, "PHYSICAL_DEVICE_TYPE_DISCRETE_GPU", "dozen"
        )
        self.assertEqual(
            eden_order([TURNIP, SOFTWARE, dozen, intel, amd, nvidia]),
            [nvidia, amd, intel, SOFTWARE, TURNIP, dozen],
        )

    def test_malformed_ini_diagnostics_do_not_include_its_contents(self) -> None:
        self.config.write_text("sensitive-ini-value\n")
        with self.assertRaises(ValueError) as caught:
            configure(self.config, [TURNIP, SOFTWARE], CRUDINI)
        self.assertNotIn("sensitive-ini-value", str(caught.exception))

    def test_invalid_native_flag_diagnostic_does_not_echo_the_value(self) -> None:
        self.config.write_text(
            "[Renderer]\nvulkan_device\\default=sensitive-ini-value\n"
        )
        with self.assertRaises(ValueError) as caught:
            configure(self.config, [TURNIP, SOFTWARE], CRUDINI)
        self.assertNotIn("sensitive-ini-value", str(caught.exception))

    def test_out_of_range_user_value_fails_without_writing(self) -> None:
        self.seed(4, False)
        before = self.config.read_bytes()
        with self.assertRaisesRegex(ValueError, "unavailable"):
            configure(self.config, [TURNIP, SOFTWARE], CRUDINI)
        self.assertEqual(before, self.config.read_bytes())


if __name__ == "__main__":
    unittest.main()
