import tempfile
import unittest
from pathlib import Path

from eden import FALLBACKS, NATIVE_DEFAULT, evidence, map_signal, selected_backend

VULKAN = "Render.Vulkan <Info> Driver: Mesa Turnip\nRender.Vulkan <Info> Vulkan: 1.4\n"
HOST = "1000-2000 r-xs 00000000 00:01 42 /memfd:HostMemory (deleted)"
CACHE = "10000000-18000000 rwxp 00000000 00:00 0"


class EvidenceTests(unittest.TestCase):
    def test_three_part_inference_retains_no_key_diagnostics(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "eden.log"
            # Synthetic fixtures use Eden's actual LogSettings canonical format.
            path.write_text(
                VULKAN + "-- Cpu.cpu_backend: Nce\nKey loading diagnostic excluded\n"
            )
            lines, backend = evidence(path, 0, {"selected": "NCE"}, [map_signal(HOST)])
            self.assertIn("NCE (inferred", backend)
            self.assertNotIn("Key loading", "\n".join(lines))

    def test_host_memory_exec_alone_does_not_discriminate_dynarmic(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "eden.log"
            path.write_text(VULKAN + "-- Cpu.cpu_backend: Dynarmic\n")
            _, backend = evidence(path, 0, {"selected": "Dynarmic"}, [map_signal(HOST)])
            self.assertTrue(backend.startswith("unproven"))
            _, backend = evidence(
                path, 0, {"selected": "Dynarmic"}, [map_signal(HOST + "\n" + CACHE)]
            )
            self.assertIn("Dynarmic (inferred", backend)

    def test_fallback_or_conflicting_runtime_is_unproven(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "eden.log"
            for suffix, signal in ((FALLBACKS[0], HOST), ("", HOST + "\n" + CACHE)):
                path.write_text(VULKAN + "-- Cpu.cpu_backend: Nce\n" + suffix)
                _, backend = evidence(
                    path, 0, {"selected": "NCE"}, [map_signal(signal)]
                )
                self.assertTrue(backend.startswith("unproven"))

    def test_native_per_game_override_wins_and_defaults_need_effective_log(self):
        with tempfile.TemporaryDirectory() as root:
            config = Path(root) / "qt-config.ini"
            config.write_text("[Cpu]\ncpu_backend=1\ncpu_backend\\default=false\n")
            self.assertEqual(
                selected_backend(config, "0100000000010000")["selected"], "NCE"
            )
            custom = Path(root) / "custom/0100000000010000.ini"
            custom.parent.mkdir()
            custom.write_text(
                "[Cpu]\ncpu_backend=0\ncpu_backend\\default=false\ncpu_backend\\use_global=false\n"
            )
            self.assertEqual(
                selected_backend(config, "0100000000010000")["selected"], "Dynarmic"
            )
            custom.write_text("[Cpu]\ncpu_backend=0\ncpu_backend\\use_global=false\n")
            self.assertEqual(
                selected_backend(config, "0100000000010000")["selected"], NATIVE_DEFAULT
            )

    def native_default_selection(self, root):
        config = Path(root) / "qt-config.ini"
        # Native \default=true means this stored value is ignored, not selected.
        config.write_text("[Cpu]\ncpu_backend=0\ncpu_backend\\default=true\n")
        return selected_backend(config, "0100000000010000")

    def test_native_default_with_matching_effective_log_passes(self):
        with tempfile.TemporaryDirectory() as root:
            selection = self.native_default_selection(root)
            path = Path(root) / "eden.log"
            for logged, maps, expected in (
                ("Nce", HOST, "NCE"),
                ("Dynarmic", CACHE, "Dynarmic"),
            ):
                path.write_text(VULKAN + f"-- Cpu.cpu_backend: {logged}\n")
                _, backend = evidence(path, 0, selection, [map_signal(maps)])
                self.assertIn(expected + " (inferred", backend)

    def test_native_default_without_effective_log_fails(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "eden.log"
            path.write_text(VULKAN)
            _, backend = evidence(
                path, 0, self.native_default_selection(root), [map_signal(HOST)]
            )
            self.assertTrue(backend.startswith("unproven"))

    def test_native_default_with_any_refusal_fails(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "eden.log"
            for refusal in FALLBACKS:
                path.write_text(VULKAN + "-- Cpu.cpu_backend: Nce\n" + refusal)
                _, backend = evidence(
                    path, 0, self.native_default_selection(root), [map_signal(HOST)]
                )
                self.assertTrue(backend.startswith("unproven"))

    def test_native_default_with_disagreeing_mapping_fails(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "eden.log"
            for logged, maps in (("Nce", HOST + "\n" + CACHE), ("Dynarmic", HOST)):
                path.write_text(VULKAN + f"-- Cpu.cpu_backend: {logged}\n")
                _, backend = evidence(
                    path, 0, self.native_default_selection(root), [map_signal(maps)]
                )
                self.assertTrue(backend.startswith("unproven"))

    def test_explicit_selection_with_disagreeing_log_fails(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "eden.log"
            path.write_text(VULKAN + "-- Cpu.cpu_backend: Dynarmic\n")
            _, backend = evidence(path, 0, {"selected": "NCE"}, [map_signal(CACHE)])
            self.assertTrue(backend.startswith("unproven"))

    def test_config_does_not_prove_vulkan_renderer_and_stale_log_fails(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "eden.log"
            path.write_text("Vulkan = true\n")
            with self.assertRaisesRegex(ValueError, "renderer"):
                evidence(path, 0, {}, [])
            with self.assertRaisesRegex(ValueError, "stale"):
                evidence(path, path.stat().st_mtime_ns + 1, {}, [])


if __name__ == "__main__":
    unittest.main()
