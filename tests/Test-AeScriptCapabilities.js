"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { analyzeCapabilities, toolName } = require("../tools/AeScriptCapabilities.js");
const { consolidateSource } = require("../tools/AeScriptSource.js");
let passed = 0;
function test(label, run) { run(); passed++; console.log("PASS " + label); }
const source = branches => ({ schema: "codex-ae-scripts/v1", branches });
const byName = (report, name) => report.branches.find(branch => branch.name === name);

test("Every source maps once, keeps inventory extras and explicitly reports missing inventory names", () => {
    const report = analyzeCapabilities(source({ "a.jsx": "1", "extra.jsx": "2" }), { inventoryNames: ["a.jsx", "missing.jsx"] });
    assert.deepEqual(report.coverage, { sourceBranches: 2, inventoryBranches: 2, mappedBranches: 2,
        missing: ["missing.jsx"], extras: ["extra.jsx"], complete: false });
    assert.equal(new Set(report.branches.map(branch => branch.capabilityId)).size, 2);
    assert.deepEqual(report.branches.map(branch => branch.call.args.branch), ["a.jsx", "extra.jsx"]);
});

test("Analyzer never executes JSX and syntax errors remain individually discoverable", () => {
    global.__capabilityAnalyzerMustNotRun = 0;
    try {
        const report = analyzeCapabilities(source({ "safe.jsx": "global.__capabilityAnalyzerMustNotRun++; throw new Error('must not run');",
            "broken.jsx": "(function broken( {" }));
        assert.equal(global.__capabilityAnalyzerMustNotRun, 0);
        assert.equal(byName(report, "safe.jsx").syntax.valid, true);
        assert.equal(byName(report, "broken.jsx").syntax.valid, false);
        assert.equal(report.summary.syntaxInvalid, 1);
        assert.equal(report.analysis.runtimeVerified, false);
        assert.ok(report.branches.every(branch => branch.runtimeVerified === false));
    } finally { delete global.__capabilityAnalyzerMustNotRun; }
});

test("Tool IDs are short, stable across source changes and collision resistant after slug normalization", () => {
    const names = ["A-B.jsx", "a_b.jsx", "a b.jsx", "A".repeat(240) + ".jsx"];
    const ids = names.map(toolName);
    assert.equal(new Set(ids).size, names.length);
    assert.ok(ids.every(id => /^[a-z0-9_]{1,64}$/.test(id)));
    assert.equal(analyzeCapabilities(source({ "A-B.jsx": "1" })).branches[0].capabilityId,
        analyzeCapabilities(source({ "A-B.jsx": "2" })).branches[0].capabilityId);
});

test("Comments, text strings and regex contents cannot fabricate direct risk calls", () => {
    const report = analyzeCapabilities(source({ "inspect-clean.jsx": `
/* app.project.save(); app.project.importFile(new ImportOptions()); alert('fake'); */
var text = "app.project.close(); layer.remove(); eval('fake');";
var pattern = /app\\.project\\.save\\(\\)|alert[\\"']/;
returnValue = app.version;
` }));
    const entry = report.branches[0];
    assert.deepEqual(entry.risks, []);
    assert.equal(entry.projectMutation, "not-detected");
});

test("API risks and bounded literal project requirements are extracted with line evidence", () => {
    const report = analyzeCapabilities(source({ "apply-example.jsx": `/* Apply title animation. */
var compName = "Scene 01";
var comp = findComp("Main \\u0043omp");
var layer = comp.layer("Title");
var path = new File("C:\\\\Media\\\\movie.mp4");
layer.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
layer.property("ADBE Opacity").setValueAtTime(0, 10);
layer.expression = "time*2";
app.project.save(); app.project.close(); layer.remove();
app.project.importFile(new ImportOptions()); app.project.renderQueue.render();
alert("Proceed?"); system.callSystem("helper.exe");
$.evalFile(new File("C:/workspace/jsx/dependency.jsx"));
`, "dependency.jsx": "0;" }));
    const entry = byName(report, "apply-example.jsx");
    assert.equal(entry.projectMutation, "detected");
    for (const risk of ["project-save", "project-close", "delete", "import-replace", "render-export", "modal-input", "external-process", "dynamic-script-loading", "expression-assignment"]) {
        assert.ok(entry.risks.includes(risk), risk);
    }
    assert.ok(entry.staticHints.comps.some(hint => hint.value === "Main Comp" && hint.line === 3));
    assert.ok(entry.staticHints.comps.some(hint => hint.value === "Scene 01"));
    assert.ok(entry.staticHints.layers.some(hint => hint.value === "Title"));
    assert.ok(entry.staticHints.files.some(hint => hint.value.includes("movie.mp4")));
    assert.ok(entry.staticHints.effects.some(hint => hint.value === "ADBE Gaussian Blur 2"));
    assert.ok(!entry.staticHints.effects.some(hint => hint.value === "ADBE Opacity"));
    assert.deepEqual(entry.dependencies, ["dependency.jsx"]);
    assert.deepEqual(entry.missingDependencies, []);
    assert.ok(entry.description.includes("Apply title animation"));
});

