#target aftereffects
#targetengine "codexAeBridge"

/*
 * Codex AE Bridge
 *
 * Run this file once per After Effects session with:
 * File > Scripts > Run Script File...
 *
 * The bridge polls a local workspace inbox. It never evaluates request text;
 * it only loads reviewed bundle branches or direct .jsx files in jsx/.
 */
(function (thisObject) {
    // Direct-run fallback can load the dispatcher without creating/stopping a panel.
    if ($.global.__CODEX_AE_BUNDLE_ONLY__) { return; }
    var GLOBAL_NAME = "__codexAeBridgeV1";
    var BRIDGE_VERSION = "1.9.0";
    var WORKSPACE_ROOT = "C:/Users/nguye/AE_Codex";
    var existingBridge = $.global[GLOBAL_NAME];
    var autoStartOnly = !!$.global.__CODEX_AE_AUTOSTART_ONLY__;
    if (autoStartOnly && existingBridge && existingBridge.version === BRIDGE_VERSION) {
        // A Startup loader must not duplicate a listener or override manual Stop.
        return;
    }

    function trim(value) {
        return String(value).replace(/^\s+|\s+$/g, "");
    }

    function normalizePath(value) {
        return String(value).replace(/\\/g, "/").toLowerCase();
    }

    function jsonEscape(value) {
        var input = String(value);
        var output = "";
        var index;

        for (index = 0; index < input.length; index += 1) {
            var character = input.charAt(index);
            var code = input.charCodeAt(index);
            var hex;

            if (character === "\\") {
                output += "\\\\";
            } else if (character === "\"") {
                output += "\\\"";
            } else if (character === "\b") {
                output += "\\b";
            } else if (character === "\f") {
                output += "\\f";
            } else if (character === "\n") {
                output += "\\n";
            } else if (character === "\r") {
                output += "\\r";
            } else if (character === "\t") {
                output += "\\t";
            } else if (code < 32) {
                hex = code.toString(16);
                while (hex.length < 4) {
                    hex = "0" + hex;
                }
                output += "\\u" + hex;
            } else {
                output += character;
            }
        }

        return output;
    }

    function Bridge(workspaceRoot) {
        this.version = BRIDGE_VERSION;
        this.workspaceRoot = workspaceRoot;
        this.bridgeRoot = workspaceRoot + "/.ae-codex/bridge";
        this.inboxPath = this.bridgeRoot + "/inbox";
        this.resultsPath = this.bridgeRoot + "/results";
        this.heartbeatPath = this.bridgeRoot + "/heartbeat.json";
        this.running = false;
        this.ready = false;
        this.busy = false;
        this.taskId = 0;
        this.startupStep = 0;
        this.generation = 0;
        this.lastHeartbeat = 0;
        this.lastStatus = "Starting bridge...";
        this.progressValue = 0;
        this.progressLabel = "Loading";
        this.hideProgressPending = false;
        this.pendingReport = null;
        this.pendingCleanupFile = null;
        this.sessionNonce = String(new Date().getTime()) + "-" +
            Math.floor(Math.random() * 2147483647).toString(16);
        this.window = null;
        this.statusText = null;
        this.connectionText = null;
        this.connectionConnected = false;
        this.modelText = null;
        this.modelDisplayValue = "";
        this.lastModelRefresh = 0;
        this.progressGroup = null;
        this.progressText = null;
        this.progressBar = null;
        this.library = null;
        this.libraryText = null;
        this.libraryDisplayValue = "";
        this.bundle = $.global.__codexAeBundleV1;
        this.functions = $.global.__codexAeFunctionsV1;
        this.scriptsText = null;
        this.logs = [];
        this.logEntries = this.logs;
        this.logView = null;
        this.logNotices = {};
        this.logWriteError = "";
    }

    Bridge.prototype.refreshLog = function () {
        var lines = [], i, entry;
        try {
            if (!this.logView) { return; }
            for (i = 0; i < this.logs.length; i += 1) {
                entry = this.logs[i];
                lines.push(entry.time + " [" + entry.level.toUpperCase() + "] " +
                    (entry.runId ? entry.runId + " | " : "") +
                    (typeof entry.percent === "number" ? entry.percent + "% | " : "") + entry.message);
            }
            this.logView.text = lines.join("\n");
            this.logView.helpTip = this.logWriteError || "Latest 200 events. Disk log: .ae-codex/bridge/logs/events.log";
            if (this.window && this.window.update) { this.window.update(); }
        } catch (logUiError) { this.logView = null; }
    };

    Bridge.prototype.persistLog = function (entry) {
        var file = null, previous, opened = false;
        try {
            if (!(new Folder(this.workspaceRoot)).exists) { throw new Error("Workspace unavailable"); }
            this.ensureFolders();
            this.ensureFolder(this.bridgeRoot + "/logs");
            file = new File(this.bridgeRoot + "/logs/events.log");
            if (file.exists && file.length >= 262144) {
                previous = new File(this.bridgeRoot + "/logs/previous.log");
                if (previous.exists && !previous.remove()) { throw new Error(previous.error); }
                if (!file.rename("previous.log")) { throw new Error(file.error); }
                file = new File(this.bridgeRoot + "/logs/events.log");
            }
            file.encoding = "UTF-8";
            if (!file.open("a")) { throw new Error(file.error); }
            opened = true;
            if (!file.write("{\"time\":\"" + jsonEscape(entry.time) + "\",\"epochMs\":" + entry.epochMs +
                    ",\"level\":\"" + jsonEscape(entry.level) + "\",\"runId\":\"" + jsonEscape(entry.runId) +
                    "\",\"message\":\"" + jsonEscape(entry.message) + "\"" +
                    (typeof entry.percent === "number" ? ",\"percent\":" + entry.percent : "") + "}\n")) {
                throw new Error(file.error);
            }
            this.logWriteError = "";
        } catch (logFileError) {
            this.logWriteError = "Disk log unavailable: " + String(logFileError);
        } finally {
            if (opened) { try { file.close(); } catch (logCloseError) {} }
        }
    };

    Bridge.prototype.log = function (level, message, runId, percent) {
        // Logging must never affect script execution or result publication.
        try {
            var now = new Date(), pad = function (n) { return n < 10 ? "0" + n : String(n); };
            var entry = {
                time: pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds()),
                epochMs: now.getTime(), level: String(level || "info").toLowerCase(),
                message: String(message || "").substring(0, 1000), runId: String(runId || "").substring(0, 80)
            };
            if (typeof percent === "number" && isFinite(percent)) { entry.percent = Math.max(0, Math.min(100, Math.round(percent))); }
            this.logs.push(entry);
            if (this.logs.length > 200) { this.logs.splice(0, this.logs.length - 200); }
            this.persistLog(entry);
            this.refreshLog();
        } catch (logError) {}
    };
    Bridge.prototype.appendLog = Bridge.prototype.log;
    Bridge.prototype.clearLog = function () { this.logs.splice(0, this.logs.length); this.refreshLog(); };
    Bridge.prototype.logOnce = function (key, level, message, runId) {
        if (this.logNotices[key] !== message) {
            this.logNotices[key] = message;
            this.log(level, message, runId);
        }
    };

    Bridge.prototype.refreshScriptsDisplay = function () {
        try {
            if (this.scriptsText) {
                this.scriptsText.text = "Tools: " + this.functions.list(false).length + " reusable functions\n" + this.bundle.describe();
                this.scriptsText.helpTip = this.bundle.errors.length ? this.bundle.errors.join("\n") :
                    "Full validation is recorded once at installation/update. Each requested branch is checksum-checked on demand; no background script scan.";
            }
        } catch (disposedScriptsUiError) { this.scriptsText = null; }
    };

    Bridge.prototype.showScripts = function () {
        var dialog = new Window("dialog", "Legacy archive - " + this.bundle.names.length + " historical scripts");
        var bundle = this.bundle;
        var search = dialog.add("edittext", undefined, "");
        var list = dialog.add("listbox", undefined, []);
        var detail = dialog.add("statictext", undefined, "", { multiline: true });
        var close = dialog.add("button", undefined, "Close", { name: "ok" });
        dialog.orientation = "column"; dialog.alignChildren = ["fill", "top"];
        search.helpTip = "Filter branch names";
        list.preferredSize = [560, 320]; detail.preferredSize = [560, 64];
        function fill() {
            var i, name, entry, item, query = String(search.text).toLowerCase();
            list.removeAll();
            for (i = 0; i < bundle.names.length; i += 1) {
                name = bundle.names[i]; entry = bundle.entries[name];
                if (name.toLowerCase().indexOf(query) < 0) { continue; }
                item = list.add("item", "[" + (entry.state === "pending" && bundle.installation.state === "verified" ?
                    "installed OK" : entry.state) + "] " + name); item.branchName = name;
            }
        }
        search.onChanging = fill;
        list.onChange = function () {
            var entry = list.selection ? bundle.entries[list.selection.branchName] : null;
            if (!entry) { detail.text = ""; return; }
            try {
                detail.text = entry.error || "Shared source pieces: " + bridge.bundle.recipe(list.selection.branchName).split("|").length +
                    "\nDependencies: " + (entry.dependencies.join(", ") || "none");
            } catch (recipeError) { detail.text = String(recipeError); }
        };
        fill(); dialog.center(); dialog.show();
    };

    Bridge.prototype.showFunctions = function () {
        var dialog = new Window("dialog", "Installed reusable tools - " + this.functions.list(false).length);
        var search = dialog.add("edittext", undefined, "");
        var list = dialog.add("listbox", undefined, []);
        var detail = dialog.add("edittext", undefined, "", { multiline: true, readonly: true, scrolling: true });
        var descriptors = this.functions.list(false);
        dialog.orientation = "column"; dialog.alignChildren = ["fill", "top"];
        search.helpTip = "Search reusable tools with parameters. Historical project scripts are kept separately in Archive.";
        list.preferredSize = [560, 280]; detail.preferredSize = [560, 180];
        dialog.add("button", undefined, "Close", { name: "ok" });
        function fill() {
            var i, entry, item, query = String(search.text).toLowerCase(), label;
            list.removeAll();
            for (i = 0; i < descriptors.length; i += 1) {
                entry = descriptors[i]; label = entry.legacy ? "script.run / " + entry.branch : entry.name;
                if ((label + " " + entry.description).toLowerCase().indexOf(query) < 0) { continue; }
                item = list.add("item", label); item.descriptorIndex = i;
            }
        }
        search.onChanging = fill;
        list.onChange = function () {
            var entry = list.selection ? descriptors[list.selection.descriptorIndex] : null;
            detail.text = entry ? entry.description + "\n\n" + bridge.functions.stringify({
                "function": entry.name, args: entry.args || {}, legacy: !!entry.legacy
            }) : "";
        };
        fill(); dialog.center(); dialog.show();
    };

    Bridge.prototype.beginLibrary = function () {
        try {
            this.bundle.run("Codex Library.jsx");
            if (typeof $.global.__codexAeLibraryFactoryV1 !== "function") {
                throw new Error("Library module did not load");
            }
            this.library = $.global.__codexAeLibraryFactoryV1(this);
            this.library.begin(this.generation);
        } catch (libraryError) {
            this.library = null;
            this.libraryDisplayValue = "Library unavailable: " + String(libraryError);
            if (this.libraryText) { this.libraryText.text = this.libraryDisplayValue; }
            this.log("error", this.libraryDisplayValue);
        }
        this.refreshLibraryDisplay();
    };

    Bridge.prototype.refreshLibraryDisplay = function () {
        var display = this.library ? this.library.describe() :
            (this.libraryDisplayValue || "Library: connect to scan effects and SFX");
        try {
            if (this.libraryText && this.libraryText.text !== display) {
                this.libraryText.text = display;
                if (this.window) { this.window.layout.layout(true); }
            }
        } catch (libraryUiError) { this.libraryText = null; }
    };

    Bridge.prototype.refreshModelDisplay = function () {
        var file = new File(this.workspaceRoot + "/.ae-codex/model-display.txt");
        var contents = "";
        var match;
        var text = "Codex model: unknown (run model sync)";
        this.lastModelRefresh = new Date().getTime();
        if (file.exists && file.length < 2048) {
            file.encoding = "UTF-8";
            if (file.open("r")) {
                try {
                    contents = file.read();
                } finally {
                    file.close();
                }
                match = contents.match(/(?:^|\n)model=([A-Za-z0-9._-]{1,100})(?:\r?\n|$)/);
                if (contents.indexOf("schema=codex-model-display/v1") === 0 && match) {
                    text = "Codex model: " + match[1] + " (default)";
                }
            }
        }
        try {
            if (this.modelText && this.modelDisplayValue !== text) {
                this.modelText.text = text;
                this.modelDisplayValue = text;
                if (this.window) {
                    this.window.layout.layout(true);
                }
            }
        } catch (disposedModelUiError) {
            this.modelText = null;
        }
    };

    Bridge.prototype.ensureFolder = function (path) {
        var folder = new Folder(path);
        if (!folder.exists && !folder.create()) {
            throw new Error("Cannot create bridge folder: " + path + "; " + folder.error);
        }
        return folder;
    };

    Bridge.prototype.ensureFolders = function () {
        this.ensureFolder(this.workspaceRoot + "/.ae-codex");
        this.ensureFolder(this.bridgeRoot);
        this.ensureFolder(this.inboxPath);
        this.ensureFolder(this.resultsPath);
    };

    Bridge.prototype.writeAtomic = function (path, text) {
        var destination = new File(path);
        var temporary = new File(path + ".tmp");
        var attempt;
        var lastError = "unknown file error";

        for (attempt = 0; attempt < 4; attempt += 1) {
            try {
                if (temporary.exists && !temporary.remove()) {
                    throw new Error("Cannot clear temporary file: " + temporary.error);
                }

                temporary.encoding = "UTF-8";
                if (!temporary.open("w")) {
                    throw new Error("Cannot open temporary file: " + temporary.error);
                }
                try {
                    temporary.write(text);
                } finally {
                    temporary.close();
                }

                if (destination.exists && !destination.remove()) {
                    throw new Error("Cannot replace destination: " + destination.error);
                }
                if (!temporary.rename(destination.name)) {
                    throw new Error("Cannot publish temporary file: " + temporary.error);
                }
                return;
            } catch (writeError) {
                lastError = String(writeError);
                if (temporary.opened) {
                    temporary.close();
                }
                if (attempt < 3) {
                    $.sleep(35 * (attempt + 1));
                }
            }
        }

        throw new Error("Atomic write failed for " + destination.fsName + ": " + lastError);
    };

    Bridge.prototype.writeNewAtomic = function (path, text) {
        var destination = new File(path);
        var temporary = new File(path + ".tmp-" + this.sessionNonce);
        var attempt;
        var lastError = "unknown file error";

        if (destination.exists) {
            throw new Error("Refusing to replace immutable result: " + destination.fsName);
        }

        for (attempt = 0; attempt < 4; attempt += 1) {
            try {
                if (temporary.exists && !temporary.remove()) {
                    throw new Error("Cannot clear temporary result: " + temporary.error);
                }

                temporary.encoding = "UTF-8";
                if (!temporary.open("w")) {
                    throw new Error("Cannot open temporary result: " + temporary.error);
                }
                try {
                    temporary.write(text);
                } finally {
                    temporary.close();
                }

                if (destination.exists) {
                    throw new Error("Immutable result appeared while publishing");
                }
                if (!temporary.rename(destination.name)) {
                    throw new Error("Cannot publish immutable result: " + temporary.error);
                }
                return;
            } catch (writeError) {
                lastError = String(writeError);
                if (temporary.opened) {
                    temporary.close();
                }
                if (destination.exists) {
                    throw new Error("Refusing to replace immutable result: " + destination.fsName);
                }
                if (attempt < 3) {
                    $.sleep(35 * (attempt + 1));
                }
            }
        }

        throw new Error("Immutable result write failed for " + destination.fsName + ": " + lastError);
    };

    Bridge.prototype.setConnectionStatus = function (connected, detail) {
        this.connectionConnected = connected;
        try {
            if (this.connectionText) {
                this.connectionText.text = (connected ? "\uD83D\uDC4D LIKE - " : "\uD83D\uDC4E DISLIKE - ") + detail;
                this.connectionText.graphics.foregroundColor = this.connectionText.graphics.newPen(
                    this.connectionText.graphics.PenType.SOLID_COLOR,
                    connected ? [0.25, 0.85, 0.40, 1] : [1, 0.40, 0.35, 1], 1
                );
            }
        } catch (disposedConnectionUiError) {
            this.connectionText = null;
        }
    };

    Bridge.prototype.setUiStatus = function (text) {
        this.lastStatus = String(text);
        try {
            if (this.statusText) {
                this.statusText.text = this.lastStatus;
                if (this.window) {
                    this.window.layout.layout(true);
                }
            }
        } catch (disposedUiError) {
            // Closing a docked ScriptUI panel can dispose its controls while
            // the named engine and polling task continue to live.
            this.window = null;
            this.statusText = null;
            this.progressGroup = null;
            this.progressText = null;
            this.progressBar = null;
        }
    };

    Bridge.prototype.setProgress = function (value, label) {
        var normalizedValue = Math.max(0, Math.min(100, Math.round(Number(value))));
        if (!isFinite(normalizedValue)) { normalizedValue = 0; }
        this.progressValue = normalizedValue;
        this.progressLabel = String(label || "Loading");

        try {
            if (this.progressBar) {
                this.progressBar.value = normalizedValue;
            }
            if (this.progressText) {
                this.progressText.text = this.progressLabel + " - " + normalizedValue + "%";
            }
            if (this.window) {
                this.window.layout.layout(true);
                if (this.window.layout.resize) {
                    this.window.layout.resize();
                }
                if (this.window.update) {
                    this.window.update();
                }
            }
        } catch (disposedUiError) {
            this.window = null;
            this.statusText = null;
            this.progressGroup = null;
            this.progressText = null;
            this.progressBar = null;
        }
    };

    Bridge.prototype.showProgress = function () {
        try {
            if (this.progressGroup) {
                this.progressGroup.visible = true;
            }
            if (this.progressText) {
                this.progressText.visible = true;
            }
            if (this.progressBar) {
                this.progressBar.visible = true;
            }
            if (this.window) {
                this.window.layout.layout(true);
                if (this.window.layout.resize) {
                    this.window.layout.resize();
                }
                if (this.window.update) {
                    this.window.update();
                }
            }
        } catch (disposedUiError) {
            this.window = null;
            this.statusText = null;
            this.progressGroup = null;
            this.progressText = null;
            this.progressBar = null;
        }
    };

    Bridge.prototype.hideProgress = function () {
        try {
            if (this.progressGroup) {
                this.progressGroup.visible = false;
            }
            if (this.progressText) {
                this.progressText.visible = false;
            }
            if (this.progressBar) {
                this.progressBar.visible = false;
            }
            if (this.window) {
                this.window.layout.layout(true);
                if (this.window.layout.resize) {
                    this.window.layout.resize();
                }
                if (this.window.update) {
                    this.window.update();
                }
            }
        } catch (disposedUiError) {
            this.window = null;
            this.statusText = null;
            this.progressGroup = null;
            this.progressText = null;
            this.progressBar = null;
        }
    };

    Bridge.prototype.writeHeartbeat = function (state, message) {
        var now = new Date().getTime();
        var payload = "{" +
            "\"schema\":\"codex-ae-heartbeat/v1\"," +
            "\"state\":\"" + jsonEscape(state) + "\"," +
            "\"bridgeVersion\":\"" + jsonEscape(BRIDGE_VERSION) + "\"," +
            "\"startupPercent\":" + this.progressValue + "," +
            "\"startupStage\":\"" + jsonEscape(this.progressLabel) + "\"," +
            "\"sessionNonce\":\"" + jsonEscape(this.sessionNonce) + "\"," +
            "\"timestampEpochMs\":" + now + "," +
            "\"afterEffectsVersion\":\"" + jsonEscape(app.version) + "\"," +
            "\"functions\":{\"schema\":\"codex-ae-functions/v1\",\"catalogRelativePath\":\".ae-codex/functions/catalog.json\"}," +
            "\"message\":\"" + jsonEscape(message || "") + "\"" +
            (this.library && $.global.__codexAeLibraryJsonV1 ?
                ",\"library\":" + $.global.__codexAeLibraryJsonV1(this.library.heartbeat()) : "") +
            (this.bundle && $.global.__codexAeLibraryJsonV1 ?
                ",\"scripts\":" + $.global.__codexAeLibraryJsonV1(this.bundle.status()) : "") +
            "}";

        this.writeAtomic(this.heartbeatPath, payload);
        this.lastHeartbeat = now;
        this.setConnectionStatus(state === "running" && this.running && this.ready,
            state === "running" ? "Connected / Ready for Codex" :
                (state === "starting" ? "Connecting..." :
                    (state === "stopped" ? "Disconnected" : "Connection error")));
    };

    Bridge.prototype.writeStarted = function (runId, operation, startedAt) {
        var now = new Date().getTime();
        var path = this.resultsPath + "/started-" + runId + ".json";
        var payload = "{" +
            "\"schema\":\"codex-ae-run-started/v1\"," +
            "\"mode\":\"file-bridge\"," +
            "\"runId\":\"" + jsonEscape(runId) + "\"," +
            "\"sessionNonce\":\"" + jsonEscape(this.sessionNonce) + "\"," +
            "\"state\":\"running\"," +
            "\"phase\":\"evaluating\"," +
            "\"operation\":\"" + jsonEscape(operation || "") + "\"," +
            "\"afterEffectsVersion\":\"" + jsonEscape(app.version) + "\"," +
            "\"startedAtEpochMs\":" + startedAt + "," +
            "\"timestampEpochMs\":" + now +
            "}";

        this.writeNewAtomic(path, payload);
    };

    Bridge.prototype.writeStatus = function (report) {
        var now = new Date().getTime();
        var path = this.resultsPath + "/status-" + report.runId + ".json";
        var payload = "{" +
            "\"schema\":\"codex-ae-run/v2\"," +
            "\"mode\":\"file-bridge\"," +
            "\"runId\":\"" + jsonEscape(report.runId) + "\"," +
            "\"sessionNonce\":\"" + jsonEscape(this.sessionNonce) + "\"," +
            "\"state\":\"" + jsonEscape(report.state) + "\"," +
            "\"phase\":\"" + jsonEscape(report.phase) + "\"," +
            "\"errorCode\":\"" + jsonEscape(report.errorCode || "") + "\"," +
            "\"retryable\":" + (report.retryable ? "true" : "false") + "," +
            "\"completionKnown\":" + (report.completionKnown ? "true" : "false") + "," +
            "\"operation\":\"" + jsonEscape(report.operation || "") + "\"," +
            "\"afterEffectsVersion\":\"" + jsonEscape(app.version) + "\"," +
            "\"startedAtEpochMs\":" + report.startedAt + "," +
            "\"timestampEpochMs\":" + now + "," +
            "\"message\":\"" + jsonEscape(report.message || "") + "\"," +
            "\"result\":\"" + jsonEscape(report.result || "") + "\"" +
            "}";

        this.writeNewAtomic(path, payload);
    };

    Bridge.prototype.describeError = function (error) {
        var description = error && error.toString ? error.toString() : String(error);
        if (error && error.line) {
            description += " (line " + error.line + ")";
        }
        if (error && error.fileName) {
            description += " in " + error.fileName;
        }
        return description;
    };

    Bridge.prototype.publishPendingReport = function () {
        var report = this.pendingReport;
        var cleanupWarning = "";

        if (!report) {
            return true;
        }

        try {
            this.writeStatus(report);
            this.pendingReport = null;
            this.logNotices.report = "";
            this.log("info", "Result report published: " + report.state, report.runId);

            if (report.runningFile && report.runningFile.exists && !report.runningFile.remove()) {
                cleanupWarning = "\nResult published; job cleanup failed: " + report.runningFile.error;
                this.pendingCleanupFile = report.runningFile;
                this.logOnce("cleanup", "error", cleanupWarning, report.runId);
            } else {
                this.pendingCleanupFile = null;
            }
            this.busy = this.pendingCleanupFile !== null;

            if (report.state === "success") {
                this.setUiStatus(
                    "Completed " + report.operation + "\nRun ID: " + report.runId + cleanupWarning
                );
            } else {
                this.setUiStatus(
                    "Failed " + report.operation + "\n" + report.message + cleanupWarning
                );
            }
            return true;
        } catch (statusError) {
            this.busy = true;
            this.logOnce("report", "error", "Result publication failed; retrying report only: " + this.describeError(statusError), report.runId);
            this.setUiStatus(
                "JSX finished; reporting result will retry\n" + String(statusError)
            );
            return false;
        }
    };

    Bridge.prototype.retryPendingCleanup = function () {
        var file = this.pendingCleanupFile;

        if (!file) {
            return true;
        }
        if (!file.exists || file.remove()) {
            this.pendingCleanupFile = null;
            this.busy = this.pendingReport !== null;
            this.setUiStatus("Result published and job cleanup completed");
            this.logNotices.cleanup = "";
            this.log("info", "Job marker cleanup completed");
            return true;
        }

        this.busy = true;
        this.logOnce("cleanup", "error", "Job marker cleanup failed; retrying: " + file.error);
        this.setUiStatus("Result published; waiting to clean job marker\n" + file.error);
        return false;
    };

    Bridge.prototype.readJob = function (jobFile) {
        var values = {};
        var fieldCount = 0;

        if (jobFile.length > 800 * 1024) {
            throw new Error("Job request is too large");
        }

        jobFile.encoding = "UTF-8";
        if (!jobFile.open("r")) {
            throw new Error("Cannot read job: " + jobFile.fsName + "; " + jobFile.error);
        }

        try {
            while (!jobFile.eof) {
                var line = jobFile.readln();
                if (trim(line) === "") {
                    continue;
                }

                var separator = line.indexOf("=");
                if (separator < 1) {
                    throw new Error("Invalid job line: " + line);
                }

                var key = trim(line.substring(0, separator));
                var value = trim(line.substring(separator + 1));
                if (key !== "schema" && key !== "runId" && key !== "sessionNonce" && key !== "script" && key !== "request") {
                    throw new Error("Unknown job field: " + key);
                }
                if (typeof values[key] !== "undefined") {
                    throw new Error("Duplicate job field: " + key);
                }
                values[key] = value;
                fieldCount += 1;
            }
        } finally {
            jobFile.close();
        }

        if (fieldCount !== 4) {
            throw new Error("Job must contain exactly schema, runId, sessionNonce, and script or request");
        }

        return values;
    };

    Bridge.prototype.validateJob = function (jobFile, job) {
        if (job.schema !== "codex-ae-job/v1" && job.schema !== "codex-ae-job/v2") {
            throw new Error("Unsupported job schema");
        }

        if (!/^[A-Za-z0-9-]{8,80}$/.test(job.runId || "")) {
            throw new Error("Invalid run ID");
        }

        if (jobFile.name !== "job-" + job.runId + ".job") {
            throw new Error("Job filename does not match run ID");
        }

        if (job.schema === "codex-ae-job/v2") {
            if (typeof job.request !== "string" || typeof job.script !== "undefined") {
                throw new Error("Function jobs require request data and cannot contain a script path");
            }
            var requestText = decodeURIComponent(job.request), request, names = [], stepIndex;
            if (requestText.length > 131072 || encodeURIComponent(requestText).replace(/%[A-Fa-f0-9]{2}|./g, "x").length > 131072) {
                throw new Error("Function request exceeds 128 KiB");
            }
            request = this.functions.parse(requestText);
            this.bundle.refresh(false);
            this.functions.validate(request);
            for (stepIndex = 0; stepIndex < request.steps.length; stepIndex += 1) { names.push(request.steps[stepIndex]["function"]); }
            return { name: "functions: " + names.join(", "), functionRequest: request };
        }
        if (typeof job.script !== "string" || typeof job.request !== "undefined" || jobFile.length > 4096) {
            throw new Error("Legacy jobs require a script path only, up to 4096 bytes");
        }

        var relativePath = String(job.script || "").replace(/\\/g, "/");
        if (!/^jsx\/[^\/]+\.jsx$/i.test(relativePath)) {
            throw new Error("Only direct .jsx files inside jsx/ are allowed");
        }

        if (/[:*?\"<>|\x00-\x1F]/.test(relativePath)) {
            throw new Error("Script path contains invalid characters");
        }

        var segments = relativePath.split("/");
        var index;
        for (index = 0; index < segments.length; index += 1) {
            if (segments[index] === "" || segments[index] === "." || segments[index] === "..") {
                throw new Error("Script path traversal is not allowed");
            }
        }

        var jsxFolder = new Folder(this.workspaceRoot + "/jsx");
        var jsxRoot = normalizePath(jsxFolder.fsName);
        var targetFile = new File(this.workspaceRoot + "/" + relativePath);
        var targetPath = normalizePath(targetFile.fsName);

        if (jsxFolder.alias || targetFile.alias) {
            throw new Error("Aliases, shortcuts, and symbolic links are not allowed");
        }

        if (normalizePath(targetFile.parent.fsName) !== jsxRoot ||
                targetPath.indexOf(jsxRoot + "/") !== 0) {
            throw new Error("Script resolves outside the jsx folder");
        }

        this.bundle.refresh(false);
        if (this.bundle.has(targetFile.name)) { return { name: targetFile.name, bundleBranch: true }; }
        if (!targetFile.exists) {
            throw new Error("Script does not exist: " + relativePath);
        }

        return targetFile;
    };

    Bridge.prototype.rejectJob = function (jobFile, error, job) {
        var rejectedName = jobFile.name + ".rejected-" + new Date().getTime();
        jobFile.rename(rejectedName);
        this.setUiStatus("Rejected job: " + String(error));
        this.log("error", "Rejected job: " + this.describeError(error), job ? job.runId : "");

        if (job && job.sessionNonce === this.sessionNonce &&
                /^[A-Za-z0-9-]{8,80}$/.test(job.runId || "")) {
            this.pendingReport = {
                runId: job.runId,
                state: "error",
                phase: "validation",
                errorCode: "JOB_REJECTED",
                retryable: false,
                completionKnown: true,
                operation: job.schema === "codex-ae-job/v2" ? "function plan" : (job.script || "unknown JSX"),
                startedAt: new Date().getTime(),
                message: this.describeError(error),
                result: "",
                runningFile: null
            };
            this.busy = true;
            this.publishPendingReport();
        }
    };

    Bridge.prototype.processJob = function (jobFile) {
        var job;
        var targetFile;

        try {
            job = this.readJob(jobFile);
            if (job.sessionNonce !== this.sessionNonce) {
                // Another AE instance owns this job. Leave it untouched so the
                // matching bridge can claim it.
                return;
            }
            targetFile = this.validateJob(jobFile, job);
        } catch (validationError) {
            this.rejectJob(jobFile, validationError, job);
            return;
        }

        var runningName = "job-" + job.runId + ".running";
        if (!jobFile.rename(runningName)) {
            this.setUiStatus("Could not claim job " + job.runId + ": " + jobFile.error);
            this.logOnce("claim", "error", "Could not claim job " + job.runId + ": " + jobFile.error, job.runId);
            return;
        }
        this.logNotices.claim = "";

        var runningFile = new File(this.inboxPath + "/" + runningName);
        var startedAt = new Date().getTime();
        var report;
        var evaluationResult;
        var executionDescription = "";
        var executionSucceeded = false;
        var controller = this, contextActive = true;
        this.busy = true;
        this.hideProgressPending = false;
        this.showProgress();
        this.setProgress(0, "Running " + targetFile.name);
        this.log("info", "Started " + targetFile.name, job.runId);
        this.setUiStatus("Running " + targetFile.name + "\nRun ID: " + job.runId);

        try {
            // If this preflight write fails, the target is not executed.
            this.writeStarted(job.runId, targetFile.name, startedAt);
        } catch (preflightError) {
            this.log("error", "Job preflight failed: " + this.describeError(preflightError), job.runId);
            this.setProgress(0, "Preflight failed");
            this.pendingReport = {
                runId: job.runId,
                state: "error",
                phase: "preflight",
                errorCode: "START_STATUS_FAILED",
                retryable: true,
                completionKnown: true,
                operation: targetFile.name,
                startedAt: startedAt,
                message: this.describeError(preflightError),
                result: "",
                runningFile: runningFile
            };
            this.publishPendingReport();
            return;
        }

        try {
            $.global.__CODEX_AE_RUN_CONTEXT__ = {
                schema: "codex-ae-context/v1",
                runId: job.runId,
                workspaceRoot: this.workspaceRoot,
                progress: function (percent, message) {
                    if (!contextActive || !isFinite(Number(percent))) { return; }
                    controller.setProgress(percent, message || targetFile.name);
                    controller.log("progress", message || targetFile.name, job.runId, Number(percent));
                },
                log: function (message, level) {
                    if (contextActive) { controller.log(level === "error" || level === "warning" ? level : "info", message, job.runId); }
                }
            };

            if (targetFile.functionRequest) {
                evaluationResult = this.functions.stringify(this.functions.run(targetFile.functionRequest, $.global.__CODEX_AE_RUN_CONTEXT__));
            } else {
                evaluationResult = targetFile.bundleBranch ? this.bundle.run(targetFile.name) : $.evalFile(targetFile);
            }
            executionSucceeded = true;
        } catch (executionError) {
            executionDescription = this.describeError(executionError);
        } finally {
            contextActive = false;
            try {
                delete $.global.__CODEX_AE_RUN_CONTEXT__;
            } catch (contextError) {
                $.global.__CODEX_AE_RUN_CONTEXT__ = null;
            }
        }

        if (executionSucceeded) {
            this.setProgress(100, "Completed " + targetFile.name);
            this.log("info", "Completed successfully: " + targetFile.name, job.runId, 100);
            this.hideProgressPending = true;
        } else {
            this.setProgress(this.progressValue, "Failed " + targetFile.name);
            this.log("error", executionDescription, job.runId);
        }

        report = {
            runId: job.runId,
            state: executionSucceeded ? "success" : "error",
            phase: executionSucceeded ? "completed" : "evaluating",
            errorCode: executionSucceeded ? "" : (targetFile.functionRequest ? "FUNCTION_EXECUTION_FAILED" : "JSX_EXECUTION_FAILED"),
            retryable: false,
            completionKnown: true,
            operation: targetFile.name,
            startedAt: startedAt,
            message: executionSucceeded ? (targetFile.functionRequest ? "Function plan completed" : "JSX completed") : executionDescription,
            result: executionSucceeded && typeof evaluationResult !== "undefined" ?
                String(evaluationResult) : "",
            runningFile: runningFile
        };
        this.pendingReport = report;
        this.publishPendingReport();
    };

    Bridge.prototype.scheduleNext = function (delay) {
        if (this.running && !this.taskId) {
            this.taskId = app.scheduleTask(
                "$.global.__codexAeBridgeV1.runScheduled(" + this.generation + ")",
                delay,
                false
            );
            if (!this.taskId) {
                throw new Error("After Effects could not schedule the next bridge task");
            }
        }
    };

    Bridge.prototype.runScheduled = function (generation) {
        if (!this.running || generation !== this.generation) {
            return;
        }

        this.taskId = 0;
        if (!this.ready) {
            this.advanceStartup(generation);
        } else {
            this.tick(generation);
        }
    };

    Bridge.prototype.failStartup = function (error) {
        this.log("error", "Connection failed: " + this.describeError(error));
        this.setConnectionStatus(false, "Connection error");
        var failedAt = this.progressValue;
        this.ready = false;
        this.running = false;
        this.taskId = 0;
        this.showProgress();
        this.setProgress(failedAt, "Failed at " + failedAt + "%");
        this.setUiStatus("Could not start bridge:\n" + String(error));
        try {
            this.writeHeartbeat("error", String(error));
        } catch (heartbeatError) {
            // The inline status remains available when file access failed.
        }
    };

    Bridge.prototype.advanceStartup = function (generation) {
        if (!this.running || generation !== this.generation) {
            return;
        }

        try {
            switch (this.startupStep) {
            case 0:
                this.setProgress(10, "Checking workspace");
                if (!(new Folder(this.workspaceRoot)).exists) {
                    throw new Error("Workspace folder does not exist: " + this.workspaceRoot);
                }
                break;
            case 1:
                this.setProgress(25, "Preparing runtime folder");
                this.ensureFolder(this.workspaceRoot + "/.ae-codex");
                break;
            case 2:
                this.setProgress(45, "Preparing bridge storage");
                this.ensureFolder(this.bridgeRoot);
                break;
            case 3:
                this.setProgress(65, "Preparing job inbox");
                this.ensureFolder(this.inboxPath);
                break;
            case 4:
                this.setProgress(80, "Preparing result storage");
                this.ensureFolder(this.resultsPath);
                break;
            case 5:
                this.setProgress(92, "Testing heartbeat");
                this.writeHeartbeat("starting", "Bridge startup in progress");
                break;
            case 6:
                this.setProgress(97, "Starting library and job listener");
                this.bundle.refresh(false);
                this.bundle.loadInstallation();
                this.refreshScriptsDisplay();
                this.beginLibrary();
                break;
            default:
                this.ready = true;
                this.setProgress(100, "Success");
                this.writeHeartbeat("running", "Waiting for jobs");
                this.setUiStatus(
                    "Bridge " + BRIDGE_VERSION + " connected successfully\n" +
                    "Ready for Codex jobs"
                );
                this.hideProgressPending = true;
                this.log("info", "Bridge " + BRIDGE_VERSION + " connected; ready for jobs");
                break;
            }

            if (!this.ready) { this.log("info", this.progressLabel, "", this.progressValue); }
            this.startupStep += 1;
            if (this.running && generation === this.generation) {
                this.scheduleNext(this.ready ? 700 : 80);
            }
        } catch (startupError) {
            this.failStartup(startupError);
        }
    };

    Bridge.prototype.tick = function (generation) {
        if (!this.running || !this.ready || generation !== this.generation) {
            return;
        }

        try {
            if (this.hideProgressPending) {
                this.hideProgressPending = false;
                this.hideProgress();
            }

            if (this.pendingReport) {
                this.publishPendingReport();
            }
            if (!this.pendingReport && this.pendingCleanupFile) {
                this.retryPendingCleanup();
            }

            var now = new Date().getTime();
            if (now - this.lastModelRefresh >= 2000) {
                this.refreshModelDisplay();
            }
            if (now - this.lastHeartbeat >= 2000) {
                this.writeHeartbeat(
                    "running",
                    this.pendingReport ? "Reporting JSX result" :
                        (this.pendingCleanupFile ? "Cleaning completed job" :
                            (this.busy ? "Executing JSX" : "Waiting for jobs"))
                );
            }

            if (!this.busy) {
                var inbox = new Folder(this.inboxPath);
                var jobs = inbox.getFiles(function (candidate) {
                    return candidate instanceof File && /\.job$/i.test(candidate.name);
                });

                if (jobs.length > 0) {
                    jobs.sort(function (left, right) {
                        return left.name < right.name ? -1 : (left.name > right.name ? 1 : 0);
                    });
                    this.processJob(jobs[0]);
                } else {
                    if (now - this.bundle.lastPoll >= 2000) { this.bundle.refresh(false); }
                    this.refreshScriptsDisplay();
                    if (this.library) {
                        this.library.tick();
                        this.refreshLibraryDisplay();
                    }
                }
            }
        } catch (tickError) {
            this.logOnce("listener", "error", "Bridge listener error: " + this.describeError(tickError));
            this.setConnectionStatus(false, "Connection error");
            this.setUiStatus("Bridge error: " + String(tickError));
            try {
                this.writeHeartbeat("error", String(tickError));
            } catch (heartbeatError) {
                // The palette remains visible so the user can see the failure.
            }
        } finally {
            if (this.running && this.ready && generation === this.generation) {
                try {
                    this.scheduleNext(500);
                } catch (scheduleError) {
                    this.log("error", "Bridge listener stopped: " + this.describeError(scheduleError));
                    this.ready = false;
                    this.running = false;
                    this.setConnectionStatus(false, "Listener stopped");
                    this.showProgress();
                    this.setProgress(100, "Listener stopped");
                    this.setUiStatus("Bridge listener stopped:\n" + String(scheduleError));
                    try {
                        this.writeHeartbeat("error", String(scheduleError));
                    } catch (heartbeatError) {
                        // The inline status remains available.
                    }
                }
            }
        }
    };

    Bridge.prototype.start = function () {
        try {
            // A ScriptUI panel can be closed while its named engine survives.
            // Always replace the old task instead of trusting a stale running
            // flag or task ID when the panel is opened again.
            if (this.taskId) {
                try {
                    app.cancelTask(this.taskId);
                } catch (cancelError) {
                    // The previous task may already have expired.
                }
            }
            this.generation += 1;
            if (this.library) { this.library.stop(); }
            this.taskId = 0;
            this.running = true;
            this.ready = false;
            this.busy = this.pendingReport !== null || this.pendingCleanupFile !== null;
            this.setConnectionStatus(false, "Connecting...");
            this.startupStep = 0;
            this.hideProgressPending = false;
            this.lastHeartbeat = 0;
            this.showProgress();
            this.setProgress(0, "Initializing");
            this.setUiStatus("Bridge " + BRIDGE_VERSION + " starting...");
            this.log("info", "Connecting automatically to workspace bridge");
            this.scheduleNext(60);
        } catch (startError) {
            this.failStartup(startError);
        }
    };

    Bridge.prototype.stop = function () {
        this.log("info", "Bridge stopped by user");
        this.generation += 1;
        if (this.library) { this.library.stop(); }
        this.refreshLibraryDisplay();
        if (this.taskId) {
            try {
                app.cancelTask(this.taskId);
            } catch (cancelError) {
                // Continue stopping even if the task already ended.
            }
        }

        this.taskId = 0;
        this.running = false;
        this.ready = false;
        this.setConnectionStatus(false, "Disconnected");
        this.startupStep = 0;
        this.hideProgressPending = false;
        this.setProgress(0, "Stopped");
        this.hideProgress();
        try {
            this.writeHeartbeat("stopped", "Bridge stopped by user");
        } catch (heartbeatError) {
            // There may be no file permission while stopping.
        }
        this.setUiStatus("Bridge stopped");
    };

    Bridge.prototype.showWindow = function () {
        if (this.window) {
            if (this.window instanceof Window) {
                this.window.show();
            } else {
                this.window.layout.layout(true);
            }
        }
    };

    var bridge;
    if (existingBridge && existingBridge.version === BRIDGE_VERSION) {
        bridge = existingBridge;
    } else {
        if (existingBridge && existingBridge.stop) {
            try {
                existingBridge.stop();
            } catch (oldBridgeError) {
                // Continue replacing an outdated controller.
            }
        }
        bridge = new Bridge(WORKSPACE_ROOT);
    }
    $.global[GLOBAL_NAME] = bridge;

    if (autoStartOnly) {
        bridge.start();
        return;
    }

    var palette = (thisObject instanceof Panel) ?
        thisObject :
        new Window("palette", "Codex AE Bridge " + BRIDGE_VERSION, undefined, { resizeable: true });
    palette.orientation = "column";
    palette.alignChildren = ["fill", "top"];
    palette.margins = 12;

    var connectionText = palette.add("statictext", undefined, "\uD83D\uDC4E DISLIKE - Connecting...");
    connectionText.alignment = ["fill", "top"];
    try {
        connectionText.graphics.font = ScriptUI.newFont("Segoe UI Emoji", "REGULAR", 16);
    } catch (connectionFontError) {
        // LIKE / DISLIKE labels remain readable if emoji fonts are unavailable.
    }
    connectionText.helpTip = "LIKE: AE bridge is running and publishing heartbeat. DISLIKE: starting, stopped, or connection error. This shows bridge availability, not whether a Codex chat is currently working.";

    var statusText = palette.add("statictext", undefined, "Starting bridge...", { multiline: true });
    statusText.preferredSize = [420, 48];

    var modelText = palette.add("statictext", undefined, "Codex model: loading...");
    modelText.alignment = ["fill", "top"];
    modelText.helpTip = "Configured default, synced when selecting a model or submitting JSX. A chat can override it. This does not identify the approval reviewer model.";

    var libraryText = palette.add("statictext", undefined, "Library: connect to scan effects and SFX", { multiline: true });
    libraryText.alignment = ["fill", "top"];
    libraryText.preferredSize = [420, 36];
    libraryText.helpTip = "Read-only effects, applied parameter schemas, project audio and configured disk SFX. Refreshes on connection and every 2 minutes while idle. Independent of installation-only script validation. See .ae-codex/library/current.json for paths and errors.";

    var scriptsText = palette.add("statictext", undefined, "Scripts: waiting for bundle index", { multiline: true });
    scriptsText.alignment = ["fill", "top"];
    scriptsText.preferredSize = [420, 36];
    var scriptButtons = palette.add("group");
    var viewScriptsButton = scriptButtons.add("button", undefined, "Archive...");
    var viewFunctionsButton = scriptButtons.add("button", undefined, "Tools...");
    viewScriptsButton.onClick = function () { bridge.showScripts(); };
    viewFunctionsButton.onClick = function () { bridge.showFunctions(); };

    var progressGroup = palette.add("group");
    progressGroup.orientation = "column";
    progressGroup.alignment = ["fill", "top"];
    progressGroup.alignChildren = ["fill", "top"];
    progressGroup.spacing = 4;

    var progressText = progressGroup.add("statictext", undefined, "Loading - 0%");
    progressText.alignment = ["fill", "top"];

    var progressBar = progressGroup.add("progressbar", undefined, 0, 100);
    progressBar.alignment = ["fill", "top"];
    progressBar.preferredSize = [420, 14];

    var buttons = palette.add("group");
    buttons.orientation = "row";
    buttons.alignment = ["right", "top"];
    var startButton = buttons.add("button", undefined, "Reconnect");
    startButton.helpTip = "Reconnect after Stop or a connection error. The panel connects automatically when opened.";
    var stopButton = buttons.add("button", undefined, "Stop");

    startButton.onClick = function () {
        bridge.start();
    };
    stopButton.onClick = function () {
        bridge.stop();
    };

    var logPanel = palette.add("panel", undefined, "Work log");
    logPanel.orientation = "column";
    logPanel.alignChildren = ["fill", "top"];
    logPanel.alignment = ["fill", "fill"];
    var logView = logPanel.add("edittext", undefined, "", { multiline: true, readonly: true, scrolling: true });
    logView.preferredSize = [420, 160];
    logView.minimumSize = [220, 90];
    logView.alignment = ["fill", "fill"];
    var clearLogButton = logPanel.add("button", undefined, "Clear view");
    clearLogButton.alignment = ["right", "bottom"];
    clearLogButton.onClick = function () { bridge.clearLog(); };
    if (palette instanceof Window) {
        palette.onClose = function () {
            bridge.stop();
            $.global[GLOBAL_NAME] = null;
            return true;
        };
    }
    palette.onResizing = palette.onResize = function () {
        this.layout.resize();
    };

    bridge.window = palette;
    bridge.statusText = statusText;
    bridge.connectionText = connectionText;
    bridge.modelText = modelText;
    bridge.libraryText = libraryText;
    bridge.bundle = $.global.__codexAeBundleV1;
    bridge.functions = $.global.__codexAeFunctionsV1;
    bridge.scriptsText = scriptsText;
    bridge.logView = logView;
    bridge.refreshLog();
    try { bridge.bundle.refresh(false); bridge.bundle.loadInstallation(); } catch (bundleError) {
        bridge.bundle.error = String(bundleError);
        bridge.log("error", "Bundle unavailable: " + String(bundleError));
    }
    bridge.refreshScriptsDisplay();
    bridge.modelDisplayValue = "";
    bridge.refreshModelDisplay();
    bridge.progressGroup = progressGroup;
    bridge.progressText = progressText;
    bridge.progressBar = progressBar;
    statusText.text = bridge.lastStatus || "Starting bridge...";
    progressText.text = bridge.progressLabel + " - " + bridge.progressValue + "%";
    progressBar.value = bridge.progressValue;
    if (palette instanceof Window) {
        palette.center();
        palette.show();
    } else {
        palette.layout.layout(true);
    }
    // Opening the panel connects automatically; Stop remains explicit until reopened.
    bridge.start();
}(this));
