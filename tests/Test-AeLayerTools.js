/* Installed composition/layer tools, exercised only against a mocked AE host. */
"use strict";
const assert = require("node:assert/strict");
const path = require("node:path");
const vm = require("node:vm");
const { readFunctionsRuntime } = require("../tools/AeFunctionsSource.js");
const source = readFunctionsRuntime(path.resolve(__dirname, ".."));
const request = steps => ({ schema: "codex-ae-functions/v1", steps });
const call = (name, args = {}, label) => ({ function: name, args, ...(label ? { as: label } : {}) });
const clean = value => JSON.parse(JSON.stringify(value));

function host() {
    const state = { begin: 0, end: 0, writes: 0, precomposes: [], removed: [], cameraCenters: [], lightCenters: [], selectionWrites: 0 };
    let nextId = 1;
    class Property {
        constructor(name, value) { Object.assign(this, { name, matchName: name, value, numKeys: 0, canVaryOverTime: true }); }
        setValue(value) { if (state.throwWrite === this.matchName) { throw new Error("Mock host assignment failed: " + this.matchName); } this.value = value; state.writes++; }
    }
    class Group {
        constructor(name) { this.name = name; this.matchName = name; this.children = []; }
        property(name) { return typeof name === "number" ? this.children[name - 1] : this.children.find(item => item.name === name || item.matchName === name) || null; }
        add(name, value) { const child = value instanceof Group ? value : new Property(name, value); this.children.push(child); return child; }
    }
    class Layer extends Group {
        constructor(comp, name, kind = "av") {
            super(name); Object.assign(this, { id: nextId++, containingComp: comp, kind, enabled: true, locked: false, startTime: 0, inPoint: 0, outPoint: comp.duration, parent: null, threeDLayer: kind !== "av", _selected: false });
            if (kind === "av") { this.blendingMode = "NORMAL"; }
            const transforms = this.add("ADBE Transform Group", new Group("ADBE Transform Group"));
            transforms.add("ADBE Position", kind === "av" ? [0, 0] : [0, 0, -1000]); transforms.add("ADBE Anchor Point", [0, 0]); transforms.add("ADBE Scale", [100, 100]); transforms.add("ADBE Opacity", 100); transforms.add("ADBE Rotate Z", 0);
            if (kind === "camera") { const options = this.add("ADBE Camera Options Group", new Group("ADBE Camera Options Group")); options.add("ADBE Camera Zoom", 1000); }
            if (kind === "light") { const options = this.add("ADBE Light Options Group", new Group("ADBE Light Options Group")); options.add("ADBE Light Color", [1, 1, 1]); options.add("ADBE Light Intensity", 100); }
        }
        get index() { return this.containingComp.layerArray.indexOf(this) + 1; }
        get selected() { return this._selected; }
        set selected(value) { this._selected = value; state.selectionWrites++; }
        remove() { if (state.failRemove) { throw new Error("Mock layer removal failed"); } state.removed.push(this.id); this.containingComp.layerArray.splice(this.index - 1, 1); state.writes++; }
    }
    class CompItem {
        constructor(name) {
            Object.assign(this, { id: nextId++, name, width: 1920, height: 1080, pixelAspect: 1, duration: 10, frameRate: 30, time: 0, layerArray: [] });
            this.layers = {
                addNull: () => this.addLayer("Null"),
                addCamera: (name, center) => { state.cameraCenters.push(Array.from(center)); return this.addLayer(name, "camera"); },
                addLight: (name, center) => { state.lightCenters.push(Array.from(center)); return this.addLayer(name, "light"); },
                precompose: (indices, name, moveAttributes) => {
                    const originals = Array.from(indices, index => this.layer(index));
                    state.precomposes.push({ indices: Array.from(indices), name, moveAttributes });
                    const result = addComp(name);
                    for (const original of originals) { result.addLayer(original.name); }
                    this.layerArray = this.layerArray.filter(layer => !originals.includes(layer));
                    const nested = this.addLayer(name); nested.source = result;
                    return result;
                }
            };
        }
        get numLayers() { return this.layerArray.length; }
        layer(index) { return this.layerArray[index - 1]; }
        addLayer(name, kind) { const layer = new Layer(this, name, kind); this.layerArray.unshift(layer); state.writes++; return layer; }
        duplicate() { const result = addComp(this.name + " 2"); for (const layer of [...this.layerArray].reverse()) { result.addLayer(layer.name, layer.kind); } return result; }
        openInViewer() { project.activeItem = this; }
    }
    const project = { comps: [], activeItem: null, get numItems() { return this.comps.length; }, item(index) { return this.comps[index - 1]; } };
    function addComp(name) { const comp = new CompItem(name); project.comps.push(comp); state.writes++; return comp; }
    project.items = { addComp: name => addComp(name) };
    const comp = addComp("Main"), a = comp.addLayer("A"), b = comp.addLayer("B"), c = comp.addLayer("C"); project.activeItem = comp; state.writes = 0;
    const blends = ["NORMAL", "ADD", "MULTIPLY", "SCREEN", "OVERLAY", "SOFT_LIGHT", "HARD_LIGHT", "COLOR_DODGE", "COLOR_BURN", "DIFFERENCE", "EXCLUSION", "HUE", "SATURATION", "COLOR", "LUMINOSITY", "DARKEN", "LIGHTEN"];
    const sandbox = { app: { version: "mock", project, beginUndoGroup: () => { state.begin++; }, endUndoGroup: () => { state.end++; } }, CompItem,
        AutoOrientType: { NO_AUTO_ORIENT: "one-node", CAMERA_OR_POINT_OF_INTEREST: "two-node" }, LightType: { POINT: 0, SPOT: 1, PARALLEL: 2, AMBIENT: 3 },
        BlendingMode: Object.fromEntries(blends.map(value => [value, value])), $: { global: { __codexAeBundleV1: { names: [] } } } };
    vm.createContext(sandbox); vm.runInContext(source, sandbox, { filename: "assembled-functions-runtime.js", timeout: 3000 });
    return { api: sandbox.$.global.__codexAeFunctionsV1, sandbox, state, project, comp, a, b, c, addComp };
}
let passed = 0;
function test(name, body) { body(); passed++; process.stdout.write("ok " + passed + " - " + name + "\n"); }

