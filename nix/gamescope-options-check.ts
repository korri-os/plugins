// Proves each typed @korri:gamescope setting is a real Gamescope long option
// with the same arity, and that the built binary accepts the values Korri
// emits. Usage: bun gamescope-options-check.ts <patched main.cpp> <gamescope>
import { readFileSync } from "node:fs"
import { settingsRules, type SettingRule } from "./plugins/gamescope/compose"

const [mainCpp, gamescope] = process.argv.slice(2)
if (!mainCpp || !gamescope) throw new Error("usage: gamescope-options-check.ts <main.cpp> <gamescope>")

const source = readFileSync(mainCpp, "utf8")
const start = source.indexOf("const struct option *gamescope_options = (struct option[]){")
const end = source.indexOf("{} // keep last", start)
if (start < 0 || end < 0) throw new Error("gamescope_options table not found in main.cpp")
const table = new Map<string, string>()
for (const [, name, arity] of source.slice(start, end).matchAll(/\{ "([^"]+)", (no_argument|required_argument)/g)) {
  table.set(name, arity)
}
// Gamescope 3.16.18 declares 82 options; a different count means a different table.
if (table.size !== 82) throw new Error(`expected 82 Gamescope options, found ${table.size}`)

function samples(rule: SettingRule): string[] {
  switch (rule.kind) {
    case "integer":
    case "float":
      return [String(rule.minimum), String(rule.maximum)]
    case "choice":
      return [...rule.choices]
    case "boolean":
      return []
    case "path":
      return ["/korri-check/cursor.png"]
    case "string":
      return [rule.example]
  }
}

// Gamescope parses options in order and handles --help last here, so a
// refused option or value exits non-zero before the usage text.
function accepts(args: string[]): boolean {
  const run = Bun.spawnSync([gamescope, ...args, "--help"], { stdout: "pipe", stderr: "pipe" })
  return run.exitCode === 0 && run.stderr.toString().includes("usage: gamescope")
}
if (accepts(["--korri-no-such-option"])) throw new Error("gamescope accepted an unknown option")
if (accepts(["--scaler", "korri-no-such-scaler"])) throw new Error("gamescope accepted an invalid scaler")

const failures: string[] = []
for (const [key, rule] of Object.entries(settingsRules)) {
  const arity = table.get(key)
  const expected = rule.kind === "boolean" ? "no_argument" : "required_argument"
  if (arity !== expected) failures.push(`${key}: table has ${arity ?? "no entry"}, Korri expects ${expected}`)
  const values = samples(rule)
  for (const args of values.length === 0 ? [[`--${key}`]] : values.map(value => [`--${key}`, value])) {
    if (!accepts(args)) failures.push(`${key}: binary refused ${JSON.stringify(args)}`)
  }
}
if (failures.length > 0) throw new Error(`Gamescope option check failed:\n${failures.join("\n")}`)
console.log(`${Object.keys(settingsRules).length} typed settings match ${table.size} Gamescope options`)
