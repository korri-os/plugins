# itch.io: supported Bitsy attachments

`@korri:itchio` preserves the legacy provider identity. This source-only slice
acquires only explicit free, author-offered raw `.bitsy` attachments. It does
not acquire browser exports, extract HTML/script data, claim paid files, use
login credentials or cookies, or download through a plugin-owned HTTP client.
The separate `@korri:bitsybox` plugin supplies the native system and runner.
Its license and publication restrictions remain unchanged.

## Finite live discovery

The provider title states its limited scope: **itch.io (supported Bitsy
attachments)**. Queries use legacy public tag/free RSS feeds, with the real
`https://itch.io/search?q=...&type=games` fallback. Results are filtered to the
only verified creator host, `0neforgetfulbug.itch.io`. This is not the entire
made-with-Bitsy catalog, nor a curated list of pinned games. A supported
creator's exact game URL can also be searched directly; its page is fetched
live. Unsupported creator URLs are not fetched. Unsupported detail ids fail
instead of inventing a title or acquiring outside the approved scope.

A listing does not establish a downloadable file. Search claims therefore omit
artifact/system hints. Core's normal details call replaces the held claim
with verified metadata. Details enable Bitsy acquisition only when the static
public `init_ViewHtmlGame` JSON explicitly contains numeric `actual_price: 0`
and `min_price: 0` for an HTML game, with a CSRF token and raw `.bitsy` upload
controls. Missing prices (including the real page's price-less `data.json`)
are not free. Multiple raw uploads require a unique file-name hint; the
resolver returns safe choices rather than guessing. No new persisted schema
or provider-specific RPC is introduced.

## Grounded download path

The real case is
`https://0neforgetfulbug.itch.io/average-day-in-america`. Its author explicitly
offers `adia.bitsy` for Bitsybox, separate from the browser version's
bitsymuse hack. The parser fixture contains only recorded public metadata and
upload-control excerpts; its CSRF token is replaced. No game or signed URL is
bundled, and the author's rights remain unchanged.

The resolver uses three handler calls: request the public page; request a
form POST with its CSRF token to the selected `/file/<upload id>` using
legacy's query parameters; return the final artifact URL and exact upload
filename. Core performs all HTTP effects and immediately downloads through
its existing acquisition queue, identification, cache and record path. Signed
URLs are short-lived (the observed URL expires after 60 seconds); they are not
configuration or library records. A later download resolves a fresh URL.

The finite manifest approves `itch.io`, `0neforgetfulbug.itch.io`, and the
observed exact artifact host
`itchio-mirror.cb031a832f44726753d6267436f3b414.r2.cloudflarestorage.com`.
Every redirect still passes Core's exact-host and SSRF checks. A changed
creator/CDN requires a reviewed manifest update and normal approval; it does
not expand automatically. Refusals remain failures, not prompts to bypass a
gate. No Cookie or Authorization support is requested.

## Checks and limits

Run focused offline package/admission/type/handler checks:

```sh
nix build --no-link .#checks.x86_64-linux.korri-itchio-plugin \
  .#checks.aarch64-linux.korri-itchio-plugin
```

The publisher pins Core `5f4f89e2bc876ba3029cbadfcc0b8641299c90fd`. Core
`1e5f6b8b432d3970b9814884769503827d0c8629` first provided request-turn form
POSTs. That pin was a consumed contract change, not an unrelated dependency
update. No developer-path override is needed. Tests use
static fixtures and synthetic artifact URLs, not live signed links.

Core also carries the ignored live test
`acquisition::provider_live_tests::public_bitsy_attachment_search_acquire_route_and_native_launch`.
The coordinator can run it once with `cargo test --lib <exact test name> --
--ignored --exact --nocapture` in Core's `korrid` shell, under Xvfb with Python
and xdotool. Set `KORRI_LIVE_ITCHIO_PACKAGE` and `KORRI_LIVE_BITSYBOX_PACKAGE`
to the two exact immutable package outputs, `KORRI_LIVE_KORRID` to the current
Core binary, and `KORRI_LIVE_BITSY_RUNTIME_TEST` to this publisher's
`plugins/bitsybox/runtime.test.py`. It loads actual packaged declarations and
manifest hosts, uses production public-DNS acquisition without retries, checks
imported byte identity and cache routing, then runs the existing native test.
Its library is disposable. It does not install packages or change trust.

The coordinator ran that live test against the pinned Core revision and the
actual packaged provider and runner. Search, details, acquire, import, cache
routing, byte identity, native startup and exit passed. The acquired file was
30,267 bytes, SHA-256
`dafd29ad1638425c743efda2af273a29376989904502193d216164235e8f3ace`.
No cookies were used. This is not full-game, audible-audio or physical-control
acceptance. Tests do not grant publication, trust, installation, or device
acceptance. No deployment or publication belongs to this slice.
