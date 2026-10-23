"""Require notices for the pinned Cemu source and its bundled components."""

import gzip
from pathlib import Path
import sys

root = Path(sys.argv[1]) / "share/licenses/cemu"
required = [
    "LICENSE.txt",
    "MIT.txt",
    "cubeb/LICENSE",
    "imgui/LICENSE.txt",
    "ih264d/NOTICE",
    "ih264d/LICENSE",
    "xbyak_aarch64/LICENSE",
    "Vulkan-Headers/LICENSE.md",
    "SDL3/LICENSE.txt",
    "SDL3/hidapi-LICENSE-bsd.txt",
    "SDL3/hidapi-LICENSE-orig.txt",
    "SDL3/yuv2rgb-LICENSE",
    "fmt/LICENSE",
    "Mesa/license.rst",
    "Mesa/licenses/MIT",
    "Mesa/licenses/Apache-2.0",
    "ZArchive/LICENSE",
    "pugixml/LICENSE.md",
    "RapidJSON/license.txt",
    "glm/copying.txt",
    "glslang/LICENSE.txt",
    "SPIRV-Tools/LICENSE",
    "fonts/OFL-1.1.txt",
    "fonts/NOTICE.txt",
    "cemu-source-NOTICES.txt.gz",
    "sdl3-source-NOTICES.txt.gz",
    "fmt-source-NOTICES.txt.gz",
    "mesa-source-NOTICES.txt.gz",
]
for name in required:
    path = root / name
    assert path.is_file() and path.stat().st_size > 0, f"Missing licence notice: {name}"
notices = gzip.decompress((root / "cemu-source-NOTICES.txt.gz").read_bytes()).decode()
for attribution in [
    "Sean Barrett",
    "Tristan Grimmer",
    "Howard Hinnant",
    "fast_float authors",
    "Martin Ankerl",
    "Lee Thomason",
    "Alexander Peslyak",
    "Khronos",
    "FUJITSU",
]:
    assert attribution in notices, f"Missing bundled attribution: {attribution}"
assert "Adobe Systems" in (root / "fonts/NOTICE.txt").read_text()
assert (
    "Sun Microsystems"
    in gzip.decompress((root / "sdl3-source-NOTICES.txt.gz").read_bytes()).decode()
)
if len(sys.argv) == 3:
    expected = Path(sys.argv[2])
    for source in expected.rglob("*"):
        if source.is_file():
            assert (
                root / source.relative_to(expected)
            ).read_bytes() == source.read_bytes(), source.name
print(
    f"Cemu licences: {len(required)} required notices and pinned source copies passed"
)
