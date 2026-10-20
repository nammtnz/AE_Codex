/* Reusable function registry tests; no real AE instance or project is touched. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = require("../tools/AeFunctionsSource.js").readFunctionsRuntime(path.resolve(__dirname, ".."));

function host() {
    const state = { begin: 0, end: 0, writes: 0, branches: [] };
    let nextId = 1;
    class Property {
        constructor(name, value) { this.name = name; this.matchName = name; this.value = value; this.canVaryOverTime = true; this.canSetExpression = true; this.expression = ""; this.expressionEnabled = false; this.expressionError = ""; this.keys = []; }
        get numKeys() { return this.keys.length; }
        setValue(value) { this.value = value; state.writes++; }
        setValueAtTime(time, value) { const found = this.keys.find(key => key.time === time); if (found) { found.value = value; } else { this.keys.push({ time, value }); this.keys.sort((a, b) => a.time - b.time); } this.value = value; state.writes++; }
        keyTime(index) { return this.keys[index - 1].time; }
        keyValue(index) { return this.keys[index - 1].value; }
        nearestKeyIndex(time) { return this.keys.findIndex(key => key.time === time) + 1; }
        setInterpolationTypeAtKey(index, input, output) { this.keys[index - 1].interpolation = [input, output]; }
        setTemporalEaseAtKey(index, incoming, outgoing) { this.keys[index - 1].ease = [incoming, outgoing]; }
    }
    class Group {
        constructor(name) { this.name = name; this.matchName = name; this.children = []; }
        get numProperties() { return this.children.length; }
        property(name) { return typeof name === "number" ? this.children[name - 1] : (this.children.find(value => value.matchName === name || value.name === name) || null); }
        add(name, value) { const item = value instanceof Group || value instanceof Property ? value : new Property(name, value); this.children.push(item); item.propertyIndex = this.children.length; return item; }
        canAddProperty(name) { return name === "ADBE Gaussian Blur 2" || name.indexOf("ADBE Vector") === 0; }
        addProperty(name) {
            if (!this.canAddProperty(name)) { throw new Error("Plugin unavailable"); }
            const item = this.add(name, new Group(name));
            if (name === "ADBE Gaussian Blur 2") { item.add("ADBE Gaussian Blur 2-0001", 0); }
            else if (name === "ADBE Vector Group") { item.add("ADBE Vectors Group", new Group("ADBE Vectors Group")); }
            else if (name === "ADBE Vector Shape - Rect") { item.add("ADBE Vector Rect Size", [100, 100]); item.add("ADBE Vector Rect Position", [0, 0]); item.add("ADBE Vector Rect Roundness", 0); }
            else if (name === "ADBE Vector Shape - Ellipse") { item.add("ADBE Vector Ellipse Size", [100, 100]); item.add("ADBE Vector Ellipse Position", [0, 0]); }
            else if (name === "ADBE Vector Shape - Group") { item.add("ADBE Vector Shape", null); }
            else if (name === "ADBE Vector Shape - Star") { for (const prop of ["Type", "Points", "Outer Radius", "Inner Radius", "Rotation"]) { item.add("ADBE Vector Star " + prop, 0); } item.add("ADBE Vector Star Position", [0, 0]); }
            else if (name === "ADBE Vector Graphic - Fill") { item.add("ADBE Vector Fill Color", [1, 1, 1]); }
            else if (name === "ADBE Vector Graphic - Stroke") { item.add("ADBE Vector Stroke Color", [1, 1, 1]); item.add("ADBE Vector Stroke Width", 2); }
            state.writes++; return item;
        }
    }
    class Layer extends Group {
        constructor(comp, type, content) {
            super(type); this.containingComp = comp; this.id = nextId++; this.enabled = true; this.locked = false; this.startTime = 0; this.inPoint = 0; this.outPoint = comp.duration; this.parent = null; this.threeDLayer = false;
            const transform = this.add("ADBE Transform Group", new Group("ADBE Transform Group"));
            for (const [name, value] of Object.entries({ "ADBE Position": [0, 0], "ADBE Anchor Point": [0, 0], "ADBE Scale": [100, 100], "ADBE Rotate Z": 0, "ADBE Rotate X": 0, "ADBE Rotate Y": 0, "ADBE Opacity": 100 })) { transform.add(name, value); }
            this.add("ADBE Effect Parade", new Group("ADBE Effect Parade"));
            if (type === "Text") { const text = this.add("ADBE Text Properties", new Group("ADBE Text Properties")); text.add("ADBE Text Document", { text: content, font: "ArialMT", fontSize: 24 }); }
            if (type === "Shape") { this.add("ADBE Root Vectors Group", new Group("ADBE Root Vectors Group")); }
        }
        get index() { return this.containingComp.layerArray.indexOf(this) + 1; }
        duplicate() { const copy = this.containingComp.addLayer("Null"); copy.name = this.name; return copy; }
        setParentWithJump(parent) { this.parent = parent; }
    }
    class CompItem {
        constructor(name, width = 1920, height = 1080, pixelAspect = 1, duration = 10, frameRate = 30) {
            this.id = nextId++; Object.assign(this, { name, width, height, pixelAspect, duration, frameRate, time: 0, layerArray: [] });
            this.layers = { addText: text => this.addLayer("Text", text), addNull: () => this.addLayer("Null"), addSolid: (color, name) => { const layer = this.addLayer("Solid"); layer.name = name; return layer; }, addShape: () => this.addLayer("Shape") };
        }
        get numLayers() { return this.layerArray.length; }
        layer(index) { return this.layerArray[index - 1]; }
        addLayer(type, content) { const layer = new Layer(this, type, content); this.layerArray.unshift(layer); state.writes++; return layer; }
        openInViewer() { project.activeItem = this; }
    }
    const project = { itemArray: [], activeItem: null, get numItems() { return this.itemArray.length; }, item(index) { return this.itemArray[index - 1]; }, items: { addComp: (...args) => { const comp = new CompItem(...args); project.itemArray.push(comp); state.writes++; return comp; } } };
    const comp = project.items.addComp("Main"), layer = comp.addLayer("Null"); layer.name = "Subject"; project.activeItem = comp; state.writes = 0;
    const sandbox = { app: { version: "26.5", project, beginUndoGroup: () => { state.begin++; }, endUndoGroup: () => { state.end++; } }, CompItem, Shape: class Shape {}, KeyframeEase: class KeyframeEase { constructor(speed, influence) { this.speed = speed; this.influence = influence; } }, ParagraphJustification: { LEFT_JUSTIFY: 1, CENTER_JUSTIFY: 2, RIGHT_JUSTIFY: 3 }, KeyframeInterpolationType: { LINEAR: 1, BEZIER: 2, HOLD: 3 }, $: { global: { __codexAeBundleV1: { names: ["hello.jsx", "preserved.jsx"], run: branch => { state.branches.push(branch); return "legacy result"; } } } } };
    vm.createContext(sandbox); vm.runInContext(source, sandbox);
    return { api: sandbox.$.global.__codexAeFunctionsV1, sandbox, state, project, comp, layer, Property, Group };
}
function request(steps) { return { schema: "codex-ae-functions/v1", steps }; }
function call(name, args = {}, label) { const step = { function: name, args }; if (label) { step.as = label; } return step; }
function clean(value) { return JSON.parse(JSON.stringify(value)); }
let passed = 0;
function test(name, body) { body(); passed++; process.stdout.write("ok " + passed + " - " + name + "\n"); }

test("strict parser roundtrips strings, Unicode, numbers and nested data without eval", () => {
    const { api } = host(), value = { message: "Tiếng Việt\n\t\"\\\u2028", values: [true, false, null, 1.25, -3e-5], nested: { a: [] } };
    assert.deepEqual(clean(api.parse(api.stringify(value))), value);
    assert.equal(api.version, "1.0.0");
});
test("strict parser rejects executable syntax, duplicate and prototype keys", () => {
    const { api } = host();
    for (const input of ['({})', '{"a":1,"a":2}', '{"__proto__":{}}', '{"constructor":1}', '{"nested":{"prototype":1}}', '{"a":NaN}', '[1,]', '{"a":1,}', '[01]', '1e999', 'true false', '"bad\u0001"', '"\\x41"']) { assert.throws(() => api.parse(input), undefined, input); }
});
test("parser and serializer enforce depth, complexity, size and finite data", () => {
    const { api } = host(), circular = {}; circular.circular = circular;
    assert.throws(() => api.parse("[".repeat(34) + "0" + "]".repeat(34)), /complexity/);
    assert.throws(() => api.parse(" ".repeat(1048577)), /at most/);
    assert.throws(() => api.parse("[" + Array(50002).fill("0").join(",") + "]"), /complexity/);
    for (const value of [Infinity, NaN, undefined, () => {}, circular]) { assert.throws(() => api.stringify(value)); }
});
test("catalog exposes exact builtin schemas and every legacy branch without loading source", () => {
    const { api, sandbox, state } = host(); sandbox.$.global.__codexAeBundleV1.source = () => { throw new Error("must not load source"); };
    const all = clean(api.list(true)), compact = clean(api.list());
    assert.ok(compact.length >= 20); assert.equal(all.length, compact.length + 3);
    assert.equal(compact.some(item => item.name === "script.run" || item.legacy), false);
    assert.equal(all.filter(item => item.legacy).length, 2); assert.equal(state.branches.length, 0);
    for (const descriptor of compact) { assert.equal(descriptor.inputSchema.additionalProperties, false); assert.deepEqual(Object.keys(descriptor.inputSchema.properties), Object.keys(descriptor.args)); }
    assert.deepEqual(compact.find(item => item.name === "property.set").inputSchema.required, ["layer", "path", "value"]);
    assert.deepEqual(compact.find(item => item.name === "comp.seek").inputSchema.required, ["time"]);
    assert.equal(compact.find(item => item.name === "comp.rebuildMedia").inputSchema.properties.resumeCompId.type, "integer");
    assert.equal(compact.find(item => item.name === "comp.rebuildMedia").inputSchema.properties.resumeCompId.minimum, 1);
});
test("read-only tools inspect active project without an undo group", () => {
    const { api, state, comp } = host();
    const result = clean(api.run(request([call("system.info"), call("project.inspect"), call("comp.inspect"), call("layer.inspect", { layer: { index: 1 }, properties: [["ADBE Transform Group", "ADBE Opacity"]] })])));
    assert.equal(result.count, 4); assert.equal(result.results[0].value.host, "After Effects"); assert.equal(result.results[2].value.id, comp.id); assert.equal(result.results[3].value.properties[0].value, 100); assert.equal(state.begin, 0); assert.equal(state.writes, 0);
});

test("composition and layer inspection expose native background, flags, types and blendingMode", () => {
    const { api, state, comp, layer } = host();
    comp.bgColor = [0.1, 0.2, 0.3];
    Object.assign(layer, { matchName: "ADBE Text Layer", solo: true, shy: false, adjustmentLayer: false, nullLayer: false, guideLayer: true, hasAudio: false, hasVideo: true, blendingMode: { toString: () => "BlendingMode.SCREEN" } });
    const result = clean(api.run(request([call("comp.inspect")]))).results[0].value;
    assert.deepEqual(result.bgColor, [0.1, 0.2, 0.3]);
    assert.equal(result.layers[0].type, "text"); assert.equal(result.layers[0].blendingMode, "BlendingMode.SCREEN");
    for (const flag of ["solo", "shy", "adjustmentLayer", "nullLayer", "guideLayer", "hasAudio", "hasVideo"]) { assert.equal(result.layers[0][flag], layer[flag]); }
    assert.equal(state.begin, 0); assert.equal(state.writes, 0);
});
test("entire structural plan validates before any project mutation", () => {
    const { api, state, project } = host(), before = project.numItems;
    const invalidPlans = [
        [call("comp.create", { name: "Will not exist" }), call("layer.text.create", { text: "x", unsupported: 1 })],
        [call("comp.create", { name: "Will not exist" }), call("property.set", { layer: { index: 1 }, path: ["bad"] })],
        [call("comp.create", { name: "Will not exist" }), call("unknown", {})],
        [call("comp.create", { name: "Will not exist" }), call("layer.null.create", { comp: { ref: "future" } })],
        [call("comp.create", { name: "Will not exist" }, "same"), call("comp.create", { name: "Other" }, "same")]
    ];
    for (const steps of invalidPlans) { assert.throws(() => api.run(request(steps))); }
    assert.equal(project.numItems, before); assert.equal(state.writes, 0); assert.equal(state.begin, 0);
});
test("static missing or ambiguous comp/layer selectors fail before undo", () => {
    const { api, state, comp, project } = host();
    comp.addLayer("Null").name = "Subject"; state.writes = 0;
    assert.throws(() => api.run(request([call("layer.update", { layer: { name: "Subject" }, name: "No" })])), /ambiguous/);
    assert.throws(() => api.run(request([call("comp.inspect", { comp: { id: 99999 } })])), /not found/);
    project.items.addComp("Main"); state.writes = 0;
    assert.throws(() => api.run(request([call("comp.inspect", { comp: { name: "Main" } })])), /ambiguous/);
    assert.equal(state.begin, 0); assert.equal(state.writes, 0);
});
test("batch creates composition/text/null then chains typed references and transform updates", () => {
    const { api, state } = host(), notifications = [];
    const result = clean(api.run(request([
        call("comp.create", { name: "New", width: 1080, height: 1920, duration: 5 }, "scene"),
        call("layer.text.create", { comp: { ref: "scene" }, text: "Hello", name: "Title", fontSize: 80, fillColor: [1, 0.5, 0], justification: "center" }, "title"),
        call("layer.null.create", { comp: { ref: "scene" }, name: "Controller" }, "controller"),
        call("layer.update", { comp: { ref: "scene" }, layer: { ref: "title" }, transform: { position: [540, 960], opacity: 80 } }),
        call("layer.parent", { comp: { ref: "scene" }, layer: { ref: "title" }, parent: { ref: "controller" } }),
        call("layer.inspect", { comp: { ref: "scene" }, layer: { ref: "title" }, properties: [["ADBE Text Properties", "ADBE Text Document"], ["ADBE Transform Group", "ADBE Position"]] })
    ]), { progress: (...args) => notifications.push(args) }));
    assert.equal(state.begin, 1); assert.equal(state.end, 1); assert.equal(result.count, 6); assert.equal(result.results[5].value.parent, 1); assert.equal(result.results[5].value.properties[0].value.text, "Hello"); assert.deepEqual(result.results[5].value.properties[1].value, [540, 960]); assert.equal(notifications.at(-1)[0], 100);
});
test("property tools write static values and keyframes while preserving unspecified keys", () => {
    const { api, layer } = host(), selected = { layer: { index: 1 }, path: ["ADBE Transform Group", "ADBE Opacity"] };
    api.run(request([call("property.set", { ...selected, value: 50 }), call("property.keyframes", { ...selected, keys: [{ time: 0, value: 0, interpolation: "hold" }, { time: 1, value: 100, interpolation: "bezier" }] })]));
    api.run(request([call("property.set", { ...selected, value: 75, time: 1 })]));
    const property = layer.property("ADBE Transform Group").property("ADBE Opacity");
    assert.deepEqual(property.keys.map(key => [key.time, key.value]), [[0, 0], [1, 75]]); assert.deepEqual(property.keys[0].interpolation, [3, 3]);
    const result = clean(api.run(request([call("property.get", { ...selected, keys: true })]))); assert.equal(result.results[0].value.keys.length, 2);
    assert.throws(() => api.run(request([call("property.set", { ...selected, value: 20 })])), /has keyframes/);
});
test("duplicate keyframe times and unsupported args fail before undo", () => {
    const { api, state } = host();
    assert.throws(() => api.run(request([call("property.keyframes", { layer: { index: 1 }, path: ["ADBE Transform Group", "ADBE Opacity"], keys: [{ time: 1, value: 1 }, { time: 1, value: 2 }] })])), /Duplicate keyframe/);
    assert.throws(() => api.run(request([call("system.info", { source: "app.project.close()" })])), /unsupported field/);
    assert.equal(state.begin, 0);
});
test("property expressions report host compilation errors and always close undo", () => {
    const { api, state, layer } = host(), property = layer.property("ADBE Transform Group").property("ADBE Opacity"), args = { layer: { index: 1 }, path: ["ADBE Transform Group", "ADBE Opacity"], expression: "value * 0.5" };
    api.run(request([call("property.expression", args)])); assert.equal(property.expression, args.expression);
    property.expressionError = "Syntax error";
    assert.throws(() => api.run(request([call("property.expression", { ...args, expression: "bad" })])), /Step 1\/1.*0 completed.*Syntax error/);
    assert.equal(state.begin, state.end);
});
test("installed effects validate matchName before mutation and add via exact API", () => {
    const { api, state, layer } = host();
    assert.throws(() => api.run(request([call("effect.add", { layer: { index: 1 }, matchName: "Missing Plugin" })])), /unavailable/); assert.equal(state.begin, 0);
    const result = clean(api.run(request([call("effect.add", { layer: { index: 1 }, matchName: "ADBE Gaussian Blur 2", name: "Softness" })])));
    assert.equal(result.results[0].value.name, "Softness"); assert.equal(layer.property("ADBE Effect Parade").children.length, 1);
});
test("one batch can add an effect then set its newly created property", () => {
    const { api, layer, state } = host();
    api.run(request([call("effect.add", { layer: { index: 1 }, matchName: "ADBE Gaussian Blur 2", name: "Softness" }), call("property.set", { layer: { index: 1 }, path: ["ADBE Effect Parade", "Softness", "ADBE Gaussian Blur 2-0001"], value: 25 })]));
    assert.equal(layer.property("ADBE Effect Parade").property("Softness").property("ADBE Gaussian Blur 2-0001").value, 25); assert.equal(state.begin, 1); assert.equal(state.end, 1);
});
test("property discovery lists exact paths and enforces limits without changing layers", () => {
    const { api, state } = host();
    const result = clean(api.run(request([call("property.list", { layer: { index: 1 }, path: ["ADBE Transform Group"], maxProperties: 2 })]))).results[0].value;
    assert.equal(result.properties.length, 2); assert.equal(result.properties[0].matchName, "ADBE Position"); assert.equal(result.properties[0].index, 1); assert.equal(result.truncated, true); assert.equal(state.writes, 0); assert.equal(state.begin, 0);
});
test("layer updates validate all transforms before changing layer names or flags", () => {
    const { api, layer, state } = host();
    assert.throws(() => api.run(request([call("layer.update", { layer: { index: 1 }, name: "Must not change", transform: { position: [1, 2, 3] } })])), /requires 2 dimensions/);
    assert.equal(layer.name, "Subject"); assert.equal(state.begin, 0);
    layer.property("ADBE Transform Group").property("ADBE Opacity").setValueAtTime(0, 100);
    assert.throws(() => api.run(request([call("layer.update", { layer: { index: 1 }, name: "Must not change", transform: { opacity: 50 } })])), /has keyframes/); assert.equal(layer.name, "Subject");
});
test("shape tools build actual vector groups, path geometry and optional strokes", () => {
    const { api, comp } = host();
    api.run(request([call("layer.shape.create", { shape: "rect", size: [100, 50], roundness: 10, fillColor: [1, 0, 0] }, "rect"), call("layer.shape.create", { shape: "path", vertices: [[0, 0], [50, 50], [100, 0]], strokeColor: [0, 1, 0], closed: false }, "path")]));
    const pathLayer = comp.layer(1), contents = pathLayer.property("ADBE Root Vectors Group").property(1).property("ADBE Vectors Group"), shape = contents.property("ADBE Vector Shape - Group").property("ADBE Vector Shape").value;
    assert.deepEqual(clean(shape.vertices), [[0, 0], [50, 50], [100, 0]]); assert.equal(shape.closed, false); assert.deepEqual(clean(shape.inTangents), [[0, 0], [0, 0], [0, 0]]);
    assert.throws(() => api.validate(request([call("layer.shape.create", { shape: "path", vertices: [[0, 0], [1, 1]], inTangents: [[0, 0]] })])), /vertices count/);
});
test("spatial temporal easing uses one ease entry and reports unsupported easing without retry", () => {
    const { api, layer, state } = host(), position = layer.property("ADBE Transform Group").property("ADBE Position");
    position.isSpatial = true;
    api.run(request([call("property.keyframes", { layer: { index: 1 }, path: ["ADBE Transform Group", "ADBE Position"], keys: [{ time: 0, value: [0, 0], easing: "ease-in-out" }, { time: 1, value: [100, 50], easing: { inInfluence: 65, outInfluence: 80 } }] })]));
    assert.equal(position.keys[0].ease[0].length, 1);
    assert.equal(position.keys[1].ease[0][0].influence, 65);
    assert.equal(position.keys[1].ease[1][0].influence, 80);
    assert.equal(state.begin, state.end);
    assert.throws(() => api.validate(request([call("property.keyframes", { layer: { index: 1 }, path: ["ADBE Transform Group", "ADBE Position"], keys: [{ time: 2, value: [0, 0], interpolation: "hold", easing: "ease" }] })])), /requires bezier/);
});
test("star and polygon use the correct native shape enum and text preserves explicit false style flags", () => {
    const { api, comp } = host();
    api.run(request([call("layer.shape.create", { shape: "star", points: 6, outerRadius: 120, innerRadius: 45 }), call("layer.shape.create", { shape: "polygon", points: 8, outerRadius: 90 })]));
    const shapeOf = index => comp.layer(index).property("ADBE Root Vectors Group").property(1).property("ADBE Vectors Group").property(1);
    assert.equal(shapeOf(1).property("ADBE Vector Star Type").value, 2);
    assert.equal(shapeOf(2).property("ADBE Vector Star Type").value, 1);
    assert.equal(shapeOf(2).property("ADBE Vector Star Inner Radius").value, 45);
    api.run(request([call("layer.text.create", { text: "Styled", bold: true, italic: false })]));
    const document = comp.layer(1).property("ADBE Text Properties").property("ADBE Text Document").value;
    assert.equal(document.fauxBold, true); assert.equal(document.fauxItalic, false);
    assert.throws(() => api.validate(request([call("layer.shape.create", { shape: "polygon", innerRadius: 10 })])), /no inner radius/);
});
test("parent cycles fail safely; exact name selectors never silently pick duplicates", () => {
    const { api, comp, layer, state } = host(), other = comp.addLayer("Null"); other.parent = layer;
    assert.throws(() => api.run(request([call("layer.parent", { layer: { index: layer.index }, parent: { index: other.index } })])), /cycle/);
    assert.equal(layer.parent, null); assert.equal(state.begin, state.end);
});
test("legacy tool invokes installed branch without filesystem writes or code arguments", () => {
    const { api, state } = host();
    assert.throws(() => api.run(request([call("script.run", { branch: "../evil.jsx" })])), /Invalid/);
    assert.throws(() => api.run(request([call("script.run", { branch: "missing.jsx" })])), /does not exist/);
    assert.throws(() => api.run(request([call("script.run", { branch: "hello.jsx", code: "alert(1)" })])), /unsupported/);
    const result = clean(api.run(request([call("script.run", { branch: "hello.jsx" })]))); assert.deepEqual(state.branches, ["hello.jsx"]); assert.equal(state.writes, 0); assert.equal(result.results[0].value.result, "legacy result");
});
test("partial failure reports completed count, closes undo and never retries a tool", () => {
    const { api, state, layer } = host();
    layer.property("ADBE Transform Group").property("ADBE Opacity").setValue = () => { throw new Error("host write failed"); };
    let error;
    try { api.run(request([call("layer.null.create", { name: "Created once" }), call("property.set", { layer: { index: 1 }, path: ["ADBE Transform Group", "ADBE Opacity"], value: 12 })])); } catch (caught) { error = caught; }
    assert.ok(error); assert.equal(error.completedSteps, 1); assert.equal(error.stepIndex, 1); assert.match(error.message, /1 completed/); assert.equal(state.end, 1); assert.equal(state.writes, 1);
});
test("progress/log callback failures cannot replay calls or change success", () => {
    const { api, state } = host();
    const result = api.run(request([call("script.run", { branch: "hello.jsx" })]), { progress: () => { throw new Error("UI failure"); }, log: () => { throw new Error("disk failure"); } });
    assert.equal(result.count, 1); assert.deepEqual(state.branches, ["hello.jsx"]); assert.equal(state.begin, 1); assert.equal(state.end, 1);
});
test("limits and reference types reject unsupported plans", () => {
    const { api, state } = host();
    assert.throws(() => api.validate(request(Array.from({ length: 101 }, () => call("system.info")))), /1 to 100/);
    assert.throws(() => api.validate(request([call("layer.null.create", {}, "layer"), call("comp.inspect", { comp: { ref: "layer" } })])), /earlier comp/);
    assert.throws(() => api.validate(request([call("system.info", {}, "info")])), /does not create a reference/);
    assert.equal(state.begin, 0);
});
process.stdout.write(passed + " reusable-function tests passed.\n");
