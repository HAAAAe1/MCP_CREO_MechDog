# MCP_CREO_MechDog 0.4.3 版本说明

日期：2026-10-20。版本类型：**PATCH**（0.3.7 反馈修复合集与观察性增强，无新增公开工具；工具数保持 87）。合入内容：`codex/bug-057-feedback-037` 实现线三个提交（BUG-036/057/074）+ BUG-075 登记 + 0.3.7 剩余验收文档。

## 修复

- **BUG-036（应用装配约束后元件位姿与约束不一致）**：native 组件变换读取重写（`native/advanced.cpp`、新增 `native/component_transform.h`），`component_constraints` 返回成功后位姿/矩阵与实际一致；配套隔离 C++ 对照测试（`tests/native/test_component_transform.cpp`）与实机脚本（`tools/test_component_transform.py`）。状态：位姿查询修复已回归，实机几何验证与外部 Creo 9 复验仍按卡保留。
- **BUG-057（toolkit_lock 并发准入在 Windows 报 PermissionError [Errno 13]）**：锁打开路径细化（`bridge.py` `_open_toolkit_lock`），区分共享冲突与真实竞争；本机修复回归通过，外部原环境（Win10 19045 / Python 3.13）待复验。
- **BUG-074（无进程身份的历史作业永久阻断模型恢复）**：新增 `src/creo_mechdog/legacy_recovery.py`——仅有 PID 的旧身份以**独立核验的 Windows 重启**为界：所有控制记录早于该启动才允许恢复动作，证据绑定 token 并在准入/执行前后复查；同次启动、时间不明、活动或权限未知身份继续拒绝。13 项隔离回归 + 全量单元通过；真实跨重启四动作与 WorkBuddy 未测（需操作者控制的 Windows 重启后重新 inspect）。

## 增强（观察性，不改公开契约）

- **种子兼容观察**（新增 `src/creo_mechdog/seed_compatibility.py`）：`creo_list_seeds` 输出合并 `seed_build_version`/兼容历史元数据；loft 种子任务结果附 `seed_load_evidence`（加载观察记录，不越权声称当前会话兼容）。
- **窗口/进程观察**（新增 `src/creo_mechdog/window_observations.py`；`process_snapshot` 支持外部观察注入）：状态探针附带进程窗口观察，区分隐藏/挂起窗口，辅助通道异常判读。
- **BUG-075 登记（待复现）**：Toolkit 状态探针偶发 `invalid_probe_result`（worker 退出码 1，显式 retry 恢复），见 [卡片](work-items/BUG-075.md)。

## 验收摘要

- 0.3.7 实现线：458 项单元（新增 legacy_recovery/seed_compatibility/window_observations 等 24 项）、隔离 C++、`tools/test_feedback037_modeling.py` 实机（三驱动/真实并发/关闭原件确认/回调全生命周期），见 [FEEDBACK-0.3.7-IMPLEMENTATION](validation/FEEDBACK-0.3.7-IMPLEMENTATION-2026-10-20.md)。
- WorkBuddy 黑盒 **16/16**（能力分页/圆角倒角别名/无盘接管 prepare→apply→shell 7152/真并发/回调双圆 loft），见 [WORKBUDDY_037_REMAINING_RESULT](validation/WORKBUDDY_037_REMAINING_RESULT.md)。
- 开发者补测：英寸件接管拒绝字段（`reason_code=non_millimeter_units`、`actual_units="in"`、`volume_mm3=null`）、四类型枚举（part/sheetmetal/assembly/drawing）、families 全量分页、异常候选只读 inspect（四动作受 BUG-074 保护正确拒绝），见 [补测记录](validation/WORKBUDDY-037-REMAINING-SUPPLEMENT-2026-10-20.md)。

## 环境与未测范围

- 本机 Windows x64 / Python 3.12.14 / Creo 12.4.0.0 / 匹配 SDK 与 MSVC。未测：BUG-074 真实跨重启四动作与 WorkBuddy、BUG-057 外部原环境复验、BUG-036 实机几何与外部 Creo 9、BUG-075 复现定位、FEAT-042/043/029 剩余边界（归原卡）。
- `[IMPROVEMENT 计划](development/CREO10-0.4.1-FEEDBACK-IMPROVEMENT-PLAN-2026-10-20.md)`（DEV-027 指纹归一化、DEV-030 vcvars64_env、补验收）已入库待实施，不随本版。

## 升级说明

常规安装/升级后重启目标 MCP 连接器（工具数不变，行为修复即生效）；`creo_reconcile_model` 对历史异常模型在完成一次操作者控制的 Windows 重启前保持保护性拒绝（BUG-074 语义）。

历史版本：[0.4.2](RELEASE_NOTES_0.4.2.md)、[0.4.1](RELEASE_NOTES_0.4.1.md)、[0.4.0](RELEASE_NOTES_0.4.0.md)、[0.3.7](RELEASE_NOTES_0.3.7.md)。
