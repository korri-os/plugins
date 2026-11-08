// Proton compatibility tools for runners that start Windows content. This
// plugin declares no runner and no handler. Its native files are declared in
// plugin.nix. A runner that lists `@korri:proton/cachyos` in its `artifacts`
// receives the ready tool directory in `input.artifacts`.
export const name = "proton"
export const title = "Proton"
export const description =
  "Proton compatibility tools: the pinned Proton-CachyOS build for this device."

// The pinned Proton-CachyOS release, one build per architecture (Core ADR
// 0052). korrid downloads and verifies this device's build, then runs
// `cachyos-unpack` on it. `bytes` is the server's Content-Length: arm64 read
// on 2026-10-19, x86_64 read from GitHub's release API on 2026-11-08.
// Build metadata derives Steam's tool name from each platform's version.
export const artifacts = {
  cachyos: {
    id: "@korri:proton/cachyos",
    platforms: {
      "aarch64-linux": {
        version: "11.0-20260601-slr-arm64",
        files: [
          {
            url: "https://github.com/CachyOS/proton-cachyos/releases/download/cachyos-11.0-20260601-slr/proton-cachyos-11.0-20260601-slr-arm64.tar.xz",
            sha256: "sha256:6793a697c8153626a9c01fcd212aae972bd1596a1d13d482620f64abf5fc69d9",
            bytes: 335847508,
          },
        ],
      },
      "x86_64-linux": {
        version: "11.0-20260601-slr-x86_64",
        files: [
          {
            url: "https://github.com/CachyOS/proton-cachyos/releases/download/cachyos-11.0-20260601-slr/proton-cachyos-11.0-20260601-slr-x86_64.tar.xz",
            sha256: "sha256:3766dc078be868536546903243a36f0c2c3fb52c1f0b9b475ee20f574fa9b99b",
            bytes: 336342276,
          },
        ],
      },
    },
    unpack: "cachyos-unpack",
  },
}
