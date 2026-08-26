import fs from "node:fs";
import { config } from "../config.js";
import type { EvalCase } from "../types.js";

interface CasesFile {
  cases: EvalCase[];
}

export function loadAllCases(): EvalCase[] {
  const visible = JSON.parse(
    fs.readFileSync(config.visibleCasesPath, "utf8"),
  ) as CasesFile;
  const custom = JSON.parse(
    fs.readFileSync(config.customCasesPath, "utf8"),
  ) as CasesFile;
  return [...visible.cases, ...custom.cases];
}
