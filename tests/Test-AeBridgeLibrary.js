/* Node regression harness: mocked AE, ScriptUI, scheduling, and file storage. */
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const workspace = path.resolve(__dirname, "..");
const aeWorkspace = "C:/Users/nguye/AE_Codex";
const bridgePath = aeWorkspace + "/jsx/Codex Bridge.jsx";
const realSourceCache = new Map();

function immutableRealSource(local) {
    if (!local) { return null; }
    const cacheKey = local.toLowerCase();
    if (realSourceCache.has(cacheKey)) { return realSourceCache.get(cacheKey); }
    if (!fs.existsSync(local)) { return null; }
    const stat = fs.statSync(local);
    if (!stat.isFile()) { return null; }
    const bytes = fs.readFileSync(local), text = bytes.toString("utf8");
    const entry = { text, binary: bytes.toString("latin1"), byteLength: bytes.length, modified: stat.mtimeMs };
    realSourceCache.set(cacheKey, entry);
    return entry;
}

function mockHost(options = {}) {
    const files = new Map();
    const folders = new Set(["c:/", "c:/users", "c:/users/nguye", aeWorkspace.toLowerCase(), (aeWorkspace + "/jsx").toLowerCase()]);
    const scheduled = new Map();
    const cancelled = [];
    const writes = [];
    const systemCalls = [];
    const createdWindows = [];
    let nextTaskId = 1;
    let executionCount = 0;
    let publicationFailures = 0;
    let now = 1700000000000;
    let context;

    class ClockDate extends Date {
        constructor(...args) { super(...(args.length ? args : [now])); }
        static now() { return now; }
    }

    function normalize(input) {
        return String(input).replace(/\\/g, "/").replace(/\/$/, "");
    }
    function key(input) { return normalize(input).toLowerCase(); }
    function sourcePath(input) {
        const normalized = normalize(input);
        if (normalized.toLowerCase().startsWith((aeWorkspace + "/jsx/").toLowerCase())) {
            return path.join(workspace, "jsx", normalized.slice((aeWorkspace + "/jsx/").length));
        }
        return null;
    }
    function isRealSource(input) {
        return !!immutableRealSource(sourcePath(input));
    }
    function textAt(input) {
        const entry = files.get(key(input)) || immutableRealSource(sourcePath(input));
        return entry ? entry.text : "";
    }
    function put(input, text) {
        const normalized = normalize(input), contents = String(text), bytes = Buffer.from(contents, "utf8");
        files.set(key(normalized), { path: normalized, text: contents, binary: bytes.toString("latin1"), byteLength: bytes.length, modified: now });
    }

    function File(input) {
        if (!(this instanceof File)) { return new File(input); }
        this.fsName = normalize(input);
        this.fullName = this.fsName;
        this.absoluteURI = this.fsName;
        this.encoding = "UTF-8";
        this.alias = false;
        this.error = "";
        this.opened = false;
        this.cursor = 0;
        this.buffer = "";
    }
    Object.defineProperties(File.prototype, {
        name: { get() { return this.fsName.slice(this.fsName.lastIndexOf("/") + 1); } },
        parent: { get() { return new Folder(this.fsName.slice(0, this.fsName.lastIndexOf("/"))); } },
        exists: { get() { return files.has(key(this.fsName)) || isRealSource(this.fsName); } },
        length: { get() {
            const entry = files.get(key(this.fsName)) || immutableRealSource(sourcePath(this.fsName));
            return entry ? entry.byteLength : 0;
        } },
        modified: { get() {
            const entry = files.get(key(this.fsName)) || immutableRealSource(sourcePath(this.fsName));
            return new Date(entry ? entry.modified : 0);
        } },
        eof: { get() { return this.cursor >= this.buffer.length; } }
    });
    File.prototype.open = function (mode) {
        if (mode === "r" && !this.exists) { this.error = "mock missing file"; return false; }
        this.mode = mode;
        this.opened = true;
        this.cursor = 0;
        const entry = mode === "r" || mode === "a" ? files.get(key(this.fsName)) || immutableRealSource(sourcePath(this.fsName)) : null;
        this.buffer = entry ? (this.encoding === "BINARY" ? entry.binary : entry.text) : "";
        if (mode === "a") { this.cursor = this.buffer.length; }
        return true;
    };
    File.prototype.read = function (length) {
        const result = this.buffer.slice(this.cursor, length === undefined ? undefined : this.cursor + length);
        this.cursor += result.length; return result;
    };
    File.prototype.seek = function (offset, mode) {
        this.cursor = (mode === 1 ? this.cursor : mode === 2 ? this.buffer.length : 0) + offset;
        return this.cursor >= 0 && this.cursor <= this.buffer.length;
    };
    File.prototype.readln = function () {
        const end = this.buffer.indexOf("\n", this.cursor);
        const result = this.buffer.slice(this.cursor, end === -1 ? undefined : end).replace(/\r$/, "");
        this.cursor = end === -1 ? this.buffer.length : end + 1;
        return result;
    };
    File.prototype.write = function (text) { this.buffer += String(text); return true; };
    File.prototype.writeln = function (text) { this.buffer += String(text) + "\n"; return true; };
    File.prototype.close = function () {
        if (this.opened && this.mode !== "r") {
            put(this.fsName, this.buffer);
            writes.push(this.fsName);
        }
        this.opened = false;
        return true;
    };
    File.prototype.remove = function () { return files.delete(key(this.fsName)); };
    File.prototype.rename = function (name) {
        const destination = this.parent.fsName + "/" + name;
        if (/^status-.*\.json$/.test(name) && publicationFailures > 0) {
            publicationFailures -= 1;
            this.error = "mock status rename failure";
            return false;
        }
        if (!files.has(key(this.fsName)) || files.has(key(destination))) {
            this.error = "mock missing source or occupied destination";
            return false;
        }
        const entry = files.get(key(this.fsName));
        files.delete(key(this.fsName));
        put(destination, entry.text);
        this.fsName = destination;
        this.fullName = destination;
        this.absoluteURI = destination;
        return true;
    };
    File.prototype.execute = function () { return true; };
    File.prototype.toString = function () { return this.fsName; };

    function Folder(input) {
        if (!(this instanceof Folder)) { return new Folder(input); }
        this.fsName = normalize(input);
        this.fullName = this.fsName;
        this.absoluteURI = this.fsName;
        this.alias = false;
        this.error = "";
    }
    Object.defineProperties(Folder.prototype, {
        name: { get() { return this.fsName.slice(this.fsName.lastIndexOf("/") + 1); } },
        parent: { get() { return new Folder(this.fsName.slice(0, this.fsName.lastIndexOf("/"))); } },
        exists: { get() { return folders.has(key(this.fsName)); } }
    });
    Folder.prototype.create = function () { folders.add(key(this.fsName)); return true; };
    Folder.prototype.getFiles = function (filter) {
        const prefix = key(this.fsName) + "/";
        const children = [];
        for (const entry of files.values()) {
            const relative = key(entry.path).slice(prefix.length);
            if (key(entry.path).startsWith(prefix) && relative && !relative.includes("/")) { children.push(new File(entry.path)); }
        }
        for (const entry of folders) {
            const relative = entry.slice(prefix.length);
            if (entry.startsWith(prefix) && relative && !relative.includes("/")) { children.push(new Folder(entry)); }
        }
        return typeof filter === "function" ? children.filter(filter) : children;
    };
    Folder.prototype.toString = function () { return this.fsName; };
    Folder.current = new Folder(aeWorkspace);
    Folder.userData = new Folder("C:/Users/nguye/AppData/Roaming");
    Folder.myDocuments = new Folder("C:/Users/nguye/Documents");
    Folder.appData = new Folder("C:/ProgramData");

    function control(type, title) {
        return {
            type, text: title || "", value: 0, children: [], visible: true,
            layout: { layout() {}, resize() {} },
            graphics: { PenType: { SOLID_COLOR: 1 }, newPen() { return {}; } },
            add(kind, bounds, value, creationProperties) {
                const child = control(kind, value);
                child.creationProperties = creationProperties || {};
                this.children.push(child);
                return child;
            },
            show() {}, update() {}, center() {}
        };
    }
    function Window(kind, title) {
        Object.assign(this, control(kind, title));
        createdWindows.push(this);
    }
    function Panel() { Object.assign(this, control("panel")); }
    function CompItem() {}
    function FootageItem() {}
    function denyMutation() { throw new Error("Project mutation is forbidden during library inventory"); }

    const app = {
        version: "26.5-test", path: new Folder("C:/Program Files/Adobe/Adobe After Effects 2026/Support Files"),
        effects: [
            { displayName: "Mock Glow", matchName: "Mock Glow", category: "Test", version: "1.0" },
            { displayName: "Trailing matchName", matchName: "Enhance AI ", category: "Test", version: "1.0" }
        ],
        project: options.project === undefined ? {
            numItems: 0, file: null, activeItem: null, item() { return null; },
            items: { addComp: denyMutation, addFolder: denyMutation },
            importFile: denyMutation, save: denyMutation, close: denyMutation
        } : options.project,
        preferences: { getPrefAsLong() { return 1; } },
        beginUndoGroup: denyMutation, endUndoGroup: denyMutation,
        scheduleTask(code, delay, repeat) {
            assert.equal(repeat, false, "bridge callbacks must remain one-shot");
            const id = nextTaskId++;
            scheduled.set(id, { code, delay });
            return id;
        },
        cancelTask(id) { cancelled.push(id); scheduled.delete(id); }
    };
    const dollar = {
        global: {}, fileName: bridgePath, os: "Windows", sleep() {},
        evalFile(file) {
            const normalized = normalize(file.fsName || file);
            if (/\/jsx\/test-job\.jsx$/i.test(normalized)) {
                executionCount += 1;
                return options.executeJob ? options.executeJob(dollar.global.__CODEX_AE_RUN_CONTEXT__) : "mock job completed";
            }
            const prior = dollar.fileName;
            dollar.fileName = normalized;
            try {
                return vm.runInContext(textAt(normalized).replace(/^#.*$/gm, ""), context, { filename: normalized });
            } finally { dollar.fileName = prior; }
        }
    };
    context = vm.createContext({
        app, $: dollar, File, Folder, Window, Panel, CompItem, FootageItem,
        PropertyType: { PROPERTY: 1, INDEXED_GROUP: 2, NAMED_GROUP: 3 },
        PropertyValueType: { NO_VALUE: 0, CUSTOM_VALUE: 1, OneD: 2 },
        ScriptUI: { newFont() { return {}; } }, Date: ClockDate,
        system: {
            callSystem(command) {
                systemCalls.push(command);
                const request = command.match(/-RequestId "([A-Za-z0-9-]+)"/);
                if (request && options.launchAck !== false) {
                    const acknowledgement = Object.assign({ schemaVersion: 1, requestId: request[1], state: "launched", processId: 1234 }, typeof options.launchAck === "object" ? options.launchAck : {});
                    const contents = typeof options.launchAck === "string" ? options.launchAck : JSON.stringify(acknowledgement);
                    put(aeWorkspace + "/.ae-codex/library/requests/launch-sfx-" + request[1] + ".json", contents);
                }
                return options.launchStdout === undefined ? "" : options.launchStdout;
            }
        }, alert() {}, console
    });
    if (options.startupOnly) { dollar.global.__CODEX_AE_AUTOSTART_ONLY__ = true; }
    try { vm.runInContext(textAt(bridgePath).replace(/^#.*$/gm, ""), context, { filename: bridgePath }); }
    finally { delete dollar.global.__CODEX_AE_AUTOSTART_ONLY__; }
    // Most inventory/decoder tests own connection setup explicitly. The opening
    // behavior is exercised separately without disabling production autostart.
    if (!options.keepAutoStart) { dollar.global.__codexAeBridgeV1.stop(); }

    function fireNext() {
        const first = scheduled.entries().next().value;
        if (!first) { throw new Error("No scheduled bridge callback"); }
        const [id, task] = first;
        scheduled.delete(id);
        now += task.delay;
        vm.runInContext(task.code, context);
        return task;
    }
    function connect() {
        const bridge = dollar.global.__codexAeBridgeV1;
        bridge.start();
        for (let i = 0; !bridge.ready && bridge.running && i < 300; i++) { fireNext(); }
        assert.equal(bridge.ready, true, bridge.lastStatus);
        return bridge;
    }
    function job(runId = "test-run-0001", nonce) {
        const bridge = dollar.global.__codexAeBridgeV1;
        const jobPath = bridge.inboxPath + "/job-" + runId + ".job";
        put(aeWorkspace + "/jsx/test-job.jsx", "/* mock */");
        put(jobPath, "schema=codex-ae-job/v1\nrunId=" + runId + "\nsessionNonce=" + (nonce || bridge.sessionNonce) + "\nscript=jsx/test-job.jsx\n");
        return new File(jobPath);
    }
    return {
        context, app, dollar, files, folders, writes, systemCalls, createdWindows, scheduled, cancelled, File, Folder, CompItem, FootageItem, put, textAt,
        connect, fireNext, job,
        bridge: dollar.global.__codexAeBridgeV1,
        advanceTime(milliseconds) { now += milliseconds; },
        get executionCount() { return executionCount; },
        failPublication(count) { publicationFailures = count; }
    };
}

const tests = [];
function test(name, run) { tests.push({ name, run }); }

function enableSfxLauncher(host) {
    host.put(aeWorkspace + "/.ae-codex/library/runtime.json", JSON.stringify({ powerShellPath: "C:/Program Files/PowerShell/7/pwsh.exe" }));
    host.put("C:/Program Files/PowerShell/7/pwsh.exe", "mock executable");
    host.put(aeWorkspace + "/tools/Start-AeSfxCatalog.ps1", "# mock launcher");
}

function directLibrary(host, launchSfx = false) {
    host.bridge.running = true;
    host.bridge.generation += 1;
    if (launchSfx) { enableSfxLauncher(host); }
    host.dollar.global.__codexAeBundleV1.run("Codex Library.jsx");
    const library = host.dollar.global.__codexAeLibraryFactoryV1(host.bridge);
    library.begin(host.bridge.generation);
    return library;
}

function successfulSfxStatus(host, library, overrides = {}) {
    const prefix = ".ae-codex/library/sessions/" + host.bridge.sessionNonce + "/";
    return Object.assign({
        schemaVersion: 1, kind: "disk-sfx", requestId: library.requestId, sessionId: host.bridge.sessionNonce,
        state: "success", count: 12,
        catalogRelativePath: prefix + "sfx-" + library.requestId + ".jsonl",
        summaryRelativePath: prefix + "summary-sfx-" + library.requestId + ".json",
        warnings: []
    }, overrides);
}

function putSfxStatus(host, library, status) {
    host.put(library.folder + "/status-sfx-" + library.requestId + ".json", typeof status === "string" ? status : JSON.stringify(status));
    host.advanceTime(1500);
}

function damageBundleByte(original, position) {
    const bytes = Buffer.from(original, "utf8");
    assert.ok(position >= 0 && position < bytes.length, "damage must target a real payload byte");
    assert.ok(bytes[position] < 128, "payload records must use ASCII URI encoding");
    bytes[position] = bytes[position] === 88 ? 89 : 88;
    return bytes.toString("utf8");
}

function moduleUsers(bundle) {
    const users = new Map();
    for (const name of bundle.names) {
        const ids = new Set(bundle.recipe(name).split("|").map(slice => slice.split(":")[0]));
        for (const id of ids) {
            if (!users.has(id)) { users.set(id, []); }
            users.get(id).push(name);
        }
    }
    return users;
}

function decodeInjectedModule(host, record) {
    const { checksum } = require("../tools/Build-AeScriptBundle.js");
    const bundle = host.bridge.bundle, id = Object.keys(bundle.modules)[0], entry = bundle.modules[id];
    const position = bundle.payloadOffset + entry.offset, originalRead = host.File.prototype.read;
    const original = { length: entry.length, checksum: entry.checksum,
        moduleCache: bundle.moduleCache, cacheOrder: bundle.cacheOrder, cacheSize: bundle.cacheSize };
    entry.length = record.length;
    entry.checksum = checksum(record);
    bundle.moduleCache = {}; bundle.cacheOrder = []; bundle.cacheSize = 0;
    host.File.prototype.read = function (length) {
        if (this.fsName === bridgePath && this.cursor === position && length === record.length) {
            this.cursor += record.length;
            return record;
        }
        return originalRead.call(this, length);
    };
    try { return bundle.moduleSource(id); }
    finally {
        host.File.prototype.read = originalRead;
        entry.length = original.length; entry.checksum = original.checksum;
        bundle.moduleCache = original.moduleCache; bundle.cacheOrder = original.cacheOrder; bundle.cacheSize = original.cacheSize;
    }
}

test("opening panel automatically connects without a Start click", () => {
    const host = mockHost({ keepAutoStart: true });
    const bridge = host.bridge;
    assert.equal(bridge.running, true);
    assert.equal(host.scheduled.size, 1, "opening schedules one connection task");
    for (let i = 0; !bridge.ready && bridge.running && i < 300; i++) { host.fireNext(); }
    assert.equal(bridge.ready, true, bridge.lastStatus);
    assert.equal(bridge.connectionConnected, true);
    assert.equal(host.scheduled.size, 1, "one timer must own the connected listener");
    assert.ok(bridge.logs.length > 0, "connection progress must appear in the panel log");
    assert.equal(host.executionCount, 0);
});

test("Stop cancels autoconnect and stays stopped until explicitly reconnected", () => {
    const host = mockHost({ keepAutoStart: true });
    const bridge = host.bridge, delivered = host.scheduled.values().next().value.code;
    bridge.stop();
    host.advanceTime(300000);
    vm.runInContext(delivered, host.context);
    assert.equal(bridge.running, false);
    assert.equal(bridge.ready, false);
    assert.equal(host.scheduled.size, 0, "a stopped panel cannot reconnect itself");
    assert.equal(JSON.parse(host.textAt(bridge.heartbeatPath)).state, "stopped");
});

test("reopening and repeated reconnects keep only one listener timer", () => {
    const host = mockHost({ keepAutoStart: true });
    for (let attempt = 0; attempt < 3; attempt++) {
        host.dollar.evalFile(new host.File(bridgePath));
        assert.equal(host.bridge.running, true);
        assert.equal(host.scheduled.size, 1, "reopening must replace the previous task");
        host.bridge.start();
        assert.equal(host.scheduled.size, 1, "reconnect must replace the previous task");
    }
    const bridge = host.bridge;
    for (let i = 0; !bridge.ready && bridge.running && i < 300; i++) { host.fireNext(); }
    assert.equal(bridge.ready, true, bridge.lastStatus);
    assert.equal(host.scheduled.size, 1);
});

test("connection failures are recorded in the panel log", () => {
    const host = mockHost({ keepAutoStart: true });
    host.folders.delete(aeWorkspace.toLowerCase());
    host.fireNext();
    assert.equal(host.bridge.running, false);
    assert.equal(host.bridge.ready, false);
    assert.equal(host.scheduled.size, 0);
    assert.ok(host.bridge.logs.some(entry => entry.level === "error" && /workspace/i.test(entry.message)));
    assert.match(host.bridge.logView.text, /workspace/i);
});

test("startup loader connects quietly once and respects a manually stopped session", () => {
    const host = mockHost({ keepAutoStart: true, startupOnly: true }), bridge = host.bridge;
    assert.equal(host.createdWindows.length, 0, "startup loader cannot create a floating panel");
    assert.equal(bridge.running, true);
    assert.equal(host.scheduled.size, 1);
    for (let i = 0; !bridge.ready && bridge.running && i < 300; i++) { host.fireNext(); }
    assert.equal(bridge.ready, true, bridge.lastStatus);
    function runLoader() {
        host.dollar.global.__CODEX_AE_AUTOSTART_ONLY__ = true;
        try { host.dollar.evalFile(new host.File(bridgePath)); }
        finally { delete host.dollar.global.__CODEX_AE_AUTOSTART_ONLY__; }
    }
    const currentTask = bridge.taskId;
    runLoader(); runLoader();
    assert.equal(host.scheduled.size, 1);
    assert.equal(bridge.taskId, currentTask, "repeated startup loader leaves the live listener alone");
    assert.equal(host.createdWindows.length, 0);
    bridge.stop();
    runLoader();
    assert.equal(bridge.running, false, "startup loader must preserve the user's Stop choice");
    assert.equal(host.scheduled.size, 0);
    host.dollar.evalFile(new host.File(bridgePath));
    assert.equal(bridge.running, true, "opening the panel intentionally reconnects");
    assert.equal(host.scheduled.size, 1);
    assert.equal(host.createdWindows.length, 1);
});

test("Stop and Start invalidate already-delivered callbacks", () => {
    const host = mockHost();
    host.bridge.start();
    const oldGeneration = host.bridge.generation;
    const oldTask = host.scheduled.values().next().value.code;
    host.bridge.stop();
    host.bridge.start();
    const currentTask = host.bridge.taskId;
    const writesBefore = host.writes.length;
    vm.runInContext(oldTask, host.context);
    assert.equal(host.bridge.taskId, currentTask, "old callbacks cannot clear new task ownership");
    assert.equal(host.writes.length, writesBefore, "old callbacks cannot publish inventory or heartbeat");
    assert.ok(host.bridge.generation > oldGeneration);
    host.bridge.stop();
    assert.equal(host.scheduled.size, 0);
});

test("JSX evaluation executes once when terminal publication retries", () => {
    const host = mockHost();
    const bridge = host.connect();
    host.failPublication(4);
    bridge.processJob(host.job());
    assert.equal(host.executionCount, 1);
    assert.ok(bridge.pendingReport);
    assert.equal(bridge.busy, true);
    assert.ok(bridge.logs.some(entry => entry.runId === "test-run-0001" &&
        /publish|report|retry/i.test(entry.message)), "publication failure must be visible in the work log");
    bridge.stop();
    host.connect();
    bridge.publishPendingReport();
    assert.equal(host.executionCount, 1, "restart must not evaluate a completed job again");
    assert.equal(bridge.pendingReport, null);
    const started = JSON.parse(host.textAt(bridge.resultsPath + "/started-test-run-0001.json"));
    const status = JSON.parse(host.textAt(bridge.resultsPath + "/status-test-run-0001.json"));
    assert.equal(started.state, "running");
    assert.equal(status.state, "success");
    assert.equal(status.completionKnown, true);
});

test("work log shows script progress, messages and successful completion", () => {
    const host = mockHost({ executeJob(runContext) {
        assert.equal(typeof runContext.progress, "function");
        assert.equal(typeof runContext.log, "function");
        runContext.progress(35, "Preparing requested layers");
        runContext.log("Layer setup finished", "info");
        return "mock progress result";
    } });
    const bridge = host.connect(), runId = "progress-run-0001";
    bridge.processJob(host.job(runId));
    const entries = bridge.logs.filter(entry => entry.runId === runId);
    assert.ok(entries.some(entry => /Preparing requested layers/.test(entry.message)));
    assert.ok(entries.some(entry => /Layer setup finished/.test(entry.message)));
    assert.ok(entries.some(entry => /success|completed/i.test(entry.message)), "successful completion needs a log entry");
    assert.ok(entries.every(entry => entry.time && entry.level && typeof entry.message === "string"));
    assert.ok(bridge.logView.text.includes("Preparing requested layers"), "panel must render work progress");
    assert.equal(host.dollar.global.__CODEX_AE_RUN_CONTEXT__, undefined, "run hooks cannot leak into the next script");
    const status = JSON.parse(host.textAt(bridge.resultsPath + "/status-" + runId + ".json"));
    assert.equal(status.state, "success");
    assert.equal(status.result, "mock progress result");
});

test("script errors remain visible in the work log and terminal status", () => {
    const host = mockHost({ executeJob() { throw new Error("mock requested edit failed"); } });
    const bridge = host.connect(), runId = "error-run-0001";
    bridge.processJob(host.job(runId));
    assert.equal(host.executionCount, 1);
    assert.ok(bridge.logs.some(entry => entry.runId === runId && entry.level === "error" &&
        /mock requested edit failed/.test(entry.message)));
    assert.ok(bridge.logView.text.includes("mock requested edit failed"));
    assert.equal(host.dollar.global.__CODEX_AE_RUN_CONTEXT__, undefined);
    const status = JSON.parse(host.textAt(bridge.resultsPath + "/status-" + runId + ".json"));
    assert.equal(status.state, "error");
    assert.equal(status.errorCode, "JSX_EXECUTION_FAILED");
    assert.match(status.message, /mock requested edit failed/);
});

test("panel log is readonly and bounded during long sessions", () => {
    const host = mockHost(), bridge = host.bridge;
    assert.equal(bridge.logView.type, "edittext");
    assert.equal(bridge.logView.creationProperties.readonly, true);
    assert.equal(bridge.logView.creationProperties.multiline, true);
    for (let index = 0; index < 260; index++) { bridge.appendLog("info", "bounded-message-" + index, "bounded-run-0001"); }
    assert.equal(bridge.logs.length, 200);
    assert.equal(bridge.logs[0].message, "bounded-message-60");
    assert.equal(bridge.logs[199].message, "bounded-message-259");
    assert.equal(bridge.logView.text.includes("bounded-message-0\n"), false);
    assert.ok(bridge.logView.text.includes("bounded-message-259"));
});

test("disk log appends complete JSON lines while preserving earlier events", () => {
    const host = mockHost(), bridge = host.bridge;
    const logPath = bridge.bridgeRoot + "/logs/events.log";
    const original = host.textAt(logPath);
    const message = 'Tiếng Việt "quoted"\nsecond line';
    bridge.appendLog("info", message, "persist-run-0001", 40);
    bridge.appendLog("warning", "Following event", "persist-run-0001");
    const contents = host.textAt(logPath);
    assert.ok(contents.startsWith(original), "append mode must preserve all earlier persisted events");
    const entries = contents.trim().split("\n").map(line => JSON.parse(line));
    assert.equal(entries.at(-2).message, message);
    assert.equal(entries.at(-2).runId, "persist-run-0001");
    assert.equal(entries.at(-2).percent, 40);
    assert.equal(entries.at(-1).message, "Following event");
    assert.equal(entries.at(-1).level, "warning");
    assert.equal(bridge.logWriteError, "");
});

test("disk log rotates at its size limit and retains the previous log", () => {
    const host = mockHost(), bridge = host.bridge;
    const logPath = bridge.bridgeRoot + "/logs/events.log", previousPath = bridge.bridgeRoot + "/logs/previous.log";
    const fullLog = "retained previous session\n".padEnd(262144, "x");
    host.put(logPath, fullLog);
    host.put(previousPath, "older rotation");
    bridge.appendLog("info", "First event after rotation", "rotate-run-0001");
    assert.equal(host.textAt(previousPath), fullLog, "rotation must retain the old active log exactly");
    const rows = host.textAt(logPath).trim().split("\n");
    assert.equal(rows.length, 1, "the current log starts fresh after rotation");
    assert.equal(JSON.parse(rows[0]).message, "First event after rotation");
    bridge.appendLog("info", "Second event after rotation", "rotate-run-0001");
    assert.equal(host.textAt(previousPath), fullLog);
    assert.equal(host.textAt(logPath).trim().split("\n").length, 2);
});

test("disk logging exceptions cannot change job execution or result publication", () => {
    for (const failure of ["open", "write"]) {
        const host = mockHost(), bridge = host.connect(), runId = "log-" + failure + "-run-0001";
        const normalOpen = host.File.prototype.open, normalWrite = host.File.prototype.write;
        host.File.prototype.open = function (mode) {
            if (failure === "open" && /\/logs\/events\.log$/.test(this.fsName)) { throw new Error("mock log open failure"); }
            return normalOpen.call(this, mode);
        };
        host.File.prototype.write = function (contents) {
            if (failure === "write" && /\/logs\/events\.log$/.test(this.fsName)) { throw new Error("mock log write failure"); }
            return normalWrite.call(this, contents);
        };
        host.failPublication(4);
        bridge.processJob(host.job(runId));
        assert.equal(host.executionCount, 1);
        assert.ok(bridge.pendingReport, "result publication still follows its normal retry path");
        bridge.publishPendingReport();
        assert.equal(bridge.pendingReport, null);
        assert.equal(host.executionCount, 1, "logging errors cannot cause script reevaluation");
        const status = JSON.parse(host.textAt(bridge.resultsPath + "/status-" + runId + ".json"));
        assert.equal(status.state, "success");
        assert.match(bridge.logWriteError, /mock log (?:open|write) failure/);
        assert.ok(bridge.logs.some(entry => entry.runId === runId && /completed|success/i.test(entry.message)),
            "memory log remains usable when disk logging fails");
    }
});

test("disposed log controls cannot interrupt a job or lose its result", () => {
    const host = mockHost(), bridge = host.connect(), runId = "disposed-log-run-0001";
    Object.defineProperty(bridge.logView, "text", {
        configurable: true, get() { throw new Error("mock disposed log control"); },
        set() { throw new Error("mock disposed log control"); }
    });
    bridge.processJob(host.job(runId));
    assert.equal(host.executionCount, 1);
    assert.equal(bridge.logView, null, "a disposed control must be detached from later log updates");
    assert.equal(bridge.pendingReport, null);
    const status = JSON.parse(host.textAt(bridge.resultsPath + "/status-" + runId + ".json"));
    assert.equal(status.state, "success");
    assert.ok(bridge.logs.some(entry => entry.runId === runId && /completed|success/i.test(entry.message)));
    const persisted = host.textAt(bridge.bridgeRoot + "/logs/events.log").trim().split("\n").map(line => JSON.parse(line));
    assert.ok(persisted.some(entry => entry.runId === runId));
});

test("immutable started and terminal status files are never overwritten", () => {
    const host = mockHost();
    const bridge = host.connect();
    bridge.processJob(host.job());
    const startedPath = bridge.resultsPath + "/started-test-run-0001.json";
    const statusPath = bridge.resultsPath + "/status-test-run-0001.json";
    const originalStarted = host.textAt(startedPath);
    const originalStatus = host.textAt(statusPath);
    assert.throws(() => bridge.writeStarted("test-run-0001", "replacement", 0), /immutable/i);
    assert.throws(() => bridge.writeStatus({ runId: "test-run-0001", state: "error" }), /immutable/i);
    assert.equal(host.textAt(startedPath), originalStarted);
    assert.equal(host.textAt(statusPath), originalStatus);
});

test("failed started preflight cannot evaluate project JSX", () => {
    const host = mockHost();
    const bridge = host.connect();
    const normalRename = host.File.prototype.rename;
    host.File.prototype.rename = function (name) {
        if (name === "started-preflight-run-0001.json") { this.error = "mock preflight publication failure"; return false; }
        return normalRename.call(this, name);
    };
    bridge.processJob(host.job("preflight-run-0001"));
    assert.equal(host.executionCount, 0);
    const status = JSON.parse(host.textAt(bridge.resultsPath + "/status-preflight-run-0001.json"));
    assert.equal(status.errorCode, "START_STATUS_FAILED");
    assert.equal(status.completionKnown, true);
    assert.equal(status.retryable, true);
});

test("jobs belonging to another AE instance remain unclaimed", () => {
    const host = mockHost();
    const bridge = host.connect();
    const foreign = host.job("foreign-run-0001", "foreign-session-0001");
    bridge.processJob(foreign);
    assert.equal(foreign.exists, true);
    assert.equal(host.executionCount, 0);
    assert.equal(bridge.busy, false);
});

test("registered effects can be read when no project is open", () => {
    const host = mockHost({ project: null });
    host.connect();
    assert.equal(host.app.project, null);
    assert.equal(host.executionCount, 0);
});

test("library scans registered effects with no project and preserves exact matchNames", () => {
    const host = mockHost({ project: null });
    const library = directLibrary(host);
    library.tick();
    const manifest = JSON.parse(host.textAt(library.root + "/current.json"));
    assert.equal(manifest.effectsState, "ready");
    assert.equal(manifest.effectsCount, 2);
    assert.equal(manifest.projectAudioCount, 0);
    const tsv = host.textAt(aeWorkspace + "/" + manifest.effectsRelativePath);
    assert.ok(tsv.includes("\tEnhance AI \t"), "trailing spaces are part of the effect matchName");
    const audio = JSON.parse(host.textAt(aeWorkspace + "/" + manifest.projectAudioRelativePath));
    assert.deepEqual(audio.items, []);
    assert.equal(host.executionCount, 0);
});

test("project scanning yields between chunks and never evaluates custom property data", () => {
    const host = mockHost();
    let layerReads = 0;
    let customReads = 0;
    const custom = {
        propertyType: 1, propertyValueType: 1, matchName: "Mock-Custom", name: "Private Data",
        hasMin: false, hasMax: false,
        get value() { customReads += 1; throw new Error("custom values must not be read"); }
    };
    const number = { propertyType: 1, propertyValueType: 2, matchName: "Mock-Radius", name: "Radius", hasMin: true, minValue: 0, hasMax: true, maxValue: 100, value: 42 };
    const effect = { matchName: "Mock Glow", name: "Mock Glow", numProperties: 2, property(n) { return [custom, number][n - 1]; } };
    const parade = { numProperties: 1, property() { return effect; } };
    const comp = new host.CompItem();
    comp.numLayers = 18;
    comp.layer = function () { layerReads += 1; return { property(name) { assert.equal(name, "ADBE Effect Parade"); return parade; } }; };
    host.app.project.numItems = 1;
    host.app.project.item = function () { return comp; };
    const library = directLibrary(host);
    for (let i = 0; !library.aeDone && i < 20; i++) {
        const before = layerReads;
        library.tick();
        assert.ok(layerReads - before <= 6, "each inventory tick must yield after its layer budget");
    }
    assert.equal(library.aeDone, true);
    assert.equal(layerReads, 18);
    assert.equal(customReads, 0);
    assert.equal(library.state.appliedSchemaCount, 1, "shared effect schema is collected once");
    const tsv = host.textAt(aeWorkspace + "/" + library.state.effectsRelativePath);
    assert.ok(tsv.includes("Mock-Radius\tRadius\t1\tmin=0 max=100\t42"));
});

test("audio inventory records existing footage without importing or changing media", () => {
    const host = mockHost();
    const footage = new host.FootageItem();
    Object.assign(footage, { id: 123, name: "Boing.wav", hasAudio: true, hasVideo: false, duration: 0.5, file: new host.File("D:/SFX/Boing.wav") });
    host.put("D:/SFX/Boing.wav", "mock audio metadata");
    host.app.project.numItems = 1;
    host.app.project.item = function () { return footage; };
    const library = directLibrary(host);
    library.tick();
    const audio = JSON.parse(host.textAt(aeWorkspace + "/" + library.state.projectAudioRelativePath));
    assert.equal(audio.items.length, 1);
    assert.equal(audio.items[0].filePath, "D:/SFX/Boing.wav");
    assert.equal(audio.items[0].available, true);
    assert.equal(audio.items[0].duration, 0.5);
    assert.ok(host.writes.every(file => file.toLowerCase().startsWith((aeWorkspace + "/.ae-codex/").toLowerCase())));
});

test("valid helper status connects only the current session catalog", () => {
    const host = mockHost();
    const library = directLibrary(host, true);
    assert.equal(host.systemCalls.length, 1);
    assert.ok(host.systemCalls[0].includes("-WindowStyle Hidden"));
    putSfxStatus(host, library, successfulSfxStatus(host, library));
    library.tick();
    const manifest = JSON.parse(host.textAt(library.root + "/current.json"));
    assert.equal(manifest.state, "ready");
    assert.equal(manifest.sfxState, "ready");
    assert.equal(manifest.sfxCount, 12);
    assert.ok(manifest.sfxRelativePath.includes(library.requestId));
});

test("native Windows PowerShell paths are accepted by the SFX launcher", () => {
    const host = mockHost();
    enableSfxLauncher(host);
    host.put(aeWorkspace + "/.ae-codex/library/runtime.json", JSON.stringify({ powerShellPath: "C:\\Program Files\\PowerShell\\7\\pwsh.exe" }));
    const library = directLibrary(host);
    assert.equal(library.sfxDone, false);
    assert.equal(library.state.sfxState, "scanning");
    assert.equal(host.systemCalls.length, 1);
    assert.ok(host.systemCalls[0].includes('"C:\\Program Files\\PowerShell\\7\\pwsh.exe"'));
});

test("empty AE callSystem stdout succeeds with a validated launcher acknowledgement", () => {
    const host = mockHost({ launchStdout: "" });
    const library = directLibrary(host, true);
    assert.equal(library.sfxDone, false);
    assert.equal(library.state.sfxState, "scanning");
    assert.deepEqual(Array.from(library.state.errors), []);
    const acknowledgement = JSON.parse(host.textAt(library.root + "/requests/launch-sfx-" + library.requestId + ".json"));
    assert.equal(acknowledgement.requestId, library.requestId);
    assert.equal(acknowledgement.state, "launched");
});

test("stdout markers cannot substitute for a missing launcher acknowledgement", () => {
    const host = mockHost({ launchAck: false, launchStdout: "CODEX_SFX_LAUNCHED" });
    const library = directLibrary(host, true);
    library.tick();
    assert.equal(library.state.sfxState, "error");
    assert.equal(library.state.state, "partial");
    assert.ok(library.state.errors.some(message => /not acknowledged/.test(message)));
});

test("mismatched, malformed, or invalid launcher acknowledgements are rejected as data", () => {
    const invalid = [
        { schemaVersion: 2 },
        { requestId: "another-library-request-0001" },
        { state: "error" },
        { processId: 0 },
        { processId: -1 },
        { processId: "1234" },
        '{"schemaVersion":1}; app.project.save()'
    ];
    for (const launchAck of invalid) {
        const host = mockHost({ launchAck });
        const library = directLibrary(host, true);
        library.tick();
        assert.equal(library.sfxDone, true);
        assert.equal(library.state.sfxState, "error");
        assert.equal(library.state.state, "partial");
        assert.equal(host.executionCount, 0);
    }
});

test("foreign helper status cannot advertise another bridge catalog", () => {
    const host = mockHost();
    const library = directLibrary(host, true);
    putSfxStatus(host, library, successfulSfxStatus(host, library, { sessionId: "another-session-0001" }));
    library.tick();
    assert.equal(library.state.sfxState, "error");
    assert.equal(library.state.sfxCount, 0);
    assert.equal(library.state.sfxRelativePath, undefined);
    assert.equal(library.state.state, "partial");
});

test("JSON status rejects code, duplicate keys, and prototype keys without eval", () => {
    const rejected = [
        '{"state":"success"}; app.project.save()',
        '{"state":"success","state":"error"}',
        '{"__proto__":{"polluted":true}}',
        '{"hasOwnProperty":false,"state":"success"}',
        '{"state":"success","count":NaN}',
        '{"state":"success",}'
    ];
    for (const input of rejected) {
        const host = mockHost();
        const library = directLibrary(host, true);
        putSfxStatus(host, library, input);
        library.tick();
        assert.equal(library.state.sfxState, "error", input);
        assert.equal(library.state.state, "partial", input);
        assert.equal(host.executionCount, 0);
        assert.equal({}.polluted, undefined);
    }
});

test("Stop discards late helper results and generation changes prevent old publication", () => {
    const host = mockHost();
    const oldLibrary = directLibrary(host, true);
    oldLibrary.stop();
    const stoppedManifest = host.textAt(oldLibrary.root + "/current.json");
    putSfxStatus(host, oldLibrary, successfulSfxStatus(host, oldLibrary));
    oldLibrary.tick();
    assert.equal(host.textAt(oldLibrary.root + "/current.json"), stoppedManifest);
    assert.equal(oldLibrary.state.sfxCount, 0);
    host.advanceTime(500);
    const newLibrary = directLibrary(host, true);
    assert.notEqual(newLibrary.requestId, oldLibrary.requestId);
    const newManifest = host.textAt(newLibrary.root + "/current.json");
    oldLibrary.active = true;
    oldLibrary.tick();
    assert.equal(host.textAt(newLibrary.root + "/current.json"), newManifest);
});

test("changing the open project during a scan yields a partial inventory", () => {
    const host = mockHost();
    const library = directLibrary(host);
    host.app.project = null;
    library.tick();
    assert.equal(library.aeDone, true);
    assert.equal(library.state.state, "partial");
    assert.ok(library.state.errors.some(message => /Project changed/.test(message)));
});

test("Start automatically publishes library metadata and heartbeat paths", () => {
    const host = mockHost();
    enableSfxLauncher(host);
    const bridge = host.connect();
    const library = bridge.library;
    assert.ok(library, "Start must initialize the library module");
    assert.equal(library.generation, bridge.generation);
    assert.match(library.requestId, /^[A-Za-z0-9-]{8,120}$/);
    assert.equal(host.systemCalls.length, 1);
    const heartbeat = JSON.parse(host.textAt(bridge.heartbeatPath));
    assert.equal(heartbeat.library.requestId, library.requestId);
    assert.equal(heartbeat.library.manifestRelativePath, ".ae-codex/library/current.json");
    assert.equal(heartbeat.library.effectsCount, 2);
    assert.equal(host.scheduled.size, 1, "one scheduler owns both jobs and library work");
});

test("periodic library refresh waits behind queued jobs and preserves old snapshots", () => {
    const host = mockHost();
    enableSfxLauncher(host);
    const bridge = host.connect();
    const library = bridge.library;
    putSfxStatus(host, library, successfulSfxStatus(host, library));
    host.fireNext();
    assert.equal(library.state.state, "ready");
    const previousRequest = library.requestId;
    const previousSnapshotPath = aeWorkspace + "/" + library.state.effectsRelativePath;
    const previousSnapshot = host.textAt(previousSnapshotPath);
    host.advanceTime(120001);
    host.job("queued-run-0001");
    host.fireNext();
    assert.equal(host.executionCount, 1);
    assert.equal(library.requestId, previousRequest, "queued JSX gets the next scheduler tick before inventory refresh");
    assert.equal(host.systemCalls.length, 1);
    host.fireNext();
    assert.notEqual(library.requestId, previousRequest);
    assert.equal(host.systemCalls.length, 2);
    assert.equal(host.textAt(previousSnapshotPath), previousSnapshot, "refresh must retain the previous immutable inventory");
    assert.equal(host.scheduled.size, 1);
});

test("pending result publication holds library work until the job is settled", () => {
    const host = mockHost();
    enableSfxLauncher(host);
    const bridge = host.connect();
    const library = bridge.library;
    let libraryTicks = 0;
    const inventoryTick = library.tick;
    library.tick = function () { libraryTicks += 1; return inventoryTick.call(this); };
    host.failPublication(8);
    bridge.processJob(host.job("held-run-0001"));
    assert.ok(bridge.pendingReport);
    host.fireNext();
    assert.ok(bridge.pendingReport);
    assert.equal(libraryTicks, 0, "inventory cannot advance while terminal result publication is pending");
    host.fireNext();
    assert.equal(bridge.pendingReport, null);
    assert.equal(libraryTicks, 1);
    assert.equal(host.executionCount, 1);
});

test("reconnect creates a fresh request and ignores the old helper result", () => {
    const host = mockHost();
    enableSfxLauncher(host);
    const bridge = host.connect();
    const previousLibrary = bridge.library;
    bridge.stop();
    host.connect();
    const currentLibrary = bridge.library;
    assert.notEqual(currentLibrary, previousLibrary);
    assert.notEqual(currentLibrary.requestId, previousLibrary.requestId);
    assert.equal(previousLibrary.active, false);
    putSfxStatus(host, previousLibrary, successfulSfxStatus(host, previousLibrary, { count: 999 }));
    host.fireNext();
    assert.equal(currentLibrary.state.sfxCount, 0);
    assert.equal(currentLibrary.state.sfxState, "scanning");
    putSfxStatus(host, currentLibrary, successfulSfxStatus(host, currentLibrary, { count: 7 }));
    host.fireNext();
    assert.equal(currentLibrary.state.sfxCount, 7);
    assert.equal(currentLibrary.state.state, "ready");
});

test("deduplicated helper status can reuse a validated catalog from another session", () => {
    const host = mockHost();
    const library = directLibrary(host, true);
    const priorSession = "previous-session-0001";
    const priorRequest = "previous-request-0001";
    const catalogPath = ".ae-codex/library/sessions/" + priorSession + "/sfx-" + priorRequest + ".jsonl";
    host.put(aeWorkspace + "/" + catalogPath, '{"path":"D:/SFX/Boing.wav"}\n');
    putSfxStatus(host, library, successfulSfxStatus(host, library, {
        catalogSessionId: priorSession, catalogRequestId: priorRequest,
        catalogRelativePath: catalogPath, reusedCatalog: true, pendingArchiveCount: 3
    }));
    library.tick();
    const manifest = JSON.parse(host.textAt(library.root + "/current.json"));
    assert.equal(manifest.state, "ready");
    assert.equal(manifest.sfxRelativePath, catalogPath);
    assert.equal(manifest.sfxCatalogReused, true);
    assert.equal(manifest.sfxCatalogCached, false);
    assert.equal(manifest.pendingArchiveCount, 3);
    assert.ok(manifest.sfxSummaryRelativePath.includes(host.bridge.sessionNonce), "summary must belong to the current inventory request");
});

test("valid last SFX catalog remains discoverable when a fresh helper launch fails", () => {
    const host = mockHost();
    const priorSession = "cached-session-0001";
    const priorRequest = "cached-request-0001";
    const catalogPath = ".ae-codex/library/sessions/" + priorSession + "/sfx-" + priorRequest + ".jsonl";
    host.put(aeWorkspace + "/" + catalogPath, '{"path":"D:/SFX/Boing.wav"}\n');
    host.put(aeWorkspace + "/.ae-codex/library/latest-sfx.json", JSON.stringify({
        schemaVersion: 1, kind: "disk-sfx", sessionId: priorSession, requestId: priorRequest,
        count: 31, catalogRelativePath: catalogPath
    }));
    const library = directLibrary(host);
    library.tick();
    const manifest = JSON.parse(host.textAt(library.root + "/current.json"));
    assert.equal(manifest.state, "partial");
    assert.equal(manifest.sfxState, "error");
    assert.equal(manifest.sfxCount, 31);
    assert.equal(manifest.sfxRelativePath, catalogPath);
    assert.equal(manifest.sfxCatalogCached, true);
    assert.equal(host.textAt(aeWorkspace + "/" + catalogPath), '{"path":"D:/SFX/Boing.wav"}\n');
});

test("status schema and reused catalog paths must be valid before advertising SFX", () => {
    const invalid = [
        { schemaVersion: 2 },
        { kind: "other-inventory" },
        { catalogSessionId: "../outside", catalogRequestId: "prior-request-0001" },
        { catalogSessionId: "prior-session-0001", catalogRequestId: "prior-request-0001", catalogRelativePath: "D:/outside.jsonl" }
    ];
    for (const metadata of invalid) {
        const host = mockHost();
        const library = directLibrary(host, true);
        putSfxStatus(host, library, successfulSfxStatus(host, library, metadata));
        library.tick();
        assert.equal(library.state.state, "partial");
        assert.equal(library.state.sfxState, "error");
        assert.equal(library.state.sfxRelativePath, undefined);
        assert.equal(library.state.sfxCount, 0, "rejected catalog metadata must not change the advertised SFX count");
    }
});

test("bundle contains every inventoried branch and validates without executing edits", () => {
    const host = mockHost();
    const bundle = host.dollar.global.__codexAeBundleV1;
    const inventory = JSON.parse(fs.readFileSync(path.join(workspace, "source/script-inventory.json"), "utf8"));
    assert.deepEqual(Array.from(bundle.names), inventory.names);
    assert.equal(bundle.checked, 0);
    while (bundle.checked < bundle.names.length) { bundle.tick(); }
    assert.equal(bundle.status().state, "ready", bundle.describe());
    assert.equal(bundle.errors.length, 0);
    assert.equal(host.executionCount, 0);
    assert.equal(host.scheduled.size, 0, "checking cannot connect a stopped panel");
});

test("installation validation certificate is reused only for the current bundle", () => {
    const host = mockHost(), bundle = host.bridge.bundle;
    const certificatePath = aeWorkspace + "/.ae-codex/bundle/installed-validation.tsv";
    const fields = ["codex-ae-install/v1", bundle.revision, new host.File(bridgePath).length,
        bundle.names.length, bundle.moduleCount, "a".repeat(64)];
    host.put(certificatePath, fields.join("\t") + "\n");
    bundle.loadInstallation();
    assert.equal(bundle.installation.state, "verified");
    assert.equal(bundle.checked, 0, "reusing installation validation cannot rebuild every branch");
    for (const fieldIndex of [1, 2, 3, 4]) {
        const changed = fields.slice();
        changed[fieldIndex] = fieldIndex === 1 ? "b".repeat(64) : Number(changed[fieldIndex]) + 1;
        host.put(certificatePath, changed.join("\t") + "\n");
        bundle.loadInstallation();
        assert.notEqual(bundle.installation.state, "verified", "certificate field " + fieldIndex + " must match");
    }
    host.put(certificatePath, "malformed certificate\n");
    bundle.loadInstallation();
    assert.notEqual(bundle.installation.state, "verified");
    host.files.delete(certificatePath.toLowerCase());
    bundle.loadInstallation();
    assert.equal(bundle.installation.state, "missing");
    assert.equal(host.executionCount, 0);
});

test("merged runtime reconstructs all original branches exactly without executing them", () => {
    const { expandSource } = require("../tools/AeScriptSource.js");
    const source = JSON.parse(fs.readFileSync(path.join(workspace, "source/scripts.json"), "utf8"));
    const expanded = expandSource(source), originals = expanded.branches || expanded;
    const host = mockHost(), bundle = host.bridge.bundle;
    assert.equal(bundle.names.length, Object.keys(source.branches).length, "all historical entry names must survive consolidation");
    assert.deepEqual(Array.from(bundle.names), Object.keys(originals).sort());
    for (const name of bundle.names) {
        assert.equal(bundle.source(name), originals[name], "source changed while merging " + name);
    }
    const status = bundle.status();
    assert.equal(status.modules, Object.keys(bundle.modules).length);
    assert.ok(status.modules > 0, "the bundle must expose its merged modules");
    assert.ok(status.sharedModules > 0, "at least one source module must serve multiple branch names");
    assert.match(bundle.describe(), /script|branch/i, "panel description must identify the available script library");
    assert.equal(host.executionCount, 0);
    assert.equal(host.scheduled.size, 0);
});

test("merged recipes reject missing modules and slices outside decoded UTF-16 source", () => {
    const host = mockHost(), bundle = host.bridge.bundle;
    const name = "hello.jsx", originalRecipe = bundle.recipe;
    const id = originalRecipe.call(bundle, name).split("|")[0].split(":")[0];
    const text = bundle.moduleSource(id);
    let missing = id.replace(/\d/g, "9");
    while (Object.hasOwn(bundle.modules, missing)) { missing += "9"; }
    try {
        bundle.recipe = function () { return missing + ":0:1"; };
        assert.throws(() => bundle.source(name), /Bundle module missing/i);
        for (const slice of [id + ":" + text.length + ":1", id + ":0:" + (text.length + 1),
            id + ":-1:1", id + ":0:1:extra"]) {
            bundle.recipe = function () { return slice; };
            assert.throws(() => bundle.source(name), /Invalid module slice/i, slice);
        }
    } finally { bundle.recipe = originalRecipe; }
    assert.equal(host.executionCount, 0);
});

test("module slice offsets address decoded UTF-16 text including surrogate pairs", () => {
    const { checksum } = require("../tools/Build-AeScriptBundle.js");
    const host = mockHost(), bundle = host.bridge.bundle, name = "hello.jsx";
    const id = bundle.recipe(name).split("|")[0].split(":")[0];
    const expected = "\ud83c\udfac\u00e9", raw = "A" + expected + "Z";
    bundle.recipe = function () { return id + ":1:3"; };
    bundle.moduleSource = function () { return raw; };
    bundle.entries[name].sourceChecksum = checksum(encodeURIComponent(expected));
    assert.equal(bundle.source(name), expected);
    assert.equal(host.executionCount, 0);
});

test("ASCII JSON module records decode Unicode, control escapes and escaped comment endings", () => {
    const host = mockHost();
    const expected = "Ti\u1ebfng Vi\u1ec7t \ud83c\udfac\r\n\u0000\b\f\t\\\"*/";
    const record = JSON.stringify(expected).replace(/[\u007f-\uffff]/g,
        character => "\\u" + character.charCodeAt(0).toString(16).padStart(4, "0")).replace(/\*\//g, "*\\/");
    assert.match(record, /^[\x00-\x7f]*$/, "physical module records must remain ASCII");
    assert.equal(record.includes("*/"), false, "module contents cannot terminate the enclosing bundle comment");
    assert.equal(decodeInjectedModule(host, record), expected);
    assert.equal(decodeInjectedModule(host, '"\\u00e9\\uD83C\\uDFAC"'), "\u00e9\ud83c\udfac");
    assert.equal(decodeInjectedModule(host, '""'), "");
    assert.equal(host.executionCount, 0);
});

test("malformed JSON module strings fail strictly without evaluating injected code", () => {
    const host = mockHost();
    host.dollar.global.__MODULE_DECODER_EVAL__ = 0;
    const invalid = [
        '"raw\ncontrol"', '"raw\u0000control"', '"\\x41"', '"\\q"',
        'missing opening quote"', '"missing closing quote', '"ok"junk', '"ok" ',
        '"\\u123"', '"\\u12xz"', '"unfinished\\"',
        '"ok";$.global.__MODULE_DECODER_EVAL__=1;""'
    ];
    for (const record of invalid) {
        assert.throws(() => decodeInjectedModule(host, record), /Invalid module|Truncated module/i,
            "malformed physical module record was accepted: " + JSON.stringify(record));
        assert.equal(host.dollar.global.__MODULE_DECODER_EVAL__, 0, "record data must never be evaluated");
    }
    assert.equal(host.executionCount, 0);
});

test("changed reconstructed source cannot bypass the original branch checksum", () => {
    const host = mockHost(), bundle = host.bridge.bundle;
    const originalModuleSource = bundle.moduleSource;
    bundle.moduleSource = function (id) {
        const source = originalModuleSource.call(this, id);
        return source.replace(/[^\r\n]/g, "X");
    };
    assert.throws(() => bundle.source("hello.jsx"), /Branch source checksum mismatch/i);
    assert.throws(() => bundle.run("hello.jsx"), /Branch source checksum mismatch/i);
    assert.equal(host.executionCount, 0);
});

test("a recovered branch clears its previous validation error without duplicate stale reports", () => {
    const host = mockHost(), bundle = host.bridge.bundle, originalRead = bundle.readRecord;
    let failure = "temporary first branch read failure";
    bundle.readRecord = function (entry, name, isModule) {
        if (name === "hello.jsx" && failure) { throw new Error(failure); }
        return originalRead.call(this, entry, name, isModule);
    };
    assert.throws(() => bundle.run("hello.jsx"), /temporary first branch read failure/);
    assert.equal(bundle.entries["hello.jsx"].state, "error");
    assert.equal(bundle.status().state, "error");
    assert.equal(bundle.errors.length, 1);
    failure = "temporary second branch read failure";
    assert.throws(() => bundle.run("hello.jsx"), /temporary second branch read failure/);
    assert.equal(bundle.errors.length, 1, "repeated failures must update the branch's existing report");
    assert.match(bundle.errors[0], /temporary second branch read failure/);
    failure = "";
    assert.equal(bundle.run("hello.jsx"), "After Effects 26.5-test; unsaved project");
    assert.equal(bundle.entries["hello.jsx"].state, "ok");
    assert.equal(bundle.entries["hello.jsx"].error, "");
    assert.equal(bundle.errors.length, 0, "a recovered branch cannot remain in the panel error list");
    assert.equal(bundle.status().errors, 0);
    assert.notEqual(bundle.status().state, "error");
    assert.doesNotMatch(bundle.describe(), /Scripts ERROR/);
});

test("transient bundle read failure recovers even when the file stamp is unchanged", () => {
    const host = mockHost(), bundle = host.bridge.bundle, originalOpen = host.File.prototype.open;
    const stamp = bundle.fileStamp;
    host.File.prototype.open = function (mode) {
        if (this.fsName === bridgePath && mode === "r") { throw new Error("temporary bundle read failure"); }
        return originalOpen.call(this, mode);
    };
    assert.throws(() => bundle.refresh(true), /temporary bundle read failure/);
    assert.equal(bundle.status().state, "error");
    assert.equal(bundle.fileStamp, stamp);
    host.File.prototype.open = originalOpen;
    assert.equal(bundle.refresh(false), true, "the unchanged-stamp shortcut must not preserve a transient read error");
    assert.equal(bundle.fileStamp, stamp);
    assert.equal(bundle.error, "");
    assert.equal(bundle.status().errors, 0);
    assert.notEqual(bundle.status().state, "error");
    assert.equal(bundle.run("hello.jsx"), "After Effects 26.5-test; unsaved project");
});

test("bundled job executes once and preserves its return value when publication retries", () => {
    const host = mockHost(), bridge = host.connect(), bundle = bridge.bundle;
    let calls = 0;
    const run = bundle.run;
    bundle.run = function (name) { calls++; return run.call(this, name); };
    const job = host.job("bundle-job-0001");
    host.put(job.fsName, host.textAt(job.fsName).replace("test-job.jsx", "hello.jsx"));
    host.failPublication(3);
    bridge.processJob(job);
    while (bridge.pendingReport) { bridge.publishPendingReport(); }
    const status = JSON.parse(host.textAt(bridge.resultsPath + "/status-bundle-job-0001.json"));
    assert.equal(status.state, "success");
    assert.equal(status.result, "After Effects 26.5-test; unsaved project");
    assert.equal(calls, 1);
});

test("nested legacy evalFile calls route to bundled branches", () => {
    const host = mockHost(), bundle = host.bridge.bundle;
    assert.equal(bundle.evalFile(new host.File(aeWorkspace + "/jsx/hello.jsx")), "After Effects 26.5-test; unsaved project");
    assert.equal(vm.runInContext(bundle.prepare("$.evalFile(new File('" + aeWorkspace + "/jsx/hello.jsx'));"), host.context),
        "After Effects 26.5-test; unsaved project");
    assert.throws(() => bundle.evalFile(new host.File(aeWorkspace + "/jsx/missing.jsx")), /missing/);
    assert.throws(() => bundle.evalFile(new host.File(aeWorkspace + "/jsx/../hello.jsx")), /Invalid/);
});

test("live validation detects corrupt payload and selected branches refuse execution", () => {
    const host = mockHost(), bundle = host.bridge.bundle;
    const entry = bundle.entries["hello.jsx"], position = bundle.payloadOffset + entry.offset;
    const original = fs.readFileSync(path.join(workspace, "jsx/Codex Bridge.jsx"), "utf8");
    host.put(bridgePath, damageBundleByte(original, position));
    bundle.refresh(true);
    assert.throws(() => bundle.run("hello.jsx"), /checksum/);
    while (bundle.checked < bundle.names.length) { bundle.tick(); }
    assert.equal(bundle.status().state, "error");
    assert.match(bundle.errors.join("\n"), /hello\.jsx.*checksum/);
});

test("corrupt shared modules block every dependent branch and appear in live checks", () => {
    const host = mockHost(), bundle = host.bridge.bundle;
    const shared = Array.from(moduleUsers(bundle)).find(([, names]) => names.length >= 2);
    assert.ok(shared, "the merged bundle must physically share source across branch names");
    const [id, names] = shared, entry = bundle.modules[id];
    const original = fs.readFileSync(path.join(workspace, "jsx/Codex Bridge.jsx"), "utf8");
    host.put(bridgePath, damageBundleByte(original, bundle.payloadOffset + entry.offset));
    bundle.refresh(true);
    for (const name of names) {
        assert.throws(() => bundle.source(name), /checksum/i, name + " must detect damage in " + id);
    }
    assert.throws(() => bundle.run(names[0]), /checksum/i, "source must be verified before branch evaluation");
    while (bundle.checked < bundle.names.length) { bundle.tick(); }
    assert.equal(bundle.status().state, "error");
    for (const name of names) {
        assert.equal(bundle.entries[name].state, "error", name + " must fail live validation");
        assert.match(bundle.entries[name].error, /checksum/i);
    }
    assert.equal(host.executionCount, 0);
});

test("live validation rejects a truncated bundle and a damaged index", () => {
    for (const truncate of [true, false]) {
        const host = mockHost(), bundle = host.bridge.bundle;
        const original = fs.readFileSync(path.join(workspace, "jsx/Codex Bridge.jsx"), "utf8");
        const indexOffset = Number(original.split("\n", 3)[2].split("\t")[3]);
        host.put(bridgePath, truncate ? original.slice(0, -10) : original.slice(0, indexOffset) + "X" + original.slice(indexOffset + 1));
        assert.throws(() => bundle.refresh(true), /size|checksum/);
        assert.equal(bundle.status().state, "error");
        assert.throws(() => bundle.run("hello.jsx"));
    }
});

test("disposed script-status controls cannot interrupt the idle listener or inventory", () => {
    const host = mockHost(), bridge = host.connect(), bundle = bridge.bundle, library = bridge.library;
    let sourceReads = 0, libraryTicks = 0;
    bundle.source = function () { sourceReads++; throw new Error("idle source reconstruction is forbidden"); };
    const normalLibraryTick = library.tick;
    library.tick = function () { libraryTicks++; return normalLibraryTick.call(this); };
    Object.defineProperty(bridge.scriptsText, "text", {
        configurable: true, get() { throw new Error("mock disposed script status"); },
        set() { throw new Error("mock disposed script status"); }
    });
    for (let index = 0; index < 3; index++) { host.advanceTime(2200); host.fireNext(); }
    assert.equal(bridge.scriptsText, null);
    assert.equal(bridge.running, true);
    assert.equal(bridge.ready, true);
    assert.equal(bridge.connectionConnected, true);
    assert.equal(host.scheduled.size, 1);
    assert.equal(JSON.parse(host.textAt(bridge.heartbeatPath)).state, "running");
    assert.equal(bridge.library, library);
    assert.equal(libraryTicks, 3, "inventory must keep advancing after ScriptUI disposal");
    assert.equal(sourceReads, 0);
    assert.equal(host.executionCount, 0);
});

test("connected idle polling never decodes or compiles the full script library", () => {
    const host = mockHost(), bridge = host.connect(), bundle = bridge.bundle;
    let scanCalls = 0, sourceCalls = 0, compilationCalls = 0;
    bundle.tick = function () { scanCalls++; throw new Error("automatic branch scans are forbidden"); };
    bundle.source = function () { sourceCalls++; throw new Error("idle source reconstruction is forbidden"); };
    host.context.Function = function () { compilationCalls++; throw new Error("idle compilation is forbidden"); };
    host.job();
    host.fireNext();
    assert.equal(host.executionCount, 1);
    for (let index = 0; index < 12; index++) { host.fireNext(); }
    assert.equal(scanCalls, 0);
    assert.equal(sourceCalls, 0);
    assert.equal(compilationCalls, 0);
    assert.equal(bundle.checked, 0, "installation checks must not turn into recurring branch scans");
    bridge.stop(); host.advanceTime(300000);
    assert.equal(host.scheduled.size, 0);
});

test("source-only bootstrap initializes bundle without opening or stopping the live bridge", () => {
    const host = mockHost(), bridge = host.connect(), generation = bridge.generation;
    host.dollar.global.__CODEX_AE_BUNDLE_ONLY__ = true;
    host.dollar.evalFile(new host.File(bridgePath));
    delete host.dollar.global.__CODEX_AE_BUNDLE_ONLY__;
    assert.equal(host.bridge, bridge);
    assert.equal(bridge.generation, generation);
    assert.equal(bridge.running, true);
    assert.equal(host.dollar.global.__codexAeBundleV1.run("hello.jsx"), "After Effects 26.5-test; unsaved project");
});

let failures = 0;
test("function jobs call installed tools from data and never create JSX", () => {
    const host = mockHost(), bridge = host.connect(), runId = "function-read-0001";
    const request = { schema: "codex-ae-functions/v1", steps: [{ function: "system.info", args: {} }] };
    const jobPath = bridge.inboxPath + "/job-" + runId + ".job";
    host.put(jobPath, "schema=codex-ae-job/v2\nrunId=" + runId + "\nsessionNonce=" + bridge.sessionNonce + "\nrequest=" + encodeURIComponent(JSON.stringify(request)) + "\n");
    bridge.processJob(new host.File(jobPath));
    const status = JSON.parse(host.textAt(bridge.resultsPath + "/status-" + runId + ".json"));
    assert.equal(status.state, "success");
    const result = JSON.parse(status.result);
    assert.equal(result.results[0].function, "system.info");
    assert.equal(result.results[0].value.version, "26.5-test");
    assert.equal(host.executionCount, 0);
    assert.ok(host.writes.every(file => !/\.jsx$/i.test(file)), "tool requests cannot generate JSX files");
    assert.equal(host.dollar.global.__CODEX_AE_RUN_CONTEXT__, undefined);
});
test("function jobs execute once when terminal report publication fails", () => {
    const host = mockHost(), bridge = host.connect(), runId = "function-once-0001";
    let calls = 0;
    const normalRun = bridge.functions.run;
    bridge.functions.run = function (request, context) { calls++; return normalRun(request, context); };
    const jobPath = bridge.inboxPath + "/job-" + runId + ".job";
    host.put(jobPath, "schema=codex-ae-job/v2\nrunId=" + runId + "\nsessionNonce=" + bridge.sessionNonce + "\nrequest=" + encodeURIComponent(JSON.stringify({ schema: "codex-ae-functions/v1", steps: [{ function: "system.info", args: {} }] })) + "\n");
    host.failPublication(4);
    bridge.processJob(new host.File(jobPath));
    assert.equal(calls, 1); assert.ok(bridge.pendingReport);
    host.fireNext();
    assert.equal(calls, 1); assert.equal(bridge.pendingReport, null);
    assert.equal(JSON.parse(host.textAt(bridge.resultsPath + "/status-" + runId + ".json")).state, "success");
});
test("invalid function plans are rejected before execution without evaluating JSON code", () => {
    const invalid = [
        '{"schema":"codex-ae-functions/v1","steps":[{"function":"eval","args":{"code":"app.project.save()"}}]}',
        '{"schema":"codex-ae-functions/v1","steps":[],"steps":[]}',
        '{"schema":"codex-ae-functions/v1","steps":[{"function":"system.info","args":{"__proto__":{}}}]}',
        'app.project.save()',
        JSON.stringify({ schema: "codex-ae-functions/v1", steps: [{ function: "system.info", args: {} }, { function: "unknown.tool", args: {} }] })
    ];
    invalid.forEach((requestText, index) => {
        const host = mockHost(), bridge = host.connect(), runId = "invalid-function-000" + index;
        const jobPath = bridge.inboxPath + "/job-" + runId + ".job";
        host.put(jobPath, "schema=codex-ae-job/v2\nrunId=" + runId + "\nsessionNonce=" + bridge.sessionNonce + "\nrequest=" + encodeURIComponent(requestText) + "\n");
        bridge.functions.run = function () { throw new Error("invalid request must not execute"); };
        bridge.processJob(new host.File(jobPath));
        const status = JSON.parse(host.textAt(bridge.resultsPath + "/status-" + runId + ".json"));
        assert.equal(status.errorCode, "JOB_REJECTED");
        assert.equal(new host.File(bridge.resultsPath + "/started-" + runId + ".json").exists, false);
        assert.equal(host.executionCount, 0);
    });
});
test("function registry exposes every preserved branch without decoding source", () => {
    const host = mockHost(), bridge = host.connect();
    bridge.bundle.source = function () { throw new Error("listing must not decode source"); };
    assert.ok(bridge.functions.list().every(entry => !entry.legacy && entry.name !== "script.run"));
    const entries = bridge.functions.list(true);
    const legacy = entries.filter(entry => entry.legacy);
    assert.equal(legacy.length, bridge.bundle.names.length);
    assert.deepEqual(Array.from(legacy, entry => entry.branch), Array.from(bridge.bundle.names));
    assert.ok(entries.some(entry => entry.name === "layer.text.create" && !entry.legacy));
    assert.equal(JSON.parse(host.textAt(bridge.heartbeatPath)).functions.catalogRelativePath, ".ae-codex/functions/catalog.json");
});
for (const { name, run } of tests) {
    try { run(); console.log("PASS " + name); }
    catch (error) { failures += 1; console.error("FAIL " + name + "\n" + error.stack); }
}
console.log(`${tests.length - failures}/${tests.length} bridge tests passed`);
process.exitCode = failures ? 1 : 0;
