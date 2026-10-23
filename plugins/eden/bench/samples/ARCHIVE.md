# Private raw evidence archive

Raw traces, full logs/dmesg, maps/backend runtime samples, process dumps,
administrative source captures and duplicate images are not published here.
Untouched originals are on the collecting host at:

```
~/.local/state/korri-eden-evidence/<sample-dir>/<relative-file>
```

Directories are mode 700; files are mode 600. Each sample's `ARCHIVE.sha256`
lists the SHA256 of the **unredacted original**, not its former public/redacted
copy. Verify from the private sample directory, for example:

```sh
cd "$HOME/.local/state/korri-eden-evidence/odin2portal-acceptance"
sha256sum -c /path/to/repository/plugins/eden/bench/samples/odin2portal-acceptance/ARCHIVE.sha256
```

Reports and summaries remain public, with identifying details replaced as
specified in [REDACTION.md](REDACTION.md). Links formerly pointing at raw files
now point to their manifest; raw filenames mentioned in reports refer to this
private archive. Retained hash manifests can also describe on-device files not
retrieved to this host; only `ARCHIVE.sha256` asserts local archive availability.

One image per device remains: Odin's full-resolution JPEG reference (encoded
from its archived PNG; encoder/version/settings and both hashes accompany it),
and Mini's unchanged native Start-screen PNG. The Mini image is **not** gameplay
acceptance. The PNG optimizer first reduced Odin's image to 986,485 bytes; JPEG
was used to keep the public evidence small. No synthetic image was generated.
