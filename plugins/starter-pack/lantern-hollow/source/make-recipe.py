#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p "python3.withPackages (p: [ p.pillow ])"
"""Generate the Lantern Hollow recipe (out/recipe.json) from CC0 Kenney tiles,
original hand-drawn tiles, CC0 MIDI and CC0 SFX.

Coordinates: screens are 16x11 cells. Screen id = row*16 + col.
"""
import json
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
ASSETS = HERE / "assets" / "unpacked"
OUT = HERE / "out"
SFX = ASSETS / "subspace_512_sfx" / "The Essential Retro Video Game Sound Effects Collection [512 sounds] By Juhani Junkala"
MIDI = ASSETS / "15_melodic_rpg_chiptunes_mid"

# ---------------------------------------------------------------- images
def kenney(pack, n):
    name = {"T": "kenney_tiny-town", "D": "kenney_tiny-dungeon"}[pack]
    return Image.open(ASSETS / name / "Tiles" / f"tile_{n:04d}.png").convert("RGBA")

def K(ref):
    return kenney(ref[0], int(ref[1:]))

def over(base, top):
    b = base.copy()
    b.alpha_composite(top)
    return b

def bob(img):
    """Second animation frame: sprite lowered by one pixel."""
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img.crop((0, 0, 16, 15)), (0, 1))
    return out

def rot(img, deg):
    return img.rotate(deg, expand=False)

