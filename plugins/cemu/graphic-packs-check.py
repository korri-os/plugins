"""Check the bundled BotW native-aspect choices without selecting them."""

from pathlib import Path
import sys
import xml.etree.ElementTree as ET

package = Path(sys.argv[1])
text = (
    package
    / "share/Cemu/graphicPacks/downloadedGraphicPacks/BreathOfTheWild/Graphics/rules.txt"
).read_text()
sections = []
for block in text.split("[Preset]")[1:]:
    fields = {}
    for line in block.splitlines():
        if line.startswith("["):
            break
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            fields[key.strip()] = value.split("#", 1)[0].strip()
    sections.append(fields)
aspects = [s for s in sections if s.get("category") == "Aspect Ratio"]
native = next(
    (s for s in aspects if s.get("name") == "31:27 (1240x1080 handheld)"), None
)
assert native is not None, "BotW must offer the optional 31:27 native-aspect preset"
assert native["$aspectRatioWidth"] == "31"
assert native["$aspectRatioHeight"] == "27"
assert native["$showSquareHUDOption:int"] == "1"
assert "default" not in native
# Like upstream's 4:3 and 5:4 options, retain the original game texture dimensions.
for aspect in [native, *[s for s in aspects if s.get("name") in ("4:3", "5:4")]]:
    assert "$gameWidth" not in aspect and "$gameHeight" not in aspect
    assert aspect["$showSquareHUDOption:int"] == "1"
assert aspects[0]["name"] == "16:9 (Default)"
defaults = text.split("[Default]", 1)[1].split("[Preset]", 1)[0]
for line in [
    "$gameWidth = 1280",
    "$gameHeight = 720",
    "$aspectRatioWidth = 16",
    "$aspectRatioHeight = 9",
]:
    assert line in defaults
condition = "((($aspectRatioWidth - 31) == 0) + (($aspectRatioHeight - 27) == 0)) == 2"
for width, height in [(1240, 1080), (1028, 896), (827, 720), (620, 540), (413, 360)]:
    preset = next(
        (
            s
            for s in sections
            if s.get("category") == "Resolution"
            and s.get("name") == f"{width}x{height}"
        ),
        None,
    )
    assert preset is not None, (width, height)
    assert preset["condition"] == condition
    assert preset["$width"] == str(width) and preset["$height"] == str(height)
    assert "default" not in preset
assert (
    ET.parse(package / "share/Cemu/settings.xml").getroot().find("GraphicPack") is None
), "Aspect selection belongs to the player, not the seed"
print("Cemu optional BotW 31:27 pack presets and unchanged defaults passed")
