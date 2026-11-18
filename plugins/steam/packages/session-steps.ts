// Build-time data only. The plugin still ships as effect-free TypeScript source.
// Usage: bun session-steps.ts [runner]; the runner defaults to `steam`.
import { runners } from "../plugin"

// Bun provides it; the strict declaration check has no Node types.
declare const process: { argv: string[] }

const shellWord = (value: string): string => `'${value.replaceAll("'", "'\\''")}'`
const name = (process.argv[2] ?? "steam") as keyof typeof runners
const runner = runners[name]
if (!runner) throw new Error(`no runner ${name}`)
const steps = runner.steps
console.log([
  `# Generated from runners.${name}.steps; do not edit.`,
  `launch_steps=(${steps.map(step => shellWord(step.key)).join(" ")})`,
  `launch_step_labels=(${steps.map(step => shellWord(step.label)).join(" ")})`,
].join("\n"))