def draw(rows, colours):
    """Original pixel art from a character grid."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in colours:
                img.putpixel((x, y), colours[ch])
    return img

OUTLINE = (38, 23, 18, 255)   # replaced below by the real most-common outline
RED = (228, 59, 68, 255)
WHITE = (255, 255, 255, 255)
GOLD = (254, 174, 52, 255)
GLOW = (254, 231, 97, 255)
GREY = (90, 105, 136, 255)

# ---------------------------------------------------------------- original art
HEART8 = [
    ".##.##..",
    "#rr#rr#.",
    "#rrrrr#.",
    "#rrrrr#.",
    ".#rrr#..",
    "..#r#...",
    "...#....",
    "........",
]
HALF8 = [
    ".##.##..",
    "#rr#..#.",
    "#rr...#.",
    "#rr...#.",
    ".#r..#..",
    "..#.#...",
    "...#....",
    "........",
]
EMPTY8 = [
    ".##.##..",
    "#..#..#.",
    "#.....#.",
    "#.....#.",
    ".#...#..",
    "..#.#...",
    "...#....",
    "........",
]
CURSOR8 = [
    "........",
    "..#.....",
    "..##....",
    "..#w#...",
    "..#ww#..",
    "..#w#...",
    "..##....",
    "..#.....",
]
LANTERN = [
    "......####......",
    ".....#....#.....",
    "....########....",
    "...#ssssssss#...",
    "...#syyyyyys#...",
    "...#syggggys#...",
    "...#sygwwgys#...",
    "...#sygwwgys#...",
    "...#syggggys#...",
    "...#syyyyyys#...",
    "...#ssssssss#...",
    "....########....",
    ".....#ssss#.....",
    "....########....",
    "................",
    "................",
]
HEART16 = [
    "................",
    "................",
    "...###...###....",
    "..#rrr#.#rrr#...",
    ".#rrwrr#rrrrr#..",
    ".#rwrrrrrrrrr#..",
    ".#rrrrrrrrrrr#..",
    "..#rrrrrrrrr#...",
    "...#rrrrrrr#....",
    "....#rrrrr#.....",
    ".....#rrr#......",
    "......#r#.......",
    ".......#........",
    "................",
    "................",
    "................",
]

def pal(extra=None):
    d = {"#": OUTLINE, "r": RED, "w": WHITE, "y": GOLD, "g": GLOW, "s": GREY}
    if extra:
        d.update(extra)
    return d

def minitile_sheet(tl=None, tr=None, bl=None, br=None):
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for art, (ox, oy) in ((tl, (0, 0)), (tr, (8, 0)), (bl, (0, 8)), (br, (8, 8))):
        if art:
            img.paste(draw(art, pal()), (ox, oy))
    return img

# ---------------------------------------------------------------- tile table
tiles = {}        # name -> (index, RGBA image, pinned cset or None)
order = []
next_tile = [20]

def add(name, img, pin=None, at=None):
    if at is None:
        at = next_tile[0]
        next_tile[0] += 1
    tiles[name] = [at, img, pin]
    order.append(name)
    return at

def add_anim(name, img, pin=None, length=8):
    """A run of tiles alternating frame / one-pixel bob. Native animation
    styles read several consecutive tiles, so never leave a neighbour short."""
    at = next_tile[0]
    for k in range(length):
        add(name if k == 0 else f"{name}+{k}", img if k % 2 == 0 else bob(img), pin, at + k)
    next_tile[0] = at + length
    return at

GRASS = K("T0")
FLOOR = K("D0")

# reserved minitiles (life meter 0/1/4, save-menu cursor 2)
add("mini0", minitile_sheet(HEART8, HALF8, CURSOR8, None), pin=1, at=0)
KEY8 = [
    "..###...",
    ".#yyy#..",
    ".#y.y#..",
    "..#y#...",
    "..#y#...",
    "..#yy#..",
    "..#y#...",
    "..#yy#..",
]

def minitile_sheet2():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    img.paste(draw(EMPTY8, pal()), (0, 0))
    img.paste(draw(KEY8, pal()), (8, 0))
    return img

add("mini1", minitile_sheet2(), pin=1, at=1)

# overworld
for nm, ref in [("grass", "T0"), ("grass2", "T1"), ("flowers", "T2"), ("dirt", "T40"),
                ("stone_path", "T43")]:
    add(nm, K(ref))
for nm, ref in [("tree", "T4"), ("bush", "T5"), ("bigtree", "T16"), ("orangetree", "T27"),
                ("mushroom", "T29"), ("sign", "T83"), ("fence_l", "T44"), ("fence_m", "T45"),
                ("fence_r", "T46"), ("barrel", "T107")]:
    add(nm, over(GRASS, K(ref)))
for nm, ref in [("roof_l", "T52"), ("roof_m", "T53"), ("roof_r", "T54"),
                ("roof2_l", "T64"), ("roof2_m", "T65"), ("roof2_r", "T66"),
                ("wall_l", "T72"), ("wall_m", "T73"), ("wall_r", "T75"), ("door", "T86"),
                ("window", "T84"), ("rock", "T126"), ("hill_door", "T125")]:
    add(nm, over(GRASS, K(ref)))

# dungeon
add("floor", K("D0"), pin=8)
for nm, ref in [("floor2", "D1"), ("wall", "D40"), ("wall_grate", "D28"),
                ("pillar", "D57")]:
    add(nm, K(ref))
add("lockdoor", over(FLOOR, K("D46")), pin=8)
for nm, ref in [("torch", "D29"), ("chest", "D89"), ("stairs", "D39")]:
    add(nm, over(FLOOR, K(ref)))
add("lantern_floor", over(FLOOR, draw(LANTERN, pal())))

# sprites (transparent background)
HERO = K("D88")
hero_t = add_anim("hero", HERO, pin=6)
sword_up = K("D104")
sword_t = add("sword", sword_up, pin=6)
add("sword_h", rot(sword_up, -90), pin=6, at=sword_t + 1)
next_tile[0] = sword_t + 2
add("key", K("T117"))
add("heart", draw(HEART16, pal()))
add("heart_big", draw(HEART16, pal()))
add("coin", K("T93"))
add("lantern", draw(LANTERN, pal()))
bat_t = add_anim("bat", K("D120"))
slime_t = add_anim("slime", K("D108"))
rat_t = add_anim("rat", K("D123"))
ghost_t = add_anim("ghost", K("D121"))
boss_t = add_anim("boss", K("D111"))
elder_t = add("elder", K("D100"))
# Message box: solid fill in tiles B, B+1, B+20, B+21 (native 2x2 frame pieces).
BOX = 200
for k, off in enumerate((0, 1, 20, 21)):
    img = Image.new("RGBA", (16, 16), (63, 38, 49, 255))
    add(f"box{k}", img, pin=0, at=BOX + off)
puff_t = add("puff", draw([
    "................", "................", "......#..#......", "...#..w..w..#...",
    "....w......w....", "................", "..#w........w#..", "................",
    "................", "..#w........w#..", "................", "....w......w....",
    "...#..w..w..#...", "......#..#......", "................", "................"], pal()))

# ---------------------------------------------------------------- palette groups
from collections import Counter

def colours(img):
    return {px[:3] for px in img.getdata() if px[3] >= 128}

freq = Counter()
for nm in order:
    freq.update(colours(tiles[nm][1]))
outline = freq.most_common(1)[0][0]
SHARED = [outline, RED[:3], WHITE[:3]]          # indices 1,2,3 in every cset
# Re-draw original art with the real outline colour.
OUTLINE_RGBA = outline + (255,)

def recolour(img):
    px = img.load()
    for y in range(16):
        for x in range(16):
            if px[x, y] == OUTLINE:
                px[x, y] = OUTLINE_RGBA
    return img

for nm in order:
    tiles[nm][1] = recolour(tiles[nm][1])

AVAILABLE = [2, 3, 4, 5, 7, 8, 9, 1, 10, 11, 12, 13]
groups = {}  # cset -> set(colours)

def fits(cs, cols):
    return len(groups.get(cs, set()) | cols) <= 12

assign = {}
for nm in sorted(order, key=lambda n: -len(colours(tiles[n][1]))):
    cols = colours(tiles[nm][1]) - set(SHARED)
    pin = tiles[nm][2]
    if pin is not None:
        cands = [pin]
    else:
        cands = [c for c in AVAILABLE if c in groups] + [c for c in AVAILABLE if c not in groups]
    for cs in cands:
        if fits(cs, cols):
            groups.setdefault(cs, set()).update(cols)
            assign[nm] = cs
            break
    else:
        raise SystemExit(f"cannot place {nm}")

def cset_colours(cs):
    own = sorted(groups.get(cs, set()))
    row = [(0, 0, 0)] + SHARED + own
    row += [(0, 0, 0)] * (16 - len(row))
    return row

def indexed(img, cs):
    row = cset_colours(cs)
    lookup = {c: i for i, c in enumerate(row)}
    out = []
    for px in img.getdata():
        out.append(0 if px[3] < 128 else lookup[px[:3]])
    return out

# UI cset 0: black background, shared colours, greys, gold, white text at 15.
ui = [(0, 0, 0)] + SHARED + [(40, 40, 52), (70, 70, 90), (110, 110, 130), (150, 150, 170),
      (190, 190, 205), (60, 30, 20), (120, 70, 40), (200, 120, 50), (254, 174, 52),
      (254, 231, 97), (230, 230, 240), (255, 255, 255)]
palette = {}
def setcs(ds, row):
    palette[str(ds)] = [list(c) for c in row]
full = {0: ui}
for cs in range(1, 15):
    full[cs] = cset_colours(cs) if cs in groups else cset_colours(cs)
for cs in range(15):
    setcs(cs, full[cs])
# Level palette 0: c2,c3,c4,c9, fades x3 (copies), newcsets c1,c5,c7,c8.
LVL = 15
lvl_rows = [full[2], full[3], full[4], full[9]] + [full[2], full[3], full[4]] * 3 + [full[1], full[5], full[7], full[8]]
for i, row in enumerate(lvl_rows):
    setcs(LVL + i, row)
# Sprite palettes.
for i in range(30):
    setcs(8719 + i, full[i % 15])

# ---------------------------------------------------------------- combos
combos = []
cid = {}
def combo(name, tile_name, solid=0, type=0, flag=0):
    i = len(combos) + 1  # combo 0 stays empty
    combos.append({"id": i, "tile": tiles[tile_name][0], "solid": solid, "type": type,
                   "flag": flag, "label": name})
    cid[name] = (i, assign[tile_name])
    return i

S = 15
# Combo 0 fills any unused cell; keep it blank and solid (tile 0 holds the
# life-meter minitiles, which must never appear as scenery).
add("blank", Image.new("RGBA", (16, 16), (0, 0, 0, 255)), pin=0, at=199)
assign["blank"] = 0
combos.append({"id": 0, "tile": 199, "solid": S, "label": "blank"})
for n in ["grass", "grass2", "flowers", "dirt", "stone_path", "floor", "floor2", "stairs"]:
    combo(n, n)
for n in ["tree", "bush", "bigtree", "orangetree", "mushroom", "sign", "fence_l", "fence_m",
          "fence_r", "barrel", "roof_l", "roof_m", "roof_r", "roof2_l", "roof2_m", "roof2_r",
          "wall_l", "wall_m", "wall_r", "door", "window", "rock", "wall", "wall_grate",
          "pillar", "torch", "chest"]:
    combo(n, n, solid=S)
C_CAVE, C_STAIR, C_LOCK = 2, 1, 59
combo("hill_door", "hill_door", type=C_CAVE)
combo("stairs_up", "stairs", type=C_STAIR)
combo("lockdoor", "lockdoor", solid=S, type=C_LOCK)
combo("lock_open", "floor")  # lock blocks become the NEXT combo when opened
combo("lantern_floor", "lantern_floor")

# ---------------------------------------------------------------- screens
W, H = 16, 11

class Screen:
    def __init__(self, m, sc, fill):
        self.m, self.sc = m, sc
        self.cells = [fill] * (W * H)
        self.flags = [0] * (W * H)
        self.extra = {}
    def put(self, x, y, name):
        self.cells[y * W + x] = name
    def rect(self, x0, y0, x1, y1, name):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, name)
    def text(self, rows, legend):
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch in legend:
                    self.put(x, y, legend[ch])
    def to_json(self):
        d = {"map": self.m, "screen": self.sc,
             "data": [cid[c][0] for c in self.cells],
             "cset": [cid[c][1] for c in self.cells],
             "sflag": self.flags}
        d.update(self.extra)
        return d

OW = {".": "grass", ",": "grass2", "*": "flowers", "T": "tree", "B": "bush", "O": "bigtree",
      "Y": "orangetree", "m": "mushroom", "s": "sign", "d": "dirt", "p": "stone_path",
      "[": "fence_l", "=": "fence_m", "]": "fence_r", "b": "barrel",
      "1": "roof_l", "2": "roof_m", "3": "roof_r", "4": "roof2_l", "5": "roof2_m", "6": "roof2_r",
      "7": "wall_l", "8": "door", "9": "wall_r", "w": "window", "R": "rock", "H": "hill_door"}

ow = {}
ow[0x00] = [
    "TTTTTTTTTTTTTTTT",
    "TOT.,..*....,..T",
    "T..123....123..T",
    "T..456.*..456..T",
    "T..789..,.7w9..T",
    "T...d..ddd..d...",
    "T.*.dddd.dddd...",
    "T..,....d....*.T",
    "T.m..B..d..B...T",
    "TT..,...d....,TT",
    "TTTTTTT.d.TTTTTT",
]
ow[0x01] = [
    "RRRRRRRRRRRRRRRR",
    "RRRRRRRHRRRRRRRR",
    "RRRRRR.pp.RRRRRR",
    "TRRRR..pp..RRRRT",
    "..TT...pp...TT..",
    ".......pp.......",
    "...*...pp..,....",
    "..B....pp....B..",
    "T......pp......T",
    "TT.,...pp....,TT",
    "TTTTTT.pp.TTTTTT",
]
ow[0x02] = [
    "TTTTTTTTTTTTTTTT",
    "T.,....Y...,...T",
    "T..YY.....YY...T",
    "...Y..*.....Y..T",
    "......B.B......T",
    "..*..........*.T",
    "....Y..m..Y....T",
    "T.....,........T",
    "T..YY.....YY...T",
    "TT......,....YTT",
    "TTTTTTT..TTTTTTT",
]
ow[0x10] = [
    "TTTTTTT.d.TTTTTT",
    "T.......d......T",
    "T..[==]..d.....T",
    "T..bb....d..*..T",
    "T.....,..d......",
    "T..*.....ddddddd",
    "T...123.......,.",
    "T...456...B.....",
    "T...7w9.......*T",
    "TT.....,.....TTT",
    "TTTTTTTTTTTTTTTT",
]
ow[0x11] = [
    "TTTTTT.pp.TTTTTT",
    "T.....,pp......T",
    "T..*...pp..*...T",
    "....s..pp.......",
    "ddddddddpppppppp",
    ".......pp.......",
    "...B...pp...B...",
    "T......pp......T",
    "T.*..........*.T",
    "TT...,....,...TT",
    "TTTTTTTTTTTTTTTT",
]
ow[0x12] = [
    "TTTTTTTT..TTTTTT",
    "T..............T",
    "..*..YY...YY...T",
    "........*......T",
    "ddddd..........T",
    ".....ddd....B..T",
    "....Y...dd.....T",
    "T......,..d..Y.T",
    "T..mm......d...T",
    "TT..........,.TT",
    "TTTTTTTTTTTTTTTT",
]

screens = []
for sc, rows in ow.items():
    s = Screen(0, sc, "grass")
    s.text(rows, OW)
    screens.append(s)
ow_scr = {s.sc: s for s in screens}

# Cave in the hill (screen 0x01) leads to the dungeon entrance (dmap 1, screen 0x34).
WT_IWARP = 4
ow_scr[0x01].extra.update({"tilewarp": {"type": WT_IWARP, "dmap": 1, "scr": 0x34},
                           "warpreturn": [7 * 16, 2 * 16]})
# The elder (a screen NPC) speaks the intro once; the engine shows a screen
# string only through such a guy.
GUY_ELDER = 1
ow_scr[0x11].extra.update({"str": 1, "guy": GUY_ELDER, "warpreturn": [7 * 16, 8 * 16]})
# A few bats in the eastern grove.
ow_scr[0x02].extra.update({"enemy": [54, 54, 54]})
ow_scr[0x12].extra.update({"enemy": [42, 42]})

# Dungeon rooms (map 1).
DG = {".": "floor", ",": "floor2", "#": "wall", "g": "wall_grate", "P": "pillar",
      "t": "torch", "c": "chest", "L": "lockdoor", "^": "stairs_up", "*": "lantern_floor"}

def room(sc, doors, rows=None, extra=None):
    s = Screen(1, sc, "floor")
    s.rect(0, 0, 15, 0, "wall"); s.rect(0, 10, 15, 10, "wall")
    s.rect(0, 0, 0, 10, "wall"); s.rect(15, 0, 15, 10, "wall")
    for d, kind in doors.items():
        cells = {"N": [(7, 0), (8, 0)], "S": [(7, 10), (8, 10)],
                 "W": [(0, 5)], "E": [(15, 5)]}[d]
        for (x, y) in cells:
            s.put(x, y, "floor" if kind == "open" else "lockdoor")
    for (x, y) in [(2, 1), (13, 1), (2, 9), (13, 9)]:
        s.put(x, y, "torch") if s.cells[y * W + x] == "floor" else None
    if rows:
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch in DG and ch != " ":
                    s.put(x, y, DG[ch])
    if extra:
        s.extra.update(extra)
    screens.append(s)
    return s

ITEM_KEY, ITEM_HEARTC = 9, 28
F_ITEM = 0x02
entry = room(0x34, {"N": "open"}, rows=[
    "", "", "", "", "", "", "", "", "            ^   ",
], extra={"warpreturn": [7 * 16, 8 * 16],
          "tilewarp": {"type": WT_IWARP, "dmap": 0, "scr": 0x01}})
room(0x24, {"S": "open", "W": "open", "E": "open", "N": "lock"},
     rows=["", "   P        P   ", "", "", "", "", "", "", "   P        P   "],
     extra={"enemy": [54, 54, 54, 54]})
room(0x23, {"E": "open"}, rows=["", "", "", "    ,,,,,,,,    ", "    ,......,    ",
                               "    ,......,    ", "    ,,,,,,,,    "],
     extra={"enemy": [42, 42, 42, 42], "flags": F_ITEM, "item": ITEM_KEY, "hasitem": 1,
            "itemx": 7 * 16, "itemy": 5 * 16})
room(0x25, {"W": "open"}, rows=["", "", "  gggg    gggg  "],
     extra={"enemy": [44, 44, 44], "item": 2, "hasitem": 1, "itemx": 12 * 16, "itemy": 6 * 16})
room(0x14, {"S": "open", "E": "open", "N": "open"},
     rows=["", "", "    P      P    ", "", "", "", "", "    P      P    "],
     extra={"enemy": [41, 41, 41]})
room(0x15, {"W": "open"}, rows=["", "", "", "      cc        "],
     extra={"enemy": [41, 44, 41, 44], "flags": F_ITEM, "item": ITEM_KEY, "hasitem": 1,
            "itemx": 7 * 16, "itemy": 6 * 16})
boss = room(0x04, {"S": "open"}, rows=[
    "#######LL#######",
    "#.....#..#.....#",
    "#.....#*.#.....#",
    "#.....####.....#",
], extra={"enemy": [79], "flags": F_ITEM, "item": ITEM_HEARTC, "hasitem": 1,
          "itemx": 7 * 16, "itemy": 6 * 16,
          # A: south door. B: inside the lantern alcove (test entry only).
          "warpreturns": [[7 * 16, 9 * 16], [7 * 16, 1 * 16], [7 * 16, 9 * 16], [7 * 16, 9 * 16]],
          "warparrival": [7 * 16, 9 * 16]})
# Re-make the lantern alcove: the lock is in the alcove wall, the lantern inside.
boss.cells = boss.cells  # layout above already places it
for s in screens:
    if s.m == 1 and s.sc == 0x04:
        s.put(7, 0, "wall"); s.put(8, 0, "wall")
        s.put(7, 3, "lockdoor"); s.put(8, 3, "lockdoor")
        s.put(6, 3, "wall"); s.put(9, 3, "wall")
        s.rect(7, 1, 8, 2, "floor"); s.put(7, 2, "lantern_floor"); s.put(8, 2, "lantern_floor")
        s.flags[2 * W + 7] = 15; s.flags[2 * W + 8] = 15   # mfZELDA: built-in ending
        for y in range(1, 3):
            s.put(6, y, "wall"); s.put(9, y, "wall")

# ---------------------------------------------------------------- recipe
tile_json = []
for nm in order:
    at, img, _ = tiles[nm]
    tile_json.append({"i": at, "px": indexed(img, assign[nm])})

def spr(name):
    return tiles[name][0]

def cs_of(name):
    return assign[name]

midis = [
    {"i": 0, "path": str(MIDI / "rpgchip03_town.mid"), "title": "Village"},
    {"i": 1, "path": str(MIDI / "rpgchip06_dungeon.mid"), "title": "The Hollow"},
    {"i": 2, "path": str(MIDI / "rpgchip12_the_evil_one.mid"), "title": "Keeper of the Hollow"},
]

def wrap(text, width=24):
    """Pad each line to the box width so the engine never splits a word."""
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    lines.append(cur)
    return "".join(l.ljust(width) for l in lines).rstrip()


def sfx(slot, rel, name):
    return {"slot": slot, "path": str(SFX / rel), "name": name}

sfx_list = [
    sfx(30, "Weapons/Melee/sfx_wpn_sword1.wav", "Swing"),
    sfx(11, "General Sounds/Simple Damage Sounds/sfx_damage_hit1.wav", "Enemy hit"),
    sfx(10, "Explosions/Shortest/sfx_exp_shortest_hard1.wav", "Enemy defeated"),
    sfx(19, "General Sounds/Simple Damage Sounds/sfx_damage_hit3.wav", "Hurt"),
    sfx(20, "General Sounds/Coins/sfx_coin_cluster1.wav", "Pickup"),
    sfx(25, "General Sounds/Fanfares/sfx_sounds_fanfare1.wav", "Item fanfare"),
    sfx(27, "General Sounds/Positive Sounds/sfx_sounds_powerup10.wav", "Secret"),
    sfx(9, "Movement/Opening Doors/sfx_movement_dooropen1.wav", "Door"),
    sfx(29, "Movement/Climbing Stairs/sfx_movement_stairs1a.wav", "Stairs"),
    sfx(18, "General Sounds/Menu Sounds/sfx_menu_move1.wav", "Text"),
]

recipe = {
    "header": {"title": "Lantern Hollow", "author": "Korri"},
    "palette": palette,
    "palnames": {"0": "Lantern Hollow"},
    "tiles": tile_json,
    "combos": combos,
    "map_count": 2,
    "screens": [s.to_json() for s in screens],
    "dmaps": [
        {"i": 0, "map": 0, "type": 1, "xoff": 0, "cont": 0x11, "color": 0,
         "grid": [255] * 8, "name": "Village", "title": "Lantern Hollow", "music": 1},
        {"i": 1, "map": 1, "type": 0, "level": 1, "xoff": 0, "cont": 0x34, "color": 0,
         "grid": [0b00011000, 0b00011000, 0b00111000, 0b00001000, 0, 0, 0, 0],
         "name": "The Hollow", "title": "The Hollow", "music": 2},
    ],
    "items": [
        {"id": 5, "name": "Sword", "tile": spr("sword"), "csets": cs_of("sword"),
         "wpn_tile": spr("sword"), "wpn_csets": cs_of("sword")},
        {"id": 9, "name": "Key", "tile": spr("key"), "csets": cs_of("key")},
        {"id": 2, "name": "Heart", "tile": spr("heart"), "csets": cs_of("heart")},
        {"id": 28, "name": "Heart Vessel", "tile": spr("heart_big"), "csets": cs_of("heart_big")},
        {"id": 0, "name": "Coin", "tile": spr("coin"), "csets": cs_of("coin")},
    ],
    "sprites": [],
    "guys": [
        {"id": 1, "name": "Elder", "tile": elder_t, "cset": cs_of("elder"), "anim": 0},
        {"id": 54, "name": "Bat", "tile": bat_t, "cset": cs_of("bat"), "anim": 3, "hp": 2, "item_set": 1},
        {"id": 42, "name": "Slime", "tile": slime_t, "cset": cs_of("slime"), "anim": 3, "hp": 4, "item_set": 1},
        {"id": 44, "name": "Rat", "tile": rat_t, "cset": cs_of("rat"), "anim": 3, "hp": 4, "item_set": 1},
        {"id": 41, "name": "Wisp", "tile": ghost_t, "cset": cs_of("ghost"), "anim": 3, "hp": 6, "item_set": 1},
        {"id": 79, "name": "Hollow Keeper", "tile": boss_t, "cset": cs_of("boss"), "anim": 3, "hp": 24, "dp": 4, "item_set": 0},
    ],
    "dropsets": [
        {"i": 0, "name": "Nothing", "none": 1, "items": []},
        {"i": 1, "name": "Hearts", "none": 6, "items": [[2, 4]]},
    ],
    "hero": {"dirs": [[hero_t, 0, 0], [hero_t, 0, 0], [hero_t, 1, 0], [hero_t, 0, 0]],
             "hold": [hero_t]},
    "strings": [
        {"text": wrap("The lanterns of the Hollow have gone dark. Take your sword, find the Great Lantern under the hill, and bring back the light."), "box": BOX},
        {"text": wrap("Old doors open with old keys. The Great Lantern waits at the top of the Hollow."), "box": BOX},
    ],
    "sfx": sfx_list,
    "midis": midis,
    "hud": {
        "life": [168, 0],
        "key_icon": [8, 36, 1, 1],
        "keys": [20, 36],
        "passive_text": [[8, 12, "LANTERN HOLLOW", 0]],
        "active_text": [[128, 40, "PAUSED", 1], [128, 72, "Find the Great Lantern", 1],
                         [128, 84, "at the top of the Hollow.", 1],
                         [128, 120, "Press START to return.", 1]],
    },
    "init": {"start_dmap": 0, "items": [5], "counter": {"0": 48}, "mcounter": {"0": 48},
             "cont_heart": 48},
}
# Test variants only (never published): LH_START=dmap:screen:x:y[:keys]
import os
if os.environ.get("LH_START"):
    d, sc, x, y, *k = (int(v, 0) for v in os.environ["LH_START"].split(":"))
    recipe["init"]["start_dmap"] = d
    recipe["dmaps"][d]["cont"] = sc
    for s in recipe["screens"]:
        if s["map"] == recipe["dmaps"][d]["map"] and s["screen"] == sc:
            s["warparrival"] = [x, y]
            s["warpreturn"] = [x, y]
            s.pop("str", None); s.pop("guy", None)
    if k:
        recipe["init"]["counter"]["5"] = k[0]
OUT.mkdir(exist_ok=True)
(OUT / "recipe.json").write_text(json.dumps(recipe))
print("tiles", len(tile_json), "combos", len(combos), "screens", len(screens),
      "csets used", sorted(groups), {c: len(v) for c, v in groups.items()})
