/* Exhaustive installed-branch dispatch contract, with no AE or branch execution. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const packed = JSON.parse(fs.readFileSync(path.join(root, "source/scripts.json"), "utf8"));
const inventory = JSON.parse(fs.readFileSync(path.join(root, "source/script-inventory.json"), "utf8"));
const names = Object.keys(packed.branches).sort();
const source = require("../tools/AeFunctionsSource.js").readFunctionsRuntime(root);
const dispatched = [], access = { undoBegin: 0, undoEnd: 0, source: 0, file: 0, evalFile: 0, project: 0 };
function prohibited(name) { return function () { access[name]++; throw new Error("This dispatch test must not access " + name); }; }
const app = { version: "mock", beginUndoGroup: () => { access.undoBegin++; }, endUndoGroup: () => { access.undoEnd++; } };
Object.defineProperty(app, "project", { get: prohibited("project") });
const bundle = {
    names,
    has: name => names.includes(name),
    source: prohibited("source"),
    prepare: prohibited("source"),
    run: name => {
        assert.ok(names.includes(name), "The registry must dispatch only an installed branch");
        dispatched.push(name);
        return "mock-dispatched:" + name;
    }
};
const sandbox = { app, File: prohibited("file"), Folder: prohibited("file"), $: { global: { __codexAeBundleV1: bundle }, evalFile: prohibited("evalFile") } };
vm.createContext(sandbox);
vm.runInContext(source, sandbox, { filename: "functions-runtime.js", timeout: 3000 });
const api = sandbox.$.global.__codexAeFunctionsV1;
const request = steps => ({ schema: "codex-ae-functions/v1", steps });
const call = (branch, extra = {}) => ({ function: "script.run", args: { branch, ...extra } });

assert.ok(names.length > 800, "The test must cover the complete historical registry");
assert.equal(new Set(names).size, names.length);
for (const name of inventory.names) { assert.ok(names.includes(name), "Original inventory branch is missing: " + name); }

const legacy = api.list(true).filter(entry => entry.legacy);
assert.equal(legacy.length, names.length, "Every source branch must appear in the installed registry");
assert.deepEqual(Array.from(legacy, entry => entry.branch).sort(), names);
for (const descriptor of legacy) {
    assert.equal(descriptor.name, "script.run");
    assert.equal(descriptor.inputSchema.additionalProperties, false);
    assert.deepEqual(Array.from(descriptor.inputSchema.required), ["branch"]);
    assert.deepEqual(Array.from(descriptor.inputSchema.properties.branch.enum), [descriptor.branch]);
}

/* The actual runtime accepts at most 100 steps, so route the complete list in pages. */
const maximumBatch = 100;
for (let offset = 0; offset < names.length; offset += maximumBatch) {
    const page = names.slice(offset, offset + maximumBatch);
    const result = api.run(JSON.stringify(request(page.map(name => call(name)))));
    assert.equal(result.count, page.length);
    assert.equal(result.results.length, page.length);
    for (let i = 0; i < page.length; i++) {
        assert.equal(result.results[i].function, "script.run");
        assert.equal(result.results[i].value.branch, page[i]);
        assert.equal(result.results[i].value.result, "mock-dispatched:" + page[i]);
    }
}
assert.deepEqual(dispatched, names, "Every source branch must dispatch exactly once and in order");
assert.equal(new Set(dispatched).size, names.length, "No branch may be silently replayed");
assert.equal(access.undoBegin, Math.ceil(names.length / maximumBatch));
assert.equal(access.undoEnd, access.undoBegin);

const dispatchCount = dispatched.length, undoCount = access.undoBegin;
const invalidRequests = [
    request([call("not-an-installed-branch.jsx")]),
    request([call("../hello.jsx")]),
    request([call("hello.jsx/../../evil.jsx")]),
    request([call("hello.jsx\n")]),
    request([call("hello.jsx;alert(1)")]),
    request([call("hello")]),
    request([call(42)]),
    request([call(names[0], { code: "app.project.close()" })]),
    request([call(names[0], { args: { arbitrary: true } })]),
    request([{ function: "script.run", args: {} }]),
    request([{ function: "unregistered.function", args: {} }]),
    request([call(names[0]), call("missing-late-step.jsx")])
];
for (const invalid of invalidRequests) { assert.throws(() => api.run(JSON.stringify(invalid)), undefined, JSON.stringify(invalid)); }
for (const text of [
    '{"schema":"codex-ae-functions/v1","steps":[{"function":"script.run","args":{"branch":"hello.jsx","branch":"other.jsx"}}]}',
    '{"schema":"codex-ae-functions/v1","steps":[{"function":"script.run","args":{"branch":"hello.jsx","__proto__":{"x":1}}}]}',
    '({schema:"codex-ae-functions/v1",steps:[]})'
]) { assert.throws(() => api.run(text)); }
assert.equal(dispatched.length, dispatchCount, "Rejected requests must not dispatch even an earlier valid step");
assert.equal(access.undoBegin, undoCount, "Invalid plans must fail before opening an undo group");
assert.equal(access.undoEnd, access.undoBegin);
for (const name of ["source", "file", "evalFile", "project"]) { assert.equal(access[name], 0, "Dispatch-only testing must not access " + name); }

process.stdout.write(JSON.stringify({
    state: "success",
    installedBranches: names.length,
    originalInventoryBranches: inventory.names.length,
    registryCoverage: legacy.length,
    mockDispatchedExactlyOnce: dispatched.length,
    rejectedRequests: invalidRequests.length + 3,
    realBranchExecution: false,
    aeProjectAccess: false,
    jsxFileWrites: false,
    limitation: "Verifies routing and strict arguments; does not prove historical project, media, plugin or render prerequisites."
}, null, 2) + "\n");
