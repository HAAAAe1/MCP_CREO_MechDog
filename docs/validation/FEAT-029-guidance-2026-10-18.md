# FEAT-029 问题 5 处置验证：指引置前与 readiness 语义拆分（2026-10-18）

来源：[0.3.7 / Creo 13 反馈](FEEDBACK-0.3.7-CREO13-2026-10-18.md)问题 5；[任务卡](../work-items/FEAT-029.md) 2026-10-18 实现节。

## 环境

Windows x64；Creo Parametric 12.4.0.0（release_numeric=44）、匹配 Toolkit SDK 与许可。分支 `codex/bug-067-creo13-feedback`，基底提交 `d647bfa`（BUG-069/070）+ 本次未提交改动（native/callback_runtime.h、src/creo_mechdog/blend_callback.py、server.py、README.md、docs/INSTALL.md、tests/unit/test_blend_callback.py、docs/BACKLOG.md、docs/work-items/FEAT-029.md）。`tools/dev_check.py` 通过（checked_source_sha256=12c6a82f… 中途快照；提交号见 git log）。

## 改动

1. **readiness 拆分**（0.3.4 外部反馈登记的双义缺口）：`not_loaded` = 可确定未加载（`no_runtime_identity_record` 首次从未加载 + `recorded_application_not_active` 已注册未运行）；`unknown` = 仅 `live_identity_unavailable`（无法确认）。枚举集合不变，协议兼容。
2. **instruction 三分支重组**，首行即操作入口，首次分支嵌入实际 registry_file 绝对路径；next_action 不变（start_or_register_application_manually）。
3. **指引置前**：README 安装节新增「直接混合（Blend）的一次性回调设置」小节（5 步 + `build\blend_callback_protk.dat` 路径示例 + config.pro 持久化 + delay_start 手动 Start + 种子放样免回调）；INSTALL.md 同步；setup 文本与 `creo_callback_status` docstring 同口径。

## 实机验证（本机 Creo 12.4，公开 MCP 接口）

- stdio 直连新服务实例查询 `creo_callback_status`（本机会话当前未加载回调）：

  ```json
  {
    "readiness": "not_loaded",
    "reason": "no_runtime_identity_record",
    "next_action": "start_or_register_application_manually",
    "instruction": "One-time setup: in Creo Auxiliary Applications register \"E:\\Projects\\MCP_CREO_MechDog\\build\\blend_callback_protk.dat\", Start it once and review its DLL prompt yourself. ..."
  }
  ```

  反馈者的原始状态（`no_runtime_identity_record`）在新语义下为 `not_loaded`（可确定未加载），instruction 首行即注册入口与实际文件路径——无须翻文档即可完成一次性设置。
- 长驻 dev 服务实例（旧代码）查询返回 `service_source_changed` 保守 unknown，源码指纹保护行为正确。
- 单测 17 项全过（新增 `test_setup_instruction_leads_with_one_time_entry`：首行句式/固定入口/路径/DLL 确认/持久化/ready 门槛/种子免回调/安全策略边界句）。
- 回归：`tools/dev_check.py` 通过、`tools/test_general.py` GENERAL_CORE_SUCCESS=1。

## 未测范围

- **脚本化注册/写 config.pro 自动启动**：按用户确认维持待评估，本轮未实现（卡内"另作方案"边界；不写配置、不隐式加载 DLL、不改安全策略）。
- 实机加载后的 `ready` 分支与 `version_mismatch`/`recorded_application_not_active` 分支文本未在本会话实测（需注册/启动回调或构造状态）；映射改动为单点三元逻辑重排，Python 枚举校验集合未变。
- 完整生命周期矩阵（升级/回退/并存）、WorkBuddy 黑盒、Creo 13.4.1.0 外部环境未测；卡保持验收中。

## 交付

提交于 `codex/bug-067-creo13-feedback`（标题 FEAT-029：回调一次性设置指引置前…；提交号见 git log）；未合 main、未发版。
