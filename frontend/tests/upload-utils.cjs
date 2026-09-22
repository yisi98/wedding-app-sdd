const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const { readFileSync } = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const ts = require("typescript");
const sourcePath = path.resolve(__dirname, "../src/lib/upload.ts");
const compiled = ts.transpileModule(readFileSync(sourcePath, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const mod = new Module(sourcePath, module);
mod.paths = module.paths;
mod._compile(compiled, sourcePath);
const { hashFile, uploadMimeType } = mod.exports;

(async () => {
  for (const size of [0, 55, 64, 1024 * 1024 + 65, 3 * 1024 * 1024]) {
    const bytes = Buffer.alloc(size, 123);
    const blob = new Blob([bytes]);
    let reads = 0;
    const file = {
      size,
      arrayBuffer() { throw new Error("Must not read the entire file"); },
      slice(start, end) {
        assert.ok(end - start <= 1024 * 1024);
        reads++;
        return blob.slice(start, end);
      },
    };
    const progress = [];
    assert.equal(await hashFile(file, (n) => progress.push(n)), createHash("sha256").update(bytes).digest("hex"));
    assert.equal(reads, Math.ceil(size / (1024 * 1024)));
    if (size) assert.equal(progress.at(-1), 100);
  }
  assert.equal(uploadMimeType({ name: "IMG_123.MOV", type: "" }), "video/quicktime");
  assert.equal(uploadMimeType({ name: "clip.mp4", type: "application/octet-stream" }), "video/mp4");
  assert.equal(uploadMimeType({ name: "clip.m4v", type: "video/x-m4v" }), "video/mp4");
  assert.equal(uploadMimeType({ name: "clip.mp4", type: "text/plain" }), "text/plain");
  assert.equal(uploadMimeType({ name: "unknown", type: "" }), "application/octet-stream");
  console.log("PASS: chunked SHA-256 matches Node, reads at most 1 MiB, and handles missing video types");
})().catch((error) => { console.error(error); process.exitCode = 1; });
