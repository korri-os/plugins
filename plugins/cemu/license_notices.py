"""Collect notices from the exact pinned sources, without retaining source paths."""

from pathlib import Path
import gzip
import re
import struct
import sys

COMMENT = re.compile(r"/\*.*?\*/|(?:^[ \t]*//[^\n]*(?:\n|$))+", re.S | re.M)
LEGAL = re.compile(r"copyright|licen[cs]e|permission|redistribution|SPDX", re.I)
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".h", ".hpp", ".s", ".S"}


def notice_comments(text: str) -> list[str]:
    return [
        match[0].strip() for match in COMMENT.finditer(text) if LEGAL.search(match[0])
    ]


def font_names(data: bytes) -> dict[int, list[str]]:
    result: dict[int, set[str]] = {}
    for index in range(struct.unpack_from(">H", data, 4)[0]):
        tag, _, offset, _ = struct.unpack_from(">4sIII", data, 12 + index * 16)
        if tag != b"name":
            continue
        _, count, start = struct.unpack_from(">HHH", data, offset)
        for record in range(count):
            platform, _, _, name, length, position = struct.unpack_from(
                ">6H", data, offset + 6 + record * 12
            )
            if name not in (0, 1, 13, 14):
                continue
            raw = data[offset + start + position : offset + start + position + length]
            text = raw.decode("utf-16-be" if platform in (0, 3) else "mac_roman")
            result.setdefault(name, set()).add(text)
    if not result.get(0):
        raise ValueError("Font has no copyright attribution")
    return {key: sorted(values) for key, values in result.items()}


def collect(output: Path, sources: dict[str, Path], ofl: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)

    def copy(component: str, source: str, target: str) -> None:
        data = (sources[component] / source).read_bytes()
        if not data:
            raise ValueError(f"Empty notice: {component}/{source}")
        path = output / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    required = [
        ("cemu", "LICENSE.txt", "LICENSE.txt"),
        ("cemu", "dependencies/cubeb/LICENSE", "cubeb/LICENSE"),
        ("cemu", "dependencies/imgui/LICENSE.txt", "imgui/LICENSE.txt"),
        ("cemu", "dependencies/ih264d/NOTICE", "ih264d/NOTICE"),
        ("cemu", "dependencies/xbyak_aarch64/LICENSE", "ih264d/LICENSE"),
        ("cemu", "dependencies/xbyak_aarch64/LICENSE", "xbyak_aarch64/LICENSE"),
        ("cemu", "dependencies/Vulkan-Headers/LICENSE.md", "Vulkan-Headers/LICENSE.md"),
        ("sdl3", "LICENSE.txt", "SDL3/LICENSE.txt"),
        ("sdl3", "src/hidapi/LICENSE-bsd.txt", "SDL3/hidapi-LICENSE-bsd.txt"),
        ("sdl3", "src/hidapi/LICENSE-orig.txt", "SDL3/hidapi-LICENSE-orig.txt"),
        ("sdl3", "src/video/yuv2rgb/LICENSE", "SDL3/yuv2rgb-LICENSE"),
        ("fmt", "LICENSE", "fmt/LICENSE"),
        ("mesa", "docs/license.rst", "Mesa/license.rst"),
        ("mesa", "licenses/MIT", "MIT.txt"),
        ("zarchive", "LICENSE", "ZArchive/LICENSE"),
        ("pugixml", "LICENSE.md", "pugixml/LICENSE.md"),
        ("rapidjson", "license.txt", "RapidJSON/license.txt"),
        ("glm", "copying.txt", "glm/copying.txt"),
        ("glslang", "LICENSE.txt", "glslang/LICENSE.txt"),
        ("spirv-tools", "LICENSE", "SPIRV-Tools/LICENSE"),
    ]
    for component, source, target in required:
        copy(component, source, target)
    for path in sorted((sources["mesa"] / "licenses").rglob("*")):
        if path.is_file():
            copy(
                "mesa",
                str(path.relative_to(sources["mesa"])),
                "Mesa/" + str(path.relative_to(sources["mesa"])),
            )

    # Header-only/static code and nested third-party notices are not covered by
    # the top-level project licence alone. Keep exact comments, deduplicated.
    trees = {
        "cemu": [
            "src",
            "dependencies/cubeb/src",
            "dependencies/cubeb/include",
            "dependencies/imgui",
            "dependencies/ih264d",
            "dependencies/xbyak_aarch64",
        ],
        "sdl3": ["src", "include"],
        "fmt": ["src", "include"],
        "mesa": ["src", "include"],
        "zarchive": ["src", "include"],
        "pugixml": ["src"],
        "rapidjson": ["include"],
        "glm": ["glm"],
        "glslang": ["glslang", "SPIRV"],
        "spirv-tools": ["source", "include"],
    }
    for component, directories in trees.items():
        notices: dict[str, str] = {}
        for directory in directories:
            for path in sorted((sources[component] / directory).rglob("*")):
                if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
                    continue
                for notice in notice_comments(path.read_text(errors="replace")):
                    notices.setdefault(
                        notice, str(path.relative_to(sources[component]))
                    )
        if not notices:
            if component in {"cemu", "sdl3", "fmt", "mesa"}:
                raise ValueError(f"No source notices found for {component}")
            continue
        text = (
            "\n\n".join(f"Source: {path}\n{notice}" for notice, path in notices.items())
            + "\n"
        )
        (output / f"{component}-source-NOTICES.txt.gz").write_bytes(
            gzip.compress(text.encode(), mtime=0)
        )

    # Cemu redistributes four renamed Noto CJK fonts. Their name tables supply
    # the actual Adobe attribution; canonical OFL 1.1 supplies the complete terms.
    fonts = []
    for path in sorted((sources["cemu"] / "bin/resources/sharedFonts").glob("*.ttf")):
        names = font_names(path.read_bytes())
        if not any("SIL Open Font License" in name for name in names.get(13, [])):
            raise ValueError(f"Re-audit the font licence: {path.name}")
        fonts.append(
            path.name
            + "\n"
            + "\n".join(value for values in names.values() for value in values)
        )
    if len(fonts) != 4:
        raise ValueError("Expected the four audited Cemu shared fonts")
    (output / "fonts").mkdir(exist_ok=True)
    (output / "fonts/OFL-1.1.txt").write_bytes(ofl.read_bytes())
    (output / "fonts/NOTICE.txt").write_text("\n\n".join(fonts) + "\n")


if __name__ == "__main__":
    names = [
        "cemu",
        "sdl3",
        "fmt",
        "mesa",
        "zarchive",
        "pugixml",
        "rapidjson",
        "glm",
        "glslang",
        "spirv-tools",
    ]
    if len(sys.argv) != len(names) + 3:
        raise SystemExit("Expected output, ten pinned source roots, and OFL text")
    collect(
        Path(sys.argv[1]),
        dict(zip(names, map(Path, sys.argv[2:-1]))),
        Path(sys.argv[-1]),
    )
