# 0.3.6 版本说明

发布日期：2026-10-18。交付条目：[DEV-041](work-items/DEV-041.md)。版本类型：PATCH（兼容修复 + 文档与工程变更）。工具数不变（84）；无原生 C++ 改动。

## 修复

### BUG-059：恢复 apply 的执行前拒绝不再误标 unknown_outcome（DEV-040）

`creo_reconcile_model` 的 apply 在**原生派发之前**失败时（会话选择变更、证据过期、输入校验等），终态由 `unknown_outcome` 改为确定性 `failed`（`reason: reconciliation_refused` 等），并新增 `failure_phase` 字段：

- `before_native`：原生执行器尚未派发。此时仅在通道锁内释放**本次恢复自身的** `recovery_pending` 占位；模型状态、revision 与原 pending 作业不受影响，可直接重新 inspect→apply。
- `native_worker_started`：派发可能已开始。仍为 `unknown_outcome` 并保留全部保护，不得自动重试。

**迁移提示**：此前把该分支按 `unknown_outcome` 处理（等待恢复）的客户端，应改为按 `failed` 处理并直接重新 inspect。错误消息含 "refused" 不代表可以绕过会话指纹保护重试。compact 作业结果新增 `reason`、`failure_phase`、`recovery_pending_released` 等字段。契约文档见 [MODEL_RECOVERY.md](MODEL_RECOVERY.md)。

已测范围：隔离黑盒三场景（原生前拒绝 / 合成原生后未知 / 合成成功）与开发者协议回归（详见[收尾复核](validation/DEV-040-closeout-review-2026-10-18.md)）；真实会话切换、原生恢复与通道并发未在本轮测试。

### BUG-057 配套：隔离诊断脚本

新增 `tools/reproduce_toolkit_lock.py`（仅标准库、TemporaryDirectory 隔离，不依赖服务与配置），供外部 Windows 环境复核 `toolkit_lock` 的 `PermissionError [Errno 13]`（外部 0.3.5 报告，本机连续 10 轮未复现）。每次打开/锁定为独立观测而非重试；受控失败不构成根因结论。用法见脚本头部说明。服务锁行为本身未改变。

## 文档与台账

- 六份 0.3.5 外部反馈全部补录归档（安装与锁文件 / Creo 10 升级检查 / Creo 9 建模 / Creo 10 实机验收 / 钣金第四轮 / 曲面链路），新登记 BUG-057～062、FEAT-038～041；FEAT-034（草图弧方向）升 P1。
- 台账按"待复现 / 待核实 / 待开发 / 剩余验收 / 待规划 / 历史观察"重构分类（DEV-038/039）。
- BUG-054/055 补外部 Creo 9 与 Creo 10 实机验收通过证据；兼容矩阵更新。

## 已知问题与未测范围

- BUG-057（外部并发准入 Errno 13，待原环境用上述脚本取证）与 BUG-058（外部 Creo 9 通道 -11、无主窗口进程）开放中。
- 钣金增料（BUG-046）、草图弧方向（FEAT-034）、纯曲面链路算子（FEAT-039）等能力缺口未在本版处理，详见[台账](BACKLOG.md)。
- 本版未执行原生建模回归（无 C++ 改动）；Creo 9 实机编译与运行时未验收（本机无 SDK）；Creo 10 不做独立复测（2026-10-15 用户决定）。历史实机证据按原身份保留，不改标本版。

## 环境

本机候选检查：Windows 11 x64（26100）/ Python 3.12.14 / Ruff 0.17.0 / clang-format 23.1.3。完整记录见 [validation/RELEASE-0.3.6.md](validation/RELEASE-0.3.6.md)。
