"""Keep compiler diagnostics available without putting them in runtime output."""

from pathlib import Path
import sys

package = Path(sys.argv[1])
evidence = Path(sys.argv[2])
runtime = package / "nix-support/cemu-build"
diagnostics = evidence / "nix-support/cemu-build"
for name in ["compile_commands.json", "ipo.txt"]:
    assert not (runtime / name).exists(), f"Runtime contains bulky diagnostics: {name}"
    path = diagnostics / name
    assert path.is_file() and path.stat().st_size > 0, (
        f"Missing optional evidence: {name}"
    )
assert "flto" in (diagnostics / "ipo.txt").read_text()
for name in [
    "cubeb.txt",
    "compiler.txt",
    "elf-header.txt",
    "elf-dynamic.txt",
    "resources.txt",
    "gameProfiles.txt",
    "graphicPacks.txt",
]:
    text = (runtime / name).read_text()
    assert text.strip(), f"Missing short build proof: {name}"
    assert str(evidence) not in text, f"Runtime proof retains evidence output: {name}"
assert "cubeb_pulse.c.o" in (runtime / "cubeb.txt").read_text()
assert "cubeb_alsa.c.o" in (runtime / "cubeb.txt").read_text()
assert sum(p.stat().st_size for p in runtime.iterdir()) < 20_000, (
    "Runtime proofs grew unexpectedly"
)
print("Cemu optional diagnostics and short runtime proofs passed")
