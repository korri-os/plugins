# Focused checks — 2026-10-23

| Check | Result |
|---|---|
| `nix build --no-link .#checks.aarch64-linux.korri-eden-package .#checks.aarch64-linux.korri-eden-admission` | Passed, cached outputs `jm57f095…` / `r6584bcg…` |
| Same two x86_64 gates | Passed, cached outputs `b67hj7vf…` / `7jqrf9p4…` |
| Personal generated source vs committed source | Exact single runner-ID literal substitution; no other difference |
| Real personal-source admission/executor check | Passed for two accounts, including refused callback inputs |
| `prove-discovery.py` on real before/after snapshots | Passed; output in `discovery-proof.txt` |
| Three negative proof cases | All rejected: changed existing value, removed existing game, unrelated new game |
| Final non-SMO semantic comparison and settings readback | Passed; proof output retained |
| Ruff 0.14.9 lint and format check, new proof script | Passed |
| mypy 1.19.1 `--check-untyped-defs`, published PyYAML stubs | Passed, 1 file |
| Local documentation links | 40 resolved |
| Evidence JSON syntax | 22 files parsed |
| Direct observer CSV parse | One destruction record, zero Present completions; corrected the initial header-only description |
| Python syntax / `git diff --check` | Passed |
| Real device path | Signature-checked delivery, inspect/install/enable, offline discovery, RPC settings, exact library reserve/start/stop exercised |
| Actual game acceptance | Failed graphics gate; no measured FPS, Dynarmic comparison or soak |

The new proof script needs PyYAML. Verification used the cached PyYAML 6.0.3
package and its published `types-pyyaml` stubs, not custom permissive stubs.
Initial Ruff found an unused import, which was removed. Initial mypy could not
find the YAML stubs; providing the existing published stubs resolved that error.
No production TypeScript, shell launcher, collector or Nix package code changed.
No full repository suite, publication or default-branch deployment ran.
