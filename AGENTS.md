# After Effects JSX workspace

## Installed plugin knowledge

- Codex Bridge automatically refreshes a read-only effect/project-audio/SFX inventory on connection and every 120 idle seconds. This inventory refresh is independent of bundle installation validation. Before choosing a sound or checking new plugins, read `.ae-codex/library/current.json` and `.ae-codex/library/USAGE.md`; follow the current catalog paths and inspect state/timestamps/warnings. Use `rg` to search the SFX JSONL rather than reading the whole catalog. Configured roots are in `.ae-codex/library/config.json`; new files inside them are discovered automatically. New plugins require AE to load them (often after restart). An inventory entry does not authorize importing/applying it outside the requested edit or prove license/render support.

- User preference: during requested After Effects editing tasks, proactively choose and apply suitable already-installed plugins/effects/presets when they materially improve the requested result. The user authorizes routine plugin selection and parameter/keyframe adjustments within the task without asking approval for each effect; they need not name the plugin.
- Choose based on the shot's purpose and style; keep gameplay/text readable and consider preview/render performance. Use a modest effect stack, validate parameters and review the result, then briefly explain the plugin's contribution. This preference alone does not request changes to the current composition or authorize installing new software, purchases, or unrelated project changes. Respect the bridge connection/Stop controls and existing project-data rules.
- Before choosing or applying installed effects/panels, read `.ae-codex/plugins/USAGE.md` and look up exact effect matchNames in `.ae-codex/plugins/effects-and-parameters.tsv` (category index: `.ae-codex/plugins/effect-index.md`).
- This local catalog distinguishes registered effects from installed panels and verified parameter schemas from untested capabilities. Refresh with `jsx/catalog-installed-plugins.jsx` through the bridge when needed; do not assume every installed plugin is licensed or every panel has a JSX effect API.

This workspace is for Adobe After Effects ExtendScript automation on Windows.

## Installed function tools (Bridge 1.9.0)

- `tools/Install-AeFunctions.ps1` builds, updates the installed user panel and
  registers the local `ae_functions` MCP server in the Codex user configuration.
  `.codex/config.toml` also supports project-scoped configuration for trusted
  projects. The server is implemented by `tools/AeFunctionsMcp.js`. After Codex
  loads the configuration (normally in a new chat/session), use its
  installed AE tools directly. Start with `ae_search_capabilities`, which
  searches only the active reusable function registry by default.
  `ae_inspect_capability` shows arguments, static requirements/risks and optional
  paginated source; `ae_run_capability` dispatches an installed capability ID;
  `ae_capability_status` checks mapping coverage, installation and connection.
  MCP tool registration and the running AE panel connection are separate; both
  must be available for live work. A session that has not loaded the project
  MCP config can use the PowerShell clients below.
- The default AI workflow is search, inspect, then run an installed capability
  with JSON arguments. Search arguments are `{query?,kind?,category?,offset?,limit?}`;
  `kind` defaults to `function`; `script` or `all` is reserved for explicitly requested archive maintenance. Inspect with
  `{id,includeSource?,sourceOffset?,sourceLimit?}`; source pages contain at most
  250 lines. Run with `{id,args?}`. Reusable functions expose argument schemas. Archived scripts keep their fixed
  original behavior and accept no new arguments; do not include them in ordinary
  tool discovery or active tool counts.
  CLI discovery without AE dispatch is `node tools/Get-AeCapabilities.js
  search '<JSON object>'`, or `inspect`/`status`. The existing PowerShell
  `Get-AeFunctions.ps1` client remains available for function-only discovery.
- The active registry has 42 public reusable tools. `tools.list` defaults to
  `includeLegacy: false`, as does `tools/Get-AeFunctions.ps1`. The internal
  `script.run` maintenance entry and 805 archived branches are excluded from
  active counts and default searches. `.ae-codex/functions/catalog.json`
  describes the named functions; the generated
  `.ae-codex/functions/capabilities.json` maps every historical branch to a stable
  callable ID and records source SHA-256, categories, literal comp/layer/file/effect
  hints, API-risk candidates, static dependencies and syntax results for archive
  maintenance. The panel's `Tools...` list exposes the active registry.
  All 805 archived branch names,
  including the internal inventory library, must remain mapped. The build fails
  if an inventoried branch is missing; extra branches are retained and reported.
- Full source analysis runs during build/installation, never as an AE background
  scan or by executing the scripts. Discovery caches the generated index between
  unchanged file revisions. MCP adds compact search/inspect/run/status tools;
  do not register 805 separate eager tool definitions or load every script body
  into AI context at connection time. Inspect only the needed source pages.
- Analyzer hints and risk markers are heuristics, not verified project
  requirements. File close, project close and ambiguous close are distinguished;
  string/media replacement can remain ambiguous. Frame export is separate from
  queued rendering. `runtimeVerified: false` must remain explicit until an actual
  requested AE run supplies evidence. Syntax parsing, complete mapping and source
  hashes do not prove plugin/license/media support or suitability for the open
  project. Structural duplicate groups ignore literal values and never authorize
  removing or aliasing a variant.
