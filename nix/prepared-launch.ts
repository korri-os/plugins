// Core's host-prepared launch handoff for `korrid plugin-launch`.
//
// Since Core d65b285dae77 the unit's `korrid plugin-launch SOURCE INPUT_JSON
// COMPOSITION_JSON PREPARED_JSON` evaluates no plugin. It validates and
// executes PREPARED_JSON, the private PreparedLaunch record that the host
// builds before the unit starts (services/korrid/src/launcher/plugin_launch.rs,
// prepare_handoff). With no modifiers, `plan` is the runner's launch.prepare
// output and `runnerArgv` is that plan's command and arguments. The host also
// sets `releaseId`; the executor ignores it, so these checks leave it out.
// Core exposes no command that prepares a launch, so the checks evaluate the
// packaged plugin.ts here.
//
// Run directly, it prints the record for one input:
//   bun prepared-launch.ts PLUGIN_TS INPUT_JSON
import process from "node:process"
import type { PluginLaunchOutput } from "../contracts/generated/korrid"

export function preparedLaunch(plan: PluginLaunchOutput): string {
  return JSON.stringify({ plan, runnerArgv: [plan.command, ...plan.args] })
}

if (import.meta.main) {
  const [source, input] = process.argv.slice(2)
  if (!source || !input) {
    throw new Error("usage: bun prepared-launch.ts PLUGIN_TS INPUT_JSON")
  }
  const plugin = await import(source)
  process.stdout.write(preparedLaunch(plugin.handlers["launch.prepare"](JSON.parse(input))))
}
