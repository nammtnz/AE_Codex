# Codex + Adobe After Effects (Windows)

## Bridge 1.9.0 — bộ chức năng AE dùng lại

Bridge cài sẵn các chức năng có tham số để tạo/sửa composition, layer,
animation, effect, media và render. Mỗi việc gửi tên chức năng cùng JSON;
không sinh JSX cho mỗi lần làm. `jsx/` chỉ giữ **Codex Bridge.jsx**.

Danh sách hoạt động có **42 công cụ dùng lại**. **805 script cũ là kho lưu trữ**,
không tính vào số công cụ và không xuất hiện trong tìm kiếm mặc định.
Nhánh cũ có giá trị riêng của project trước nên không thay thế công cụ có
tham số. Code AI/chat, chọn model, CEP UI và ElevenLabs của source tham khảo
không được tích hợp. Codex hiện tại gọi các công cụ AE đã cài.

Bảng `.ae-codex/functions/external-ae-tool-mapping.json` đối chiếu đủ 50 thao tác
AE của source tham khảo với tool hoặc plan hiện tại. `execute_script` được thay
bằng cách bổ sung chức năng có tên; không cài bộ thực thi JSX tùy ý.

## Cài và kết nối

Yêu cầu After Effects, Node.js và PowerShell 7. Trong AE, bật một lần:

`Edit > Preferences > Scripting & Expressions > Allow Scripts to Write Files and Access Network`

Nếu chưa có panel người dùng, chọn `File > Scripts > Install ScriptUI Panel...`
và chọn `jsx/Codex Bridge.jsx`. Sau đó, từ workspace:

~~~powershell
pwsh -NoProfile -File .\tools\Install-AeFunctions.ps1
~~~

Installer build, kiểm tra bundle, cập nhật panel trong AppData và đăng ký MCP
`ae_functions` cho Codex. Project cũng có `.codex/config.toml` cho project
được tin cậy. Đóng/mở lại **Window > Codex Bridge** để nạp panel mới;
mở chat Codex mới hoặc tải lại MCP để nạp cấu hình công cụ.
Phiên chưa nạp MCP vẫn dùng các lệnh PowerShell bên dưới.

Panel tự kết nối khi mở. **Stop** dừng phiên; **Reconnect** nối lại.
Installer có loader nhỏ trong
`%APPDATA%\Adobe\After Effects\26.5\Scripts\Startup`; việc AE tự thực thi loader
người dùng này chưa được xác minh trực tiếp. Workspace đã lưu có panel docked.
AE phải đang chạy để nhận job; bật Windows riêng chưa tạo kết nối AE.
Không dùng installer cũ ghi vào `Program Files` khi phát triển.

## Tìm, xem tham số rồi gọi

| Tool | Cách dùng |
| --- | --- |
| `ae_search_capabilities` | Tìm công cụ hoạt động; mặc định `kind: "function"`. Có `query`, `category`, `offset`, `limit` tối đa 100. |
| `ae_inspect_capability` | Đọc schema và điều kiện theo `id`. |
| `ae_run_capability` | Chạy `{ "id": "ID đã chọn", "args": { ... } }`. |
| `ae_capability_status` | Xem riêng số tool hoạt động, script lưu trữ, chứng nhận cài và kết nối AE. |

Các tool AE trực tiếp và `ae_run_plan` cũng dùng registry này. Với CLI:

~~~powershell
pwsh -NoProfile -File .\tools\Get-AeFunctions.ps1
node .\tools\Get-AeCapabilities.js search '{"query":"text","limit":10}'
pwsh -NoProfile -File .\tools\Invoke-AeFunction.ps1 -Function project.inspect -ArgumentsJson '{}'
~~~

`tools.list` mặc định `includeLegacy: false`. Catalog hoạt động ở
`.ae-codex/functions/catalog.json`; bảng **Tools...** trong panel hiển thị
các chức năng này. Đọc schema thực tế trước khi chọn tham số.

Các nhóm gồm đọc/tạo/sửa/nhân bản/precompose composition; tạo và chỉnh text,
solid, shape, null, camera, light; chọn layer, parent, blend mode, 3D, timing;
đọc/ghi property, keyframe, easing, expression; tìm/kiểm tra/thêm/xóa effect;
import và thêm footage vào comp; lưu, undo và render queue.
Không có tool thực thi JSX tùy ý thay cho registry.

