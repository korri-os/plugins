"""Original trusted Korri multi-module Pyxel fixture. CC0-1.0."""

from pathlib import Path

import pyxel
from sibling import COLOR

pyxel.init(64, 64, title="Korri Pyxel Fixture")
# Native user_data_dir persists saves; init deliberately uses extracted cwd
# for project resources. Relative project writes are temporary upstream.
data = Path(pyxel.user_data_dir("Korri", "NativeFixture"))
save = data / "fixture-save.txt"
save.write_text(str(int(save.read_text()) + 1) if save.exists() else "1")
(data / "native-save.txt").write_text("native data path")
# Prove init's native script cwd and sibling resources were not broken.
assert Path("sibling.py").is_file()


def update():
    # A changing native frame counter proves updates continue after input.
    (data / "alive-after-start").write_text(str(pyxel.frame_count))


def draw():
    pyxel.cls(COLOR)
    pyxel.rect(8, 8, 32, 32, 11)
    assert pyxel.pget(8, 8) == 11 and pyxel.pget(0, 0) == COLOR


pyxel.run(update, draw)
