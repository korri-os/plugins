// Build-time data only. The plugin still ships as effect-free TypeScript source.
import { runners } from "../plugin"

const shellWord = (value: string): string => `'${value.replaceAll("'", "'\\''")}'`
const steps = runners.steam.steps
console.log([
  "# Generated from runners.steam.steps; do not edit.",
  `launch_steps=(${steps.map(step => shellWord(step.key)).join(" ")})`,
  `launch_step_labels=(${steps.map(step => shellWord(step.label)).join(" ")})`,
].join("\n"))