Selector comp dùng đúng một trường `{ "id": 123 }`, `{ "name": "Main" }` hoặc
`{ "ref": "scene" }`. Layer dùng `{ "index": 1 }`, `{ "name": "Title" }` hoặc ref
từ bước tạo layer trước. Tên trùng báo lỗi, cần dùng ID/index.
Bỏ `comp` để dùng composition hiện tại.

Nhiều bước dùng `Invoke-AeFunction.ps1 -Plan <file-JSON>` hoặc
`-PlanJson '<JSON>'`, ví dụ thêm text rồi chỉnh vị trí trong comp hiện tại:

~~~json
{
  "schema": "codex-ae-functions/v1",
  "steps": [
    { "function": "layer.text.create", "args": { "text": "Hello", "name": "Title" }, "as": "title" },
    { "function": "layer.update", "args": { "layer": { "ref": "title" }, "transform": { "position": [960, 540] } } }
  ]
}
~~~

Tọa độ ví dụ dành cho comp 1920×1080; kiểm tra kích thước trước khi dùng.
Kế hoạch và báo cáo nằm trong `.ae-codex/`, không thêm JSX vào source.
Việc lặp lại thay tham số công cụ đã có. Chỉ thêm chức năng tổng quát khi
registry thực sự thiếu; không tạo bản sao theo ngày, project hoặc từng job.

`media.import` cần đường dẫn nguồn tuyệt đối. Lưu, xóa, import, ghi đè và render
chỉ được gọi khi yêu cầu người dùng đã bao gồm thao tác đó.
`project.save` cần `path` khi project chưa lưu; `overwrite: true` cho phép
thay một đích khác đã tồn tại. `render.queue.add` cần `outputPath` và nhận
tên template chính xác. `render.start`, `project.save` và `project.undo` chạy
riêng một job. Không tự undo hoặc gửi lại thao tác lỗi.

## Effect và kiểm tra hình ảnh

`effects.list` đọc `app.effects` trực tiếp, nhận `search`, `category`,
`maxItems`; không tạo layer thử. `effect.inspect` nhận selector `layer` và
`maxProperties`, trả tên/matchName, đường dẫn và giá trị có giới hạn.
`effect.add` dùng matchName chính xác; `effect.remove` nhận selector `effect`
bằng đúng một `index` hoặc tên instance không trùng. Chỉnh property effect qua
các công cụ property chung. Effect đăng ký không chứng minh license, render
hay API JSX của panel riêng.

~~~powershell
pwsh -NoProfile -File .\tools\Invoke-AeFunction.ps1 -Function inspection.capture -ArgumentsJson '{}'
~~~

`inspection.capture` nhận `times: [0, 2, 5]` hoặc `numFrames: 4`, tối đa 10 frame,
không dùng cả hai. Thời gian từ 0 đến `duration - frameDuration`; frame mẫu
không dùng mốc kết thúc loại trừ. Mặc định chụp tại thời gian viewer hiện tại,
không đổi viewer time hay project.

Ảnh chỉ ghi vào `.ae-codex/inspection/<runId>/`, không ghi đè run cũ.
Ảnh đầu `frame.png`, ảnh sau `frame-002.png`... cùng `manifest.json`.
Kết quả trả `frameRelativePath`, danh sách frame và metadata PNG;
`visualVerified: false` / `visualReviewState: pending` nghĩa là chưa xem ảnh.
Codex mở ảnh cần kiểm tra bằng `view_image` rồi mới xác nhận đã xem.

Nếu dịch vụ duyệt ảnh lỗi, không thử né kiểm duyệt hoặc nhận đã xem.
Chạy báo cáo kỹ thuật cho cùng run ID:

~~~powershell
pwsh -NoProfile -File .\tools\Get-AeInspectionReport.ps1 -RunId <run-id> -VisualReviewErrorCode MODERATION_SERVICE_ERROR -VisualReviewErrorMessage 'Automatic approval reviewer was unavailable.'
~~~

Báo cáo cho `frame.png` giữ `visualReview.verified: false`; chữ ký, kích thước,
SHA-256 và metadata màu không thay việc xem pixel. Ảnh/báo cáo giữ với
`retention: manual`.

## Kiểm tra khi cài và log

