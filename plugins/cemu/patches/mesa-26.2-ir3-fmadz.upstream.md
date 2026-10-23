# Draft only — ir3: finish late algebraic lowering after lowering imul

**Not submitted.** This is a local Mesa 26.2.5 patch, not an upstream fix claim.
Hardware validation status is recorded in
[the gameplay-gated Odin report](../bench/devices/odin2portal-turnip262-phase2-2026-10-23.md).

## Issue

Cemu `29f2f1fae4631e2317977debd9eacd55cc28dd7d` on an Adreno 740
(Odin 2 Portal, Linux/MSM) crashes compiling a BotW vertex shader with Mesa
26.2.3. Fresh live compilation and cached pipeline compilation reproduce the
same pipeline BLAKE3:

```text
026211ce39d10e5e02021680ebff7da347ac4ee27a5064daeacd045d15efb127
```

The actual core resolves the rejected ALU operation to `nir_op_fmadz`, 32 bits,
`MESA_SHADER_VERTEX`. The compiler reports `Unhandled ALU op` from
`ir3_compiler_nir.c:emit_alu`; `ir3_context_error` then faults in `ralloc_free`.
The latter error-path crash is a separate issue not addressed by this patch.
No Vulkan device loss was observed in the original failure.

## Where the unsupported operation can escape

1. `ir3_compiler.c` sets `has_fmulz=true` and
   `lower_fmulz_with_abs_min=true`. The compiler wants NIR to recover `fmulz`
   patterns and lower them with the abs-min zero check.
2. Commit `acad18d97e83901002d755715fdfe202a80e0115` (MR 41165,
   "ir3: port to nir_op_fmad") advertises `has_fmad | fuse` in
   `float_mul_add{16,32,64}`. This entered Mesa 26.2.0.
3. `nir_opt_algebraic.py` late rules fuse `fadd(fmulz(a,b),c)` to `fmadz`.
   Separate late rules lower `fmulz`, `ffmaz` and `fmadz` to the abs-min select.
   A newly fused replacement is not necessarily revisited in that invocation.
4. `ir3_nir_lower_variant` in `ir3_nir.c` already runs late algebraic to a fixed
   point. This is not the final opportunity to introduce `fmulz`.
5. `ir3_context_init` in `ir3_context.c:81–100` runs `ir3_nir_lower_imul`, then
   **normal** algebraic to a fixed point. Normal algebraic can recover `fmulz`
   from its abs-min lowering. The following re-fusing call to
   `nir_opt_algebraic_late` runs **only once**.
6. That final call can leave a newly fused `fmadz` for instruction selection,
   whose switch supports `fmad` but not `fmadz`.

The pass-order explanation is source-grounded. It is not an instruction-by-
instruction trace of the game shader. The original failure itself is proven
by the core. The affected options/emitter remain in the checked Mesa 26.2.5 and
main source; this does not establish the status of every unmerged MR.

## Proposed MR

Run the final late-algebraic re-fusing step in `ir3_context_init` to a fixed
point, with DCE after each invocation. This uses the existing NIR abs-min
lowering, preserves its zero/NaN semantics, and does not disable multiply-add
fusing globally or add another emitter implementation of those semantics.

```text
plugins/cemu/patches/mesa-26.2-ir3-fmadz.patch
```

Cost: another late-algebraic traversal when the integer-lowering cleanup path
makes progress. Other late-algebraic optimizations may also iterate further.
No shader-cache compatibility workaround, system driver replacement, or Cemu
source modification is part of the patch.

## Reproducer and validation limits

The exact vertex and fragment SPIR-V modules were extracted on the development
host from `VkShaderModule` memory in the retained original core, not by running
or compiling anything on a device:

| Stage | Bytes | SHA-256 |
|---|---:|---|
| Vertex | 183876 | `82362762eed34a1b9465f0bb79c465f8d8b416dcd13458259358666c63ff8016` |
| Fragment | 34956 | `bb0724331fc0ed25fb8585936487bba929f069cb35502f33eaf321c91756a256` |

These private game-generated modules and the cores are **not included** in this
repository or this proposed submission. The extraction used the exact Mesa
26.2.3 library and DWARF, and another same-source Cemu executable for the core
loader after the original Cemu output had been garbage-collected.

A bounded synthetic IR3 harness did not produce a valid reproduction: its input
metadata caused `idx < ctx->ninputs` before the target ALU was emitted. Its
floating-point controls also allowed the zero-preserving operation to simplify
away. It is not a regression proof and is not shipped. The first three harness
attempts stopped during package configuration (duplicate Meson wrap option,
optional VA frontend, then missing zlib), before running the test.

The real patched aarch64 Turnip build passes the existing `ir3_disasm` and
`ir3_delay_test` tests on the ARM builder. See the device report for any completed
BotW validation and remaining gaps. Before submitting an MR, add a correct small
NIR test that preserves NaN/Inf behaviour and exercises the final context
cleanup, and run relevant upstream CI. No conformance-suite result is claimed.
