# FAKE-08 unix libretro credits and licensing

FAKE-08 is by Jon Bell (jtothebell): https://github.com/jtothebell/fake-08.
This is an independent reimplementation, not Lexaloffle's official PICO-8.
The installed LICENSE.MD is the unchanged upstream original. It lists more
platform dependencies than this unix libretro build uses.

The package's nix-support/libretro-fake08/manifest.txt records immutable
FAKE-08 and z8lua source links. original-notices/ preserves original source
files with the Lua, Eris (Florian Nuecke), Zepto-8 (Sam Hocevar), LodePNG
(Lode Vandevenne), miniz, SimpleIni (Brodie Thiesfield), Unicode ConvertUTF,
and libretro notices. Lua/z8lua and Eris are MIT; Zepto-8 code is WTFPL 2;
LodePNG has its original zlib-style license. ConvertUTF has its original
Unicode 2001-2004 permission notice, not SimpleIni's MIT license.

Additional source credits used by the core:

- tac08 by Lee Witek: https://github.com/0xcafed00d/tac08
  (cart parsing, graphics and font data).
- PicoLove by Jez Kabanov: https://github.com/gamax92/picolove
  (Lua helper functions and cart loader).
- PS4-P8 by Victor Oliva: https://github.com/voliva/ps4-p8
  (adapted Lua save-state functions; not its executable or bundled games).
- Oval drawing: Michael Dorgan's answer, https://stackoverflow.com/a/8448181,
  adapted by FAKE-08 in source/graphics.cpp. Upstream LICENSE.MD declares
  CC BY-SA 3.0: https://creativecommons.org/licenses/by-sa/3.0/.
  The answer credits Michael Abrash's ellipse algorithm. The original adapted
  source and source link are preserved in original-notices/source/graphics.cpp.

Original tac08 LICENSE, inspected at
https://github.com/0xcafed00d/tac08/blob/38c1f3bb2ae81c06983dc5132d45f0c8747dff95/LICENSE:

```
MIT License

Copyright (c) 2018 Lee Witek

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Original PicoLove LICENCE.md, inspected at
https://github.com/gamax92/picolove/blob/c505d6e3c8f0d73096c6ccffe81506b40e6a01ef/LICENCE.md:

```
Copyright (c) 2015 Jez Kabanov <thesleepless@gmail.com>

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgement in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.
```

Original PS4-P8 license section of README.md, inspected at the revision
referenced by FAKE-08's p8GlobalLuaFunctions.h:
https://github.com/voliva/ps4-p8/blob/ecba7f93ef9ba73ccb121b45ede6f46e651cef65/README.md:

```
MIT

Copyright 2021 Victor Oliva

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

No standalone player, official PICO-8 runtime, Vita postcard, platform art,
or sample games are installed. Cartridge authors retain their own licenses.
This core's license does not grant rights to any game.
