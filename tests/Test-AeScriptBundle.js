"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const { build, verify, expandSource, checkInventory } = require("../tools/Build-AeScriptBundle.js");
const { readFunctionsRuntime } = require("../tools/AeFunctionsSource.js");
const root = path.resolve(__dirname, "..");
const fixture = path.join(root, ".ae-codex/tests-bundle", String(Date.now()));
fs.mkdirSync(path.join(fixture, "source"), { recursive: true });
for (const name of ["bridge.js", "bundle-runtime.js", "functions-runtime.js", "functions-layer-tools.js", "functions-project-tools.js", "functions-inspection-tools.js", "script-inventory.json", "scripts.json"]) {
    fs.copyFileSync(path.join(root, "source", name), path.join(fixture, "source", name));
}
const source = expandSource(JSON.parse(fs.readFileSync(path.join(fixture, "source/scripts.json"), "utf8")));
const literalTokens = '/* preserve replacement tokens: $& $` $\' */\n';
const fragmentPath = path.join(fixture, "source/functions-project-tools.js");
fs.appendFileSync(fragmentPath, literalTokens);
assert.ok(readFunctionsRuntime(fixture).includes(literalTokens), "module assembly must preserve literal replacement tokens");
const result = build(fixture);
const output = fs.readFileSync(result.file, "utf8");
assert.equal(verify(output, source).branches, Object.keys(source.branches).length);
assert.equal(build(fixture).sha256, result.sha256, "repeated builds must be deterministic");
console.log("PASS all branches round-trip and builds are deterministic");

const missing = structuredClone(source);
delete missing.branches["hello.jsx"];
assert.throws(() => build(fixture, { source: missing }), /Missing original branch/);
assert.throws(() => checkInventory(fixture, missing), /Missing original branch/);
assert.equal(fs.readFileSync(result.file, "utf8"), output, "failed builds must preserve the last good JSX");
console.log("PASS omission of an original branch fails without replacing the bundle");

const invalid = structuredClone(source);
invalid.branches["hello.jsx"] = "(function broken( {";
assert.throws(() => build(fixture, { source: invalid }), /syntax error.*hello/);
console.log("PASS syntax errors identify the affected branch before publication");

const dependency = structuredClone(source);
dependency.branches["hello.jsx"] = "$.evalFile(new File('C:/Users/nguye/AE_Codex/jsx/missing-dependency.jsx'));";
assert.throws(() => build(fixture, { source: dependency }), /Missing dependency/);
console.log("PASS missing static dependencies prevent publication");

const ambiguous = structuredClone(source);
ambiguous.branches["HELLO.jsx"] = ambiguous.branches["hello.jsx"];
assert.throws(() => build(fixture, { source: ambiguous }), /Case-insensitive duplicate/);
console.log("PASS Windows branch names cannot differ only by case");

const unicode = structuredClone(source);
unicode.branches["unicode-test.jsx"] = "/* tiếng Việt </script> */ (function () { return 'Nhánh mới 🎬'; }());";
const unicodeResult = build(fixture, { source: unicode });
const unicodeOutput = fs.readFileSync(unicodeResult.file, "utf8");
assert.equal(verify(unicodeOutput, unicode).branches, result.branches + 1);
assert.throws(() => verify(unicodeOutput.slice(0, -1)), /header mismatch/);
console.log("PASS new branches preserve Unicode and embedded comment terminators; truncation is rejected");
// Maintenance must publish the index AFTER extending the inventory; otherwise
// its inventory hash is stale as soon as --update finishes.
fs.mkdirSync(path.join(fixture, "tools"), { recursive: true });
for (const name of ["Build-AeScriptBundle.js", "AeScriptSource.js", "AeScriptCapabilities.js", "AeCapabilities.js", "AeFunctionsSource.js"]) {
    fs.copyFileSync(path.join(root, "tools", name), path.join(fixture, "tools", name));
}
build(fixture);
const staged = path.join(fixture, "jsx/capability-update-test.jsx");
fs.writeFileSync(staged, "(function () { return 42; }());\n");
execFileSync(process.execPath, [path.join(fixture, "tools/Build-AeScriptBundle.js"), "--update", staged], { cwd: fixture });
const fixtureApi = require("../tools/AeCapabilities.js").createCapabilitiesApi(fixture);
assert.equal(fixtureApi.inspectCapability({ id: "capability-update-test.jsx", includeSource: true }).entry.name, "capability-update-test.jsx");
assert.equal(fixtureApi.capabilityStatus().coverage.complete, true);
assert.equal(fs.existsSync(staged), false, "maintenance consumes its own staged JSX after indexing");
execFileSync(process.execPath, [path.join(fixture, "tools/Build-AeScriptBundle.js"), "--verify"], { cwd: fixture });
console.log("PASS maintenance updates inventory before indexing and verifies the new callable branch");
console.log("7/7 bundle build tests passed");
