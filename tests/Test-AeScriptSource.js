"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { expandSource, consolidateSource } = require("../tools/AeScriptSource.js");
const hash = text => crypto.createHash("sha256").update(text, "utf8").digest("hex");
const root = path.resolve(__dirname, "..");
const source = JSON.parse(fs.readFileSync(path.join(root, "source/scripts.json"), "utf8"));
const inventory = JSON.parse(fs.readFileSync(path.join(root, "source/script-inventory.json"), "utf8"));
const original = expandSource(source);
const result = consolidateSource(original);
assert.deepEqual(expandSource(result.source), original);
assert.equal(Object.keys(original.branches).length, inventory.names.length, "all inventoried historical branch names remain present");
for (const name of inventory.names) { assert.equal(typeof original.branches[name], "string", "original branch missing: " + name); }
assert.ok(result.stats.moduleBytes < result.stats.sourceBytes, "shared literal storage must actually reduce source bytes");
assert.ok(Object.values(result.source.branches).some(recipe => recipe.parts.some(Array.isArray)), "related scripts reuse source slices");
assert.deepEqual(consolidateSource(original), result, "consolidation must be deterministic");
for (const module of Object.values(result.source.modules)) { assert.doesNotThrow(() => encodeURIComponent(module)); }
console.log("PASS all " + inventory.names.length + " historical scripts reconstruct exactly with deterministic shared source storage");

const common = "function shared(value) { return value + 'same reusable source'; }\r\n".repeat(4);
const examples = { schema: "codex-ae-scripts/v1", branches: {
    "largest.jsx": "/* prefix */" + common + "/* suffix */\r\n",
    "different.jsx": "var different = true;\n" + common + "var tail = 2;",
    "identical.jsx": "/* prefix */" + common + "/* suffix */\r\n",
    "unicode.jsx": "/* tiếng Việt 🎬 中文 */\r\nvar x = 'a\\nb';\r\n",
    "empty.jsx": "",
    "surrogate.jsx": "\ud83d\ude00\ud800\udfff"
} };
const exampleResult = consolidateSource(examples);
assert.deepEqual(expandSource(exampleResult.source), expandSource(examples));
assert.deepEqual(exampleResult.source.branches["largest.jsx"].parts, exampleResult.source.branches["identical.jsx"].parts);
assert.notDeepEqual(exampleResult.source.branches["different.jsx"].sha256, exampleResult.source.branches["largest.jsx"].sha256);
console.log("PASS exact aliases share references while differing literals, Unicode, CRLF and surrogate code units survive");

const splitUnicode = { schema: "codex-ae-scripts/v2", modules: { m00001: "A\ud83d\ude00Z" }, branches: {
    "split.jsx": { parts: [["m00001", 0, 2], ["m00001", 2, 2]], sha256: hash("A\ud83d\ude00Z") }
} };
assert.equal(expandSource(splitUnicode).branches["split.jsx"], "A😀Z");
console.log("PASS recipes may split surrogate pairs without decoding or changing the joined text");

const emojiCommon = "x".repeat(113) + "🎬" + "y".repeat(113) + "😀" + "z".repeat(113);
const emojiEdges = { schema: "codex-ae-scripts/v1", branches: {
    "baseline.jsx": "long-prefix-" + emojiCommon + "-long-suffix",
    "pair-end.jsx": emojiCommon.slice(0, 115) + "different-tail",
    "pair-start.jsx": "different-prefix" + emojiCommon.slice(113),
    "related.jsx": "another-prefix-" + emojiCommon + "another-tail",
    "related-copy.jsx": "another-prefix-" + emojiCommon + "another-tail"
} };
const emojiResult = consolidateSource(emojiEdges);
assert.deepEqual(expandSource(emojiResult.source), expandSource(emojiEdges));
for (const module of Object.values(emojiResult.source.modules)) { assert.doesNotThrow(() => encodeURIComponent(module)); }
assert.deepEqual(emojiResult.source.branches["related.jsx"].parts, emojiResult.source.branches["related-copy.jsx"].parts);
console.log("PASS shared module boundaries preserve complete surrogate pairs for independent payload encoding");

const invalids = [
    { schema: "unsupported", branches: {} },
    { schema: "codex-ae-scripts/v2", modules: [], branches: {} },
    { schema: "codex-ae-scripts/v2", modules: { bad: "text" }, branches: {} },
    { schema: "codex-ae-scripts/v1", branches: { "../bad.jsx": "text" } }
];
for (const invalid of invalids) { assert.throws(() => expandSource(invalid)); }
const valid = { schema: "codex-ae-scripts/v2", modules: { m00001: "abcdef" }, branches: {
    "valid.jsx": { parts: ["m00001"], sha256: hash("abcdef") }
} };
for (const part of ["m99999", ["m00001", -1, 1], ["m00001", 0, -1], ["m00001", 1, 6],
    ["m00001", 0.5, 2], ["m00001", 0, 0], ["m00001", 0], ["valid.jsx", 0, 1], {}, null]) {
    const invalid = structuredClone(valid);
    invalid.branches["valid.jsx"].parts = [part];
    assert.throws(() => expandSource(invalid), /module|slice/);
}
for (const change of ["hash", "module", "order"]) {
    const invalid = structuredClone(valid);
    if (change === "hash") { invalid.branches["valid.jsx"].sha256 = "0".repeat(64); }
    if (change === "module") { invalid.modules.m00001 = "abcdeg"; }
    if (change === "order") { invalid.branches["valid.jsx"].parts = [["m00001", 3, 3], ["m00001", 0, 3]]; }
    assert.throws(() => expandSource(invalid), /SHA-256/);
}
console.log("PASS missing modules, recursive references, invalid slice bounds, changed source and recipe hashes fail closed");
console.log(JSON.stringify(result.stats));