Kiểm tra đầy đủ chỉ chạy lúc build/cài/cập nhật. Chứng nhận ở
`.ae-codex/bundle/installed-validation.json` và `installed-validation.tsv`
gắn với nội dung bundle; bản không đổi tái sử dụng chứng nhận.
Không quét lặp toàn bộ source trong AE khi kết nối. Catalog được cache;
không đăng ký 805 định nghĩa tool hay đưa code lưu trữ vào ngữ cảnh AI.

Bảng log dưới panel giữ tối đa 200 dòng về kết nối, tiến trình, hoàn tất và lỗi.
Lịch sử ở `.ae-codex/bridge/logs/events.log` có xoay file.
Tiến trình là những bước thực sự đã báo, không đoán phần trăm thao tác đang
chặn AE. Lỗi ghi log không chạy lại job hay thay kết quả thực tế.

Kiểm kê effect/audio/SFX là luồng riêng, làm mới lúc kết nối và mỗi 120 giây
khi rảnh. Đọc `.ae-codex/library/current.json`, `library/USAGE.md` và catalog
plugin trước khi chọn effect/SFX. Kiểm kê không import media hay sửa project.

## Bảo trì source và kho cũ

Nguồn panel/runtime: `source/bridge.js`, `source/bundle-runtime.js`,
`source/functions-runtime.js`. Các phần chức năng nằm trong
`source/functions-layer-tools.js`, `source/functions-project-tools.js`,
`source/functions-inspection-tools.js`; `tools/AeFunctionsSource.js` ghép
chúng trước khi builder sinh **một JSX**. Không sửa JSX đã sinh.

805 nhánh cũ giữ qua module dùng chung và recipe trong `source/scripts.json`;
`source/script-inventory.json` ngăn mất nhánh. Chúng là kho bảo trì,
không phải 805 chức năng hoạt động. Chỉ bảo trì rõ ràng mới dùng
`kind: "script"`/`"all"`, `Get-AeFunctions.ps1 -IncludeLegacy` hoặc
`tools.list` với `includeLegacy: true`. Nhánh `script.run` vẫn cần đọc source
và điều kiện project gốc; không dùng để tạo job thường.

Metadata kho ở `.ae-codex/functions/capabilities.json` gồm checksum, gợi ý code,
phụ thuộc và cú pháp. Gợi ý/rủi ro có thể nhầm hoặc bỏ sót alias/giá trị động.
`runtimeVerified: false` không chứng minh đã chạy trên AE. Nhóm cùng cấu trúc
giữ riêng vì khác comp/thời gian/đường dẫn. Build lỗi nếu thiếu inventory.

~~~powershell
node .\tools\Build-AeScriptBundle.js
node .\tools\Build-AeScriptBundle.js --verify
node .\tests\Test-AeFunctions.js
node .\tests\Test-AeLayerTools.js
node .\tests\Test-AeProjectTools.js
node .\tests\Test-AeInspectionTools.js
pwsh -NoProfile -File .\tools\Install-AeFunctions.ps1
~~~

Chạy thêm kiểm tra liên quan tới phần sửa. JSX gốc và báo cáo chuyển đổi ở
`.ae-codex/bundle/`. Không xóa inventory hay thay hash để vượt kiểm tra.

## Timeout và giới hạn

Bridge tuần tự hóa job bằng `.ae-codex/bridge/submit.lock`, công bố trạng thái
nguyên tử. Thành công phải có `state: success`. Các bước dừng khi lỗi;
bước đã thành công có thể đã sửa project. Đọc kết quả và kiểm tra hiện trạng
trước khi xử lý phần còn lại. Không tự gửi lại kế hoạch vì lỗi xuất status.

Nếu timeout, giữ khóa, kiểm tra AE có dialog/modal và đã bật quyền ghi file.
Không chạy job mới, tự xóa khóa hoặc kill AE. Chỉ sau khi xác minh AE rảnh:

~~~powershell
pwsh -NoProfile -File .\tools\Reset-AeBridgeLock.ps1 -RunId <run-id> -IHaveVerifiedAfterEffectsIsIdle
~~~

`tools/Run-AeJsx.ps1` là fallback cho host cùng Windows session; file bridge
là mặc định trên máy này. Không dùng `aerender.exe` làm cầu nối JSX.