- Invoke one tool with `tools/Invoke-AeFunction.ps1 -Function <name>
  -ArgumentsJson '<JSON object>'`. Submit several steps with `-Plan <JSON path>`
  or `-PlanJson '<JSON request>'`. Requests use schema `codex-ae-functions/v1`
  and `steps: [{"function":"project.inspect","args":{}}]`.
  Store task plans and results under `.ae-codex/`; a task needs no new JSX file.
- Search the active function registry before implementing anything new. Reuse
  installed functions with different parameters or compose them into a JSON
  plan. Historical scripts are an archive, not everyday tools. Only for an
  explicitly requested archive maintenance task, use `kind: "script"`/`"all"`,
  `Get-AeFunctions.ps1 -IncludeLegacy -Search <text>`, or `script.run` with
  `{"branch":"hello.jsx"}`. Archived scripts contain project-specific
  assumptions; inspect their source and requirements before executing them.
- Do not create dated/project-specific JSX clones or add a legacy branch for
  each job. If a requested capability is truly absent, add a reusable named
  function to the reusable runtime or an appropriate source module, document and
  validate its arguments, rebuild the bundle and update the installed panel. Runtime requests are data;
  do not pass arbitrary JSX or eval snippets as a replacement for implementing
  a reusable function. A named tool that sets an AE expression property may
  accept a legitimate expression string for that specific property.
- Native AE functions are the integration surface. Do not copy external
  AI/chat/model selection, CEP UI or ElevenLabs integrations into this bridge.
  Batch operations reuse the registry through plans; do not add arbitrary
  `execute_script` or eval tools.
  `.ae-codex/functions/external-ae-tool-mapping.json` accounts for all 50 native
  AE entries from the read-only reference source, including argument translation
  and the deliberate replacement of arbitrary script execution. It is a semantic
  map, not a compatibility adapter or proof of live AE execution.
- Function steps execute in order and stop on error. Earlier successful edits
  may already exist when a later step fails. Inspect the returned result and
  current project before deciding what remains; never automatically replay the
  whole plan or a timed-out job.

## Single JSX bundle

- Keep `jsx/Codex Bridge.jsx` as the only permanent runnable JSX. It includes
  the panel, installed function tools and all historical script branches,
  loaded individually on demand. The 805 historical branch names remain an
  archive; only reusable tools belong to the active catalog.
- Editable panel/runtime sources are `source/bridge.js` and
  `source/bundle-runtime.js` and `source/functions-runtime.js`. Function modules
  are `source/functions-layer-tools.js`, `source/functions-project-tools.js`
  and `source/functions-inspection-tools.js`, assembled by
  `tools/AeFunctionsSource.js` before generating the single JSX.
  `source/scripts.json` uses schema v2: shared source
  modules plus per-branch slice recipes and SHA-256. Export a branch to edit it;
  do not manually change shared modules or recipe hashes. The build reconstructs
  every branch exactly and packs shared modules once;
  `source/script-inventory.json` prevents losing original branches during builds.
  Do not edit the generated JSX or remove inventory entries to make a build pass.
- Run an existing branch with
  `pwsh -NoProfile -File tools/Submit-AeJsx.ps1 -Branch hello`.
  Legacy `-Script jsx/hello.jsx` also resolves to the packed branch even though
  that individual file is absent. This is an archive maintenance route;
  ordinary inspection uses the reusable `inspection.capture` tool.
- For maintenance of an existing historical branch, export it with
  `node tools/Build-AeScriptBundle.js --export hello.jsx`, edit `jsx/hello.jsx`,
  then run `node tools/Build-AeScriptBundle.js --update jsx/hello.jsx`.
  Update verifies all branches, backs up the source JSON, packs the changes,
  and consumes the staged file in `jsx/`. This is a maintenance route; ordinary
  AI tasks use the installed function tools above.
- After editing the panel/runtime, run `node tools/Build-AeScriptBundle.js`.
  Verify with `node tools/Build-AeScriptBundle.js --verify`,
  `node tests/Test-AeBridgeLibrary.js`, `node tests/Test-AeScriptBundle.js`,
  `node tests/Test-AeScriptSource.js`, `node tests/Test-AeFunctions.js`,
  `node tests/Test-AeLayerTools.js`, `node tests/Test-AeProjectTools.js`,
  `node tests/Test-AeInspectionTools.js`, `node tests/Test-AeScriptCapabilities.js`,
  and `pwsh -NoProfile -File tests/Test-AeScriptResolver.ps1`.
- Full bundle validation runs at installation/update through
  `tools/Validate-AeBridgeInstallation.ps1`. It checks inventory presence, shared
  modules, slice bounds, reconstructed source checksums, dependencies and syntax
  without executing edits. Certificates are
  `.ae-codex/bundle/installed-validation.json` and `installed-validation.tsv`;
  an unchanged bundle reuses its certificate and a changed bundle requires
  validation again. Do not reintroduce background `bundle.tick` validation.
  `Archive...` shows installation certificate status and branch errors.
  Each selected branch still verifies its source checksum on demand. Decoded
  module caching is bounded to 131072 source characters and resets when the
  bundle changes. None of these checks prove media, plugin, license or project
  requirements for a script.
