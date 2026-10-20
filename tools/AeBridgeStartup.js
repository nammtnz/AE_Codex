#target aftereffects
#targetengine "codexAeBridge"
/* Installed only in the user's After Effects Scripts/Startup folder. */
(function () {
    var bundle;
    var hadFlag = Object.prototype.hasOwnProperty.call($.global, "__CODEX_AE_AUTOSTART_ONLY__");
    var previousFlag = $.global.__CODEX_AE_AUTOSTART_ONLY__;
    try {
        bundle = new File(__CODEX_AE_WORKSPACE_BUNDLE__);
        if (!bundle.exists) { throw new Error("Workspace bundle is missing: " + bundle.fsName); }
        $.global.__CODEX_AE_AUTOSTART_ONLY__ = true;
        $.evalFile(bundle);
    } catch (error) {
        try { $.writeln("Codex Bridge startup: " + error.toString()); } catch (ignoredLogError) {}
    } finally {
        if (hadFlag) { $.global.__CODEX_AE_AUTOSTART_ONLY__ = previousFlag; }
        else { delete $.global.__CODEX_AE_AUTOSTART_ONLY__; }
    }
}());
