"""Check the packaged Cemu-only Vulkan override, without requiring a GPU."""
import json
from pathlib import Path
import re
import sys

package = Path(sys.argv[1])
architecture = sys.argv[2]
wrapper = (package / "bin/cemu").read_text()
match = re.search(r'^export VK_DRIVER_FILES="([^"]+)"$', wrapper, re.MULTILINE)
if architecture == "aarch64":
    assert match, "aarch64 Cemu must pin its Turnip ICD"
    icd = Path(match[1])
    assert re.fullmatch(r"/nix/store/[a-z0-9]{32}-mesa-25\.3\.[0-9]+/share/vulkan/icd\.d/freedreno_icd\.aarch64\.json", str(icd)), icd
    assert 'export VK_ICD_FILENAMES="$VK_DRIVER_FILES"' in wrapper
    driver = Path(json.loads(icd.read_text())["ICD"]["library_path"])
    assert driver == icd.parents[3] / "lib/libvulkan_freedreno.so", driver
    assert driver.is_file(), driver
else:
    assert match is None, "non-aarch64 Cemu must retain host ICD selection"
    assert "export VK_ICD_FILENAMES=" not in wrapper
print(f"Cemu {architecture} Turnip selection passed")
