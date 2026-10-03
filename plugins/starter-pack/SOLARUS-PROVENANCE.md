# Solarus quest provenance

The owner selected Perlshaw's Problems and Vegan on a Desert Island on
2026-10-03. Blue Isle is excluded. The selection accepts the first game's short
test-game scope and the second game's unfinished state. It does not establish
full-game or handheld acceptance.

| Quest | Actual pinned source | Original archive SHA-256 | Media evidence |
|---|---|---|---|
| Perlshaw's Problems 0.8 | [cdc5ea95d84be7051da08a1c770e511648aae1b0](https://github.com/AgentNintaku/perlshaws-problems/tree/cdc5ea95d84be7051da08a1c770e511648aae1b0) | `ff05a636102c4bfc874c7ecf6ee449a71bc7afbe6dec0a936f4e7217d39b79b3` | All 310 inspected media/editable-art files match explicit standard CC or public-domain records. |
| Vegan on a Desert Island 0.3 | [197105cb25eb0de1b7e6d4acc25303ece1be479f](https://gitlab.com/voadi/voadi/-/tree/197105cb25eb0de1b7e6d4acc25303ece1be479f) | `56a3ce756c3aed37af0761e64e7bb1a963aee0376219b88e73e9329ba94c84a5` | The actual runtime payload contains 122 media files: 89 PNGs, 31 Oggs and two TTFs. All have exact-file or directory grants. |

Both upstreams provide GPLv3 software licenses. Their actual resource databases
carry individual asset and code exceptions. Vegan includes a CC BY-SA test
script and mixed GPL/CC map directories. Do not label every file GPL-only.
The original database, older attribution notice, file bytes and embedded tags
remain unchanged. `CREDITS.md` supplies the additional embedded-author credits.
The two actual Vegan fonts have CC BY 4.0 grants confirmed by their creator.
The older notice names Minecraftia, but that font is absent from this source.

Vegan's `sprites/entities/gleasonator.png` inherits a directory declaration
listing CC BY-SA 4.0, CC BY 4.0 and CC0 with several authors. Its exact member
selector is not specified. Retain the complete declaration and credits, not an
assumed CC0 selection. The listed grants permit commercial redistribution.
This packaging makes no new per-file license choice.

The original Vegan attribution file specifically licenses `quest.dat` and
adds contributor notices, so it accompanies the archive and external notices.
The source README links a credits wiki. Its first-party snapshot is pinned to
version `ab311c41cb1b7fce58ff3465889f9cd272c20a4b` and JSON SHA-256
`5f0e4bef3e281fd99aa468cacdd3c7b6f4d6429079096b767ff748b4c17f9960`.
The bundle preserves that JSON and its exact Markdown content. Full CC legal
texts are fetched with their own native hash pins. GPL text comes from each
original source. These notices do not replace any original grants.

Vegan's root `screenshot.gif` is unnecessary for play and has no exact CC
variant selector. It is not copied into the content payload. This is not a
claim that its positive free-culture blanket grant prohibits redistribution.

No current PNG in either candidate matched the pinned ZSDX reference images
explicitly marked proprietary, after native RGBA decoding. That limited exact
comparison does not detect cropped, recolored or partial copies and does not
prove every creator's ownership. No noncommercial, no-derivatives, proprietary
or fair-use-only exception was found in the inspected runtime media notices.
This is an engineering permission inventory, not legal clearance.

The Nix package pins original archives and preserves runtime file bytes. Its
only layout change puts `data/` at the native quest archive root and includes
Perlshaw's repository-root editor metadata. No runtime migration, alias,
quest-script patch, image optimization or media conversion is introduced.
Asset files remain outside Git. The content output and normal signed cache
publication are distinct from the quest-free Solarus engine output.
