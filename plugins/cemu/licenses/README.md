# Cemu notice audit

Grounding: pinned Cemu `29f2f1fae4631e2317977debd9eacd55cc28dd7d`, its
`CMakeLists.txt`, `src/imgui/CMakeLists.txt`, actual source notices and the
installed ELF/static-link evidence. `licenses.nix` uses these exact sources,
not notices copied from another installed version.

| Distributed component | Notice source |
|---|---|
| Cemu / graphic packs | Cemu `LICENSE.txt` (MPL-2.0); existing Github989 CC0 notice |
| Static Cubeb, including nested resampler code | `dependencies/cubeb/LICENSE`, copyright/licence comments in its source/include trees |
| Static ImGui, its three imstb headers and embedded ProggyClean font | `dependencies/imgui/LICENSE.txt`, source/header licence blocks and the Tristan Grimmer attribution in `imgui_draw.cpp`; common MIT terms in `MIT.txt` |
| Static ih264d | `dependencies/ih264d/NOTICE`, source notices, complete Apache-2.0 terms (the identical standard text shipped in xbyak's `LICENSE`) |
| ARM xbyak_aarch64 | Its Apache-2.0 `LICENSE` and FUJITSU source notices; retained on both architectures for a uniform notice bundle |
| Bundled Vulkan/OpenGL headers | Vulkan-Headers `LICENSE.md`, Khronos notices from Cemu's bundled headers, common MIT terms |
| Header/static utilities | Actual date.h, fast_float, robin_hood, TinyXML2 and MD5 notices, including Howard Hinnant, fast_float authors, Martin Ankerl, Lee Thomason and Alexander Peslyak |
| Four shared Noto CJK fonts | Copyright/family/licence records decoded from each actual TTF name table; complete SIL OFL-1.1 terms |
| SDL3 3.4.18 | Exact overridden source `LICENSE.txt`, HIDAPI BSD/original notices, yuv2rgb BSD notice, source notices including Sun libm |
| fmt 12.1.0 | Exact overridden source `LICENSE` and embedded source notices |
| Mesa 25.3.2 runtime / Cemu Turnip | Exact `pkgs.mesa.src`: `docs/license.rst`, its complete `licenses/` directory, source copyright/licence comments |
| ZArchive, pugixml, RapidJSON, GLM, glslang and SPIRV-Tools | Licences and source notices from the exact Nix dependencies used by this package; includes statically linked archives and header-only code |

Source notices are deduplicated by exact comment and gzip-compressed with a
fixed timestamp. They retain relative upstream filenames, not Nix source paths.
This covers nested notices without pulling complete source/development trees
into the runtime closure. Common licence texts and primary project notices
remain plain text. The Mesa notice collection is deliberately broader than the
selected Turnip driver; listing a notice does not claim every Mesa component
is linked. RapidJSON's unbuilt JSON-checker and optional licence alternatives
likewise do not change the selected library's licence.

Not distributed by this Linux build: DirectX/Metal platform code, disabled
GameMode and Discord integrations, vcpkg build machinery, and Cubeb's disabled
GoogleTest/tool targets. The system's other separately packaged shared-library
dependencies retain their own packaging; this audit does not claim a legal
review of every transitive system package.

`OFL-1.1.txt` is the unmodified canonical licence text from SPDX license-list-data
`v3.27.0`, `text/OFL-1.1.txt`:
https://raw.githubusercontent.com/spdx/license-list-data/v3.27.0/text/OFL-1.1.txt
The font attribution is taken from Cemu's actual font bytes, not from this
canonical text. A change to a font's licence or the expected four-font set fails
the notice build and requires a new audit.

`license-check.py` requires the primary notices, checks bundled attribution
markers, and compares every installed notice byte-for-byte with the generated
pinned-source bundle. It runs in both architecture package checks.