test("Known file close calls remain distinct from project close and unknown receiver close calls", () => {
    const report = analyzeCapabilities(source({ "file-close.jsx": "var output = new File('x'); output.close(); inspectionFile.close();",
        "project-close.jsx": "var p=app.project; p.close();", "unknown-close.jsx": "thing.close();" }));
    assert.deepEqual(byName(report, "file-close.jsx").risks, ["file-close"]);
    assert.deepEqual(byName(report, "project-close.jsx").risks, ["project-close"]);
    assert.deepEqual(byName(report, "unknown-close.jsx").risks, ["ambiguous-close"]);
});

test("String replace and frame inspection do not claim media import or queued rendering", () => {
    const report = analyzeCapabilities(source({ "strings.jsx": "var text='a'; text.replace(/a/,'b'); 'a'.replace('a','b');",
        "unknown-replace.jsx": "source.replace(candidate);", "capture.jsx": "comp.saveFrameToPng(0, file);" }));
    assert.deepEqual(byName(report, "strings.jsx").risks, []);
    assert.equal(byName(report, "strings.jsx").projectMutation, "not-detected");
    assert.deepEqual(byName(report, "unknown-replace.jsx").risks, ["ambiguous-media-or-string-replace"]);
    assert.equal(byName(report, "unknown-replace.jsx").projectMutation, "possible");
    assert.deepEqual(byName(report, "capture.jsx").risks, ["frame-export"]);
});

test("Missing static dependencies are visible and dynamic-only dependencies are not invented", () => {
    const report = analyzeCapabilities(source({ "deps.jsx": `$.evalFile("unknown.jsx"); $.evalFile(new File(dynamicPath)); var path="C:/work/jsx/absent.jsx";` }));
    assert.deepEqual(report.branches[0].dependencies, ["absent.jsx", "unknown.jsx"]);
    assert.deepEqual(report.branches[0].missingDependencies, ["absent.jsx", "unknown.jsx"]);
});

test("Exact and literal-only structural variants are distinguished without dropping branch names", () => {
    const report = analyzeCapabilities(source({ "first.jsx": "var x = 'a'; x = 10;", "copy.jsx": "var x = 'a'; x = 10;",
        "variant.jsx": "/* different targets */ var x = 'b'; x = 20;", "different.jsx": "var y = 'b'; y = 20;" }));
    assert.equal(report.summary.branches, 4);
    assert.equal(report.summary.uniqueExactSources, 3);
    assert.equal(report.summary.uniqueStructuralShapes, 2);
    assert.equal(report.duplicateGroups.exact.length, 1);
    assert.equal(report.duplicateGroups.structural.length, 1);
    assert.equal(byName(report, "first.jsx").duplicates.exactGroup, byName(report, "copy.jsx").duplicates.exactGroup);
    assert.equal(byName(report, "variant.jsx").duplicates.exactGroup, null);
    assert.equal(byName(report, "first.jsx").duplicates.structuralGroup, byName(report, "variant.jsx").duplicates.structuralGroup);
    assert.equal(byName(report, "different.jsx").duplicates.structuralGroup, null);
});

test("Hints and descriptions are bounded and shared-module input produces identical deterministic metadata", () => {
    const input = source({ "many-hints.jsx": "/* " + "description ".repeat(80) + " */\n" +
        Array.from({ length: 40 }, (_, index) => "comp.layer('Layer" + index + "');").join("\n") +
        "comp.layer('" + "x".repeat(600) + "');", "Codex Library.jsx": "var x = 1;" });
    const first = analyzeCapabilities(input);
    assert.deepEqual(analyzeCapabilities(input), first);
    assert.deepEqual(analyzeCapabilities(consolidateSource(input).source), first);
    const entry = byName(first, "many-hints.jsx");
    assert.equal(entry.staticHints.layers.length, 16);
    assert.equal(entry.staticHints.truncated, true);
    assert.ok(entry.description.length < 250);
    assert.ok(entry.searchTokens.length <= 96);
    assert.equal(byName(first, "Codex Library.jsx").internal, true);
});

test("All installed historical branches are mapped once, syntax-checked and retained without runtime execution", () => {
    const root = path.resolve(__dirname, "..");
    const input = JSON.parse(fs.readFileSync(path.join(root, "source/scripts.json"), "utf8"));
    const inventory = JSON.parse(fs.readFileSync(path.join(root, "source/script-inventory.json"), "utf8"));
    const report = analyzeCapabilities(input, { inventoryNames: inventory.names });
    assert.equal(report.coverage.complete, true);
    assert.deepEqual(report.coverage.missing, []);
    assert.equal(report.branches.length, Object.keys(input.branches).length);
    assert.equal(report.summary.syntaxInvalid, 0);
    assert.ok(report.branches.every(entry => entry.missingDependencies.length === 0), "all installed static dependencies are present");
    assert.equal(new Set(report.branches.map(entry => entry.capabilityId)).size, report.branches.length);
    for (const name of inventory.names) { assert.ok(byName(report, name), name); }
    assert.deepEqual(analyzeCapabilities(input, { inventoryNames: inventory.names }), report);
    console.log(JSON.stringify({ coverage: report.coverage, summary: report.summary }));
});

console.log(passed + "/" + passed + " capability analyzer tests passed");