- Update an existing user-installed panel using
  `tools/Update-AeBridgeUserPanel.ps1`, then close/reopen the panel. The panel
  connects automatically when loaded; no Start click is needed. Stop still
  stops the current session. The installer also places a thin loader in
  `%APPDATA%/Adobe/After Effects/26.5/Scripts/Startup`; actual AE execution of
  this user Startup loader is not yet verified. The existing saved workspace
  includes the docked panel. AE must be running to receive jobs; do not claim
  that Windows startup alone establishes an AE connection. Original JSX backup
  and migration verification are under `.ae-codex/bundle/`.
- The bottom panel log keeps at most 200 entries and records connection,
  job progress, completion and errors. Persistent logs are under
  `.ae-codex/bridge/logs/events.log` with rotation. Scripts may optionally call
  `$.global.__CODEX_AE_RUN_CONTEXT__.progress(percent, message)` and
  `.log(message)` after checking that those callbacks exist. Legacy scripts
  report only start/end; never invent intermediate percentages. Log failure
  must not re-execute a script or replace its actual terminal result.
- `node tools/Build-AeScriptBundle.js --optimize` can recompute shared modules
  deterministically without removing any branch names. Before publishing, every
  reconstructed source must match its SHA-256; the inventory is checked by build
  and CLI `--verify`. `--update` maintains the merged source format automatically.

## Authoring rules

- Keep `jsx/Codex Bridge.jsx` as the only permanent runnable script. For an
  authorized maintenance export, use `jsx/` and the `.jsx` extension, then pack
  and consume it with the bundle builder. Implement new reusable capabilities
  in the reusable runtime/source modules rather than generating a JSX for each
  task. Supply parameters to installed tools for ordinary work.
- Target ExtendScript/ECMAScript 3. Use `var`; do not use `let`, `const`, arrow
  functions, classes, modules, promises, Node.js APIs, or browser APIs.
- Wrap project mutations in `app.beginUndoGroup(...)` and always close the
  group in `finally`.
- Validate `app.project`, the active item, item types, and layer/property
  existence before mutating anything.
- Never save, close, overwrite, render, import, or delete project data unless
  the user's request explicitly requires it.
- Keep all generated logs and results under `.ae-codex/`. Do not write secrets
  or project media there.
- Do not install scripts into the After Effects application directory during
  development. Work from this repository.

## Run and verify

The default workflow uses installed function tools through the file bridge
running inside the user's interactive After Effects session. From the workspace:

```powershell
pwsh -NoProfile -File .\tools\Get-AeFunctions.ps1
node .\tools\Get-AeCapabilities.js search '{"query":"inspect","limit":10}'
pwsh -NoProfile -File .\tools\Invoke-AeFunction.ps1 -Function project.inspect -ArgumentsJson '{}'
```

Before submission, the installed `Window > Codex AE Bridge` panel (source:
`jsx/Codex Bridge.jsx`) must be running and connected in After Effects. It
connects automatically on load; a stopped session must be reconnected using
the panel controls before submitting work.
The function client submits only a named-tool JSON request, serializes executions
and waits for an atomic JSON status file. `Submit-AeJsx.ps1` remains available
for historical branch compatibility and source maintenance. A successful run must end with
`state: success`.

For visual inspection of the active composition, invoke `inspection.capture`
with `{}`. Optional `times` (1..10 times) or `numFrames` (1..10) capture multiple
frames; do not supply both. It exports the frame(s) to the
unique run folder under `.ae-codex/inspection/` without importing, saving, or
changing the project or viewer time. Inspect the returned `frameRelativePath`
and, for multiple frames, the `frames` entries. PNG metadata and
`visualVerified: false` do not prove a visual review. If image review
is unavailable because the approval/moderation service failed, do not attempt
to bypass it and do not claim visual verification. Instead run
`tools/Get-AeInspectionReport.ps1` for the same run ID, report
`visualReview.verified: false` with the returned error code, and use only the
technical metadata as a fallback.

Never automatically resubmit a function plan or JSX after dispatch merely because status
publication or visual review failed; the job may already have mutated the
project. The bridge publishes an immutable `started-<runId>.json` separately
from the immutable terminal `status-<runId>.json` and retries only result
publication, never script evaluation.

If a run times out, do not start another run and do not delete the lock
automatically. After verifying in After Effects that the prior script is idle,
use `tools/Reset-AeBridgeLock.ps1` with the exact run ID and its explicit
acknowledgement switch.

If a run times out before producing status, first verify that After Effects is
not blocked by a modal dialog and that this preference is enabled:

`Edit > Preferences > Scripting & Expressions > Allow Scripts to Write Files and Access Network`

Never kill After Effects merely to clear a bridge timeout; the project may have
unsaved work.

`tools/Run-AeJsx.ps1` is only a fallback for hosts where the Codex terminal and
the interactive After Effects instance share a Windows session. It is not the
default on this machine.
