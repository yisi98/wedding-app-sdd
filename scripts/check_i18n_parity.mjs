// EN/ZH/RU parity audit (T085 / SC-004).
// Checks that every frontend locale key exists in all three languages, and that every
// backend API message has en/zh/ru. Exits non-zero on any gap.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const LANGS = ["en", "zh", "ru"];
let failures = 0;

// --- Frontend locales ---
const localeDir = path.join(root, "frontend/src/locales");
const flat = (obj, prefix = "") =>
  Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === "object" ? flat(v, `${prefix}${k}.`) : [`${prefix}${k}`]
  );
const localeKeys = LANGS.map((l) =>
  new Set(flat(JSON.parse(fs.readFileSync(path.join(localeDir, `${l}.json`), "utf8"))))
);
const [en, zh, ru] = localeKeys;
console.log(`frontend locale keys: en=${en.size} zh=${zh.size} ru=${ru.size}`);
for (const [name, set] of [["zh", zh], ["ru", ru]]) {
  const missing = [...en].filter((k) => !set.has(k));
  const extra = [...set].filter((k) => !en.has(k));
  if (missing.length || extra.length) {
    failures++;
    console.log(`  ${name}: missing=${JSON.stringify(missing)} extra=${JSON.stringify(extra)}`);
  }
}

// --- Backend API messages ---
const i18nSrc = fs.readFileSync(path.join(root, "backend/src/i18n/__init__.py"), "utf8");
const keys = [...i18nSrc.matchAll(/^\s{4}"([a-z_]+)":\s*\{/gm)].map((m) => m[1]);
let backendGaps = 0;
for (const key of keys) {
  for (const lang of LANGS) {
    const re = new RegExp(`"${key}":[\\s\\S]*?"${lang}":`, "m");
    if (!re.test(i18nSrc)) {
      backendGaps++;
      console.log(`  backend message "${key}" missing ${lang}`);
    }
  }
}
console.log(`backend messages: ${keys.length} keys x ${LANGS.length} langs, gaps=${backendGaps}`);
if (backendGaps) failures++;

console.log(failures === 0 ? "\nPARITY OK ✓" : `\nPARITY FAILURES: ${failures}`);
process.exit(failures === 0 ? 0 : 1);
