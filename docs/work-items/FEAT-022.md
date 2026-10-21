# FEAT-022：运行旧源码实例时的重启指引

类型：功能。优先级：P2。状态：验收中。目标版本：未排期。

## 目标与现状

升级磁盘源码不替换已运行MCP实例。当前startup status/capabilities已公开启动指纹、当前指纹比较与source_changed_since_startup。新增工具仍需重启连接器，版本号或远端有新版不足以证明实际部署。

## 本轮范围与验收

接管工具说明、README/安装入口及ADOPTION说明置前提示重启，要求核对版本、实际路径、启动指纹和工具清单；保留现有机制。现有test_creo_startup覆盖未改动时false、源码变化时true且不篡改启动身份；helper_layout既有用例覆盖包内辅助模块的指纹变化。新session_models模块已加入启动清单，逐文件身份见本轮证据。实际连接器更新前→更新未重启→重启后黑盒对照仍需在客户端执行；不引入热重载，不与FEAT-029回调DLL生命周期混同。

结果见本轮纳管完善证据；未执行的真实连接器升级对照保持未测。

2026-10-19字段修正后，开发者通过当前E盘dev服务只读capabilities确认实际路径正确、source_changed_since_startup=true，启动指纹仍为旧代码；新inspection_units.h已加入启动身份及变化检测回归。固定源码后的406项单元/统一检查通过，见[补录](../validation/ADOPTION-WorkBuddy-2026-10-19.md)。这是更新后未重启状态的开发者观察；WorkBuddy重启后身份、能力和字段复验仍未执行，不据此关闭整项。

## 2026-10-20：session_status 统一携带 server_version

[v0.4.1 反馈](../validation/FEEDBACK-0.4.1-CREO10-2026-10-20.md) P2-3 要求 `creo_session_status` 直接携带版本便于反馈对齐（capabilities 顶层 `version` 已存在，见该核对结论第 2 条）。本轮在工具层为 session_status 的全部返回分支（运行中、connected、timeout、busy、probe_failed）统一附加 `server_version`，保留原部署身份诊断字段。不改 startup_status/callback_status 的既有结构；真实连接器升级前后黑盒对照仍按上文未测边界保留。实现当日经 stdio 直连实测 `server_version` 与 capabilities.version 一致（[验证记录](../validation/FEAT-044-live-2026-10-20.md)第二节），随 0.4.2 发布。