test("seven installed tools expose exact fields, required arguments and ref kinds", () => {
    const { api } = host(), catalog = clean(api.list());
    for (const name of ["comp.duplicate", "comp.precompose", "layer.camera.create", "layer.light.create", "layer.remove", "layer.select", "layer.blendMode"]) {
        const descriptor = catalog.find(item => item.name === name); assert.ok(descriptor, name); assert.equal(descriptor.inputSchema.additionalProperties, false); assert.equal(descriptor.mutates, true);
        assert.deepEqual(Object.keys(descriptor.args), Object.keys(descriptor.inputSchema.properties));
    }
    assert.deepEqual(catalog.find(item => item.name === "comp.precompose").inputSchema.required, ["layers", "name"]);
    assert.equal(catalog.find(item => item.name === "comp.precompose").resultRef, "comp");
    assert.equal(catalog.find(item => item.name === "layer.camera.create").resultRef, "layer");
    assert.deepEqual(catalog.find(item => item.name === "layer.blendMode").inputSchema.required, ["layer", "mode"]);
    assert.equal(catalog.find(item => item.name === "layer.select").inputSchema.properties.layers.minItems, 0);
});
test("all structural arguments validate before the first creation or undo group", () => {
    const { api, state, project } = host(), before = project.numItems;
    const invalid = [
        call("layer.camera.create", { position: [1, 2, 3] }), call("layer.camera.create", { zoom: 0 }), call("layer.camera.create", { type: "invalid" }),
        call("layer.light.create", { color: [1, -1, 0] }), call("layer.light.create", { intensity: "100" }), call("layer.light.create", { type: "environment" }),
        call("comp.precompose", { name: "Nested", layers: [] }), call("comp.precompose", { name: "Nested", layers: [{ index: 1 }, { index: 2 }], moveAttributes: false }),
        call("layer.select", { layers: [{ index: 1, name: "C" }] }), call("layer.blendMode", { layer: { index: 1 }, mode: "toString" }), call("layer.remove", { layer: { index: 1 }, force: true })
    ];
    for (const last of invalid) { assert.throws(() => api.run(request([call("comp.duplicate", { name: "Never created" }), last]))); }
    assert.equal(project.numItems, before); assert.equal(state.writes, 0); assert.equal(state.begin, 0);
});
test("duplicated compositions preserve the source and support typed references", () => {
    const { api, comp, project, state } = host();
    const result = clean(api.run(request([call("comp.duplicate", { name: "Copy" }, "copy"), call("layer.camera.create", { comp: { ref: "copy" }, name: "Camera", zoom: 1500 }, "camera"), call("layer.update", { comp: { ref: "copy" }, layer: { ref: "camera" }, transform: { position: [10, 20, -1000] } })])));
    assert.equal(comp.numLayers, 3); assert.equal(project.numItems, 2); assert.equal(project.comps[1].numLayers, 4); assert.equal(result.results[0].value.name, "Copy"); assert.equal(result.results[2].value.compId, project.comps[1].id); assert.equal(state.begin, 1); assert.equal(state.end, 1);
});
test("precompose resolves exact layers and passes sorted unique native indices", () => {
    const { api, comp, a, c, state } = host();
    const result = clean(api.run(request([call("comp.precompose", { layers: [{ name: a.name }, { index: c.index }], name: "Nested" }, "nested"), call("comp.inspect", { comp: { ref: "nested" }, includeLayers: false })])));
    assert.deepEqual(state.precomposes, [{ indices: [1, 3], name: "Nested", moveAttributes: true }]); assert.equal(comp.numLayers, 2); assert.equal(result.results[1].value.numLayers, 2); assert.equal(result.results[0].value.id, result.results[1].value.id); assert.equal(state.begin, state.end);
});
test("precompose rejects missing, duplicate and locked selections before moving any layers", () => {
    for (const mode of ["missing", "duplicate", "locked"]) {
        const { api, comp, a, state } = host();
        let selections;
        if (mode === "missing") { selections = [{ index: 1 }, { index: 99 }]; }
        if (mode === "duplicate") { selections = [{ index: a.index }, { name: a.name }]; }
        if (mode === "locked") { a.locked = true; selections = [{ index: 1 }, { name: a.name }]; }
        assert.throws(() => api.run(request([call("comp.precompose", { layers: selections, name: "No changes" })])));
        assert.equal(comp.numLayers, 3); assert.equal(state.precomposes.length, 0); assert.equal(state.writes, 0); assert.equal(state.begin, state.end);
    }
});
test("single-layer precompose supports leaving attributes in the source", () => {
    const { api, state } = host(); api.run(request([call("comp.precompose", { layers: [{ index: 1 }], name: "Single", moveAttributes: false })])); assert.equal(state.precomposes[0].moveAttributes, false);
});
test("precompose array indices bind original layers while typed references bind newly created layers", () => {
    const { api, comp, c, state } = host();
    const result = clean(api.run(request([
        call("layer.null.create", { name: "Created" }, "created"),
        call("comp.precompose", { layers: [{ index: 1 }, { ref: "created" }], name: "Mixed" })
    ])));
    assert.deepEqual(state.precomposes[0].indices, [1, 2]);
    const nested = comp.layer(1).source;
    assert.deepEqual(nested.layerArray.map(layer => layer.name).sort(), ["C", "Created"]);
    assert.equal(comp.layerArray.some(layer => layer === c), false); assert.equal(result.count, 2);
});
test("missing static layer arrays fail preflight before earlier plan mutations", () => {
    for (const operation of ["layer.select", "comp.precompose"]) {
        const { api, comp, state } = host();
        const args = { layers: [{ index: 99 }], ...(operation === "comp.precompose" ? { name: "Never" } : {}) };
        assert.throws(() => api.run(request([call("layer.null.create", { name: "Never" }), call(operation, args)])), /does not exist/);
        assert.equal(comp.numLayers, 3); assert.equal(state.writes, 0); assert.equal(state.begin, 0);
    }
});
test("array selectors in a referenced composition resolve after its creation", () => {
    const { api, state, project } = host();
    api.run(request([call("comp.duplicate", { name: "Copy" }, "copy"), call("comp.precompose", { comp: { ref: "copy" }, layers: [{ index: 1 }], name: "Nested" })]));
    assert.deepEqual(state.precomposes[0].indices, [1]);
    assert.equal(project.comps.find(comp => comp.name === "Nested").layer(1).name, "C");
});
test("camera creation uses matchNames, explicit orientation and a 2D center", () => {
    const { api, comp, state } = host();
    api.run(request([call("layer.camera.create", { name: "One", position: [100, 200], type: "one-node", zoom: 2400 }), call("layer.camera.create", { name: "Two" })]));
    const one = comp.layerArray.find(layer => layer.name === "One"), two = comp.layerArray.find(layer => layer.name === "Two");
    assert.equal(one.autoOrient, "one-node"); assert.equal(two.autoOrient, "two-node"); assert.equal(one.property("ADBE Camera Options Group").property("ADBE Camera Zoom").value, 2400); assert.deepEqual(state.cameraCenters, [[100, 200], [960, 540]]);
});
test("camera option failure is reported and closes the undo group without replay", () => {
    const { api, state } = host(); state.throwWrite = "ADBE Camera Zoom";
    assert.throws(() => api.run(request([call("layer.camera.create", { zoom: 1500 })])), /Step 1\/1.*0 completed.*Mock host assignment failed/); assert.equal(state.cameraCenters.length, 1); assert.equal(state.begin, 1); assert.equal(state.end, 1);
});
test("missing host constants reject camera creation before creating a layer", () => {
    const { api, sandbox, comp, state } = host(); delete sandbox.AutoOrientType;
    assert.throws(() => api.run(request([call("layer.camera.create")])), /orientation constants/); assert.equal(comp.numLayers, 3); assert.equal(state.cameraCenters.length, 0); assert.equal(state.begin, state.end);
});
test("lights honor all four types, exact color paths and zero intensity", () => {
    const { api, comp, state } = host();
    api.run(request(["point", "spot", "parallel", "ambient"].map(type => call("layer.light.create", { name: type, type, color: [0.2, 0.4, 0.6], intensity: 0 }))));
    for (const [name, value] of [["point", 0], ["spot", 1], ["parallel", 2], ["ambient", 3]]) { const layer = comp.layerArray.find(item => item.name === name); assert.equal(layer.lightType, value); assert.deepEqual(clean(layer.property("ADBE Light Options Group").property("ADBE Light Color").value), [0.2, 0.4, 0.6]); assert.equal(layer.property("ADBE Light Options Group").property("ADBE Light Intensity").value, 0); }
    assert.equal(state.lightCenters.length, 4); assert.equal(state.begin, 1); assert.equal(state.end, 1);
});
test("remove acts once on the exact layer and rejects locked layers", () => {
    const { api, a, b, comp, state } = host(); a.locked = true;
    assert.throws(() => api.run(request([call("layer.remove", { layer: { name: "A" } })])), /locked/); assert.equal(state.removed.length, 0);
    const result = clean(api.run(request([call("layer.remove", { layer: { name: "B" } })]))); assert.equal(result.results[0].value.removed.id, b.id); assert.deepEqual(state.removed, [b.id]); assert.equal(comp.numLayers, 2); assert.equal(state.begin, state.end);
});
test("selection resolves its full set before changing existing selection", () => {
    const { api, a, b, c, state } = host(); a.selected = true; state.selectionWrites = 0;
    assert.throws(() => api.run(request([call("layer.select", { layers: [{ name: "B" }, { index: 99 }] })])), /does not exist/); assert.equal(a.selected, true); assert.equal(state.selectionWrites, 0);
    assert.throws(() => api.run(request([call("layer.select", { layers: [{ name: "B" }, { index: b.index }] })])), /more than once/); assert.equal(state.selectionWrites, 0);
    api.run(request([call("layer.select", { layers: [{ name: "B" }], replace: false })])); assert.equal(a.selected, true); assert.equal(b.selected, true);
    api.run(request([call("layer.select", { layers: [{ name: "C" }] })])); assert.equal(a.selected, false); assert.equal(b.selected, false); assert.equal(c.selected, true);
    api.run(request([call("layer.select", { layers: [] })])); assert.equal(c.selected, false); assert.equal(state.begin, state.end);
});
test("selection arrays retain original targets across insertion and reject removed targets", () => {
    const { api, c, comp, state } = host();
    api.run(request([call("layer.null.create", { name: "New" }, "created"), call("layer.select", { layers: [{ index: 1 }, { ref: "created" }] })]));
    assert.equal(c.selected, true); assert.equal(comp.layer(1).selected, true); assert.equal(comp.layer(2), c);
    state.selectionWrites = 0;
    assert.throws(() => api.run(request([call("layer.remove", { layer: { index: c.index } }), call("layer.select", { layers: [{ index: c.index }] })])), /no longer available/);
    assert.equal(state.selectionWrites, 0); assert.equal(state.removed.length, 1); assert.equal(state.begin, state.end);
});
test("ambiguous layer names cannot select, remove or precompose the wrong layer", () => {
    const { api, comp, state } = host(); comp.addLayer("A"); state.writes = 0;
    for (const step of [call("layer.select", { layers: [{ name: "A" }] }), call("layer.remove", { layer: { name: "A" } }), call("comp.precompose", { layers: [{ name: "A" }], name: "Nested" })]) { assert.throws(() => api.run(request([step])), /ambiguous/); }
    assert.equal(comp.numLayers, 4); assert.equal(state.writes, 0); assert.equal(state.selectionWrites, 0);
});
test("blend modes write AE blendingMode and never the ineffective blendMode field", () => {
    const { api, a, state } = host();
    const modes = { Normal: "NORMAL", Add: "ADD", Multiply: "MULTIPLY", Screen: "SCREEN", Overlay: "OVERLAY", SoftLight: "SOFT_LIGHT", HardLight: "HARD_LIGHT", ColorDodge: "COLOR_DODGE", ColorBurn: "COLOR_BURN", Difference: "DIFFERENCE", Exclusion: "EXCLUSION", Hue: "HUE", Saturation: "SATURATION", Color: "COLOR", Luminosity: "LUMINOSITY", Darken: "DARKEN", Lighten: "LIGHTEN" };
    for (const [mode, expected] of Object.entries(modes)) { api.run(request([call("layer.blendMode", { layer: { name: "A" }, mode })])); assert.equal(a.blendingMode, expected); assert.equal(Object.hasOwn(a, "blendMode"), false); }
    assert.equal(state.begin, state.end);
    a.locked = true; assert.throws(() => api.run(request([call("layer.blendMode", { layer: { name: "A" }, mode: "Normal" })])), /locked/);
});
test("camera/light layers cannot accept AV-only blending modes", () => {
    const { api, state } = host();
    let error;
    try { api.run(request([call("layer.camera.create", {}, "camera"), call("layer.blendMode", { layer: { ref: "camera" }, mode: "Add" })])); } catch (caught) { error = caught; }
    assert.ok(error); assert.equal(error.completedSteps, 1); assert.match(error.message, /does not support blending/); assert.equal(state.begin, 1); assert.equal(state.end, 1);
});
test("selection limits and typed reference mismatches fail during structural validation", () => {
    const { api, state } = host();
    assert.throws(() => api.validate(request([call("layer.select", { layers: Array.from({ length: 1001 }, () => ({ index: 1 })) })])), /0 to 1000/);
    assert.throws(() => api.validate(request([call("comp.duplicate", {}, "copy"), call("layer.select", { layers: [{ ref: "copy" }] })])), /earlier layer/);
    assert.equal(state.begin, 0);
});
process.stdout.write(passed + " composition/layer-tool tests passed.\n");
