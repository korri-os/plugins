// Public launch.prepare callback, from the exact installed source.
import { resolve } from "node:path"
const [packagePath, input] = process.argv.slice(2)
const plugin = await import(resolve(packagePath, "plugin.ts"))
process.stdout.write(JSON.stringify(plugin.handlers["launch.prepare"](JSON.parse(input))))
