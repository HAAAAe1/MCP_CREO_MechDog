# MCP_CREO_MechDog 0.4.5 版本说明

日期：2026-10-21。版本类型：**PATCH**（0.4.2/Creo 10 反馈首批处理计划：稳定性与诊断优先，无新增公开工具；工具数保持 87）。实施计划：[CREO10-0.4.2-FEEDBACK-PLAN-2026-10-21](development/CREO10-0.4.2-FEEDBACK-PLAN-2026-10-21.md)；两份反馈原件归档 [feedback-0.4.2-creo10-2026-10-21](validation/feedback-0.4.2-creo10-2026-10-21/report.md)（主报告 SHA256 `59832348…b4f07`、构建侧 `72c1a634…2990`，均与原件逐字节一致）。

## 修复与诊断

- **BUG-076（收养链路 16 MiB 元数据预算阻断真实模型，首批可定位诊断）**：外部 Creo 10/0.4.2 报真实零件（1 MB）与外部装配 adopt inspect 均撞 `Adoption metadata exceeds the 16 MiB read budget`。本版把该裸错误升级为稳定原因码 `ADOPTION_METADATA_BUDGET_EXCEEDED`，携带 `metadata_kind`（原生结果/历史登记/证据令牌/提交日志四类读取之一）、服务内相对路径、`actual_bytes`/`budget_bytes`、`failed_stage`、job/model 标识与恢复指引；同步错误返回同一 JSON 文本与 structuredContent。失败预检 job 保留结构化诊断与超限文件本体；错误收尾与轮询遇二次超限以 `failure_read_budget_exceeded`/`commit_read_budget_exceeded` 附注，不覆盖原始诊断、不破坏保护与幂等重放。**不提高限额、不重构存储**：取得原环境超限文件类别后按对应读取路径精修（原环境证据未取得前条目保持开放）。
- **FEAT-006/008（收养错误信息）**：空窗口 `NO_CURRENT_MODEL` 补齐 Python 结构化转换（保留原生 `ProMdlCurrentGet`/`-8` 原码与阶段，refusal_details 未知值如实标记，实机空窗口验证）；预检诊断覆盖整个链路——native 结果预算异常、来源核验、冲突扫描、令牌发布失败均在预检 job 上标注阶段，不再停留在 succeeded。
- **FEAT-043/044（打开后的会话信息）**：`creo_open_file` 成功结果新增 `open_file.opened_session_model`：直接对已打开句柄做单模型观察（字段与 `creo_list_session_models` 条目一致：name/model_type/is_current/origin/has_saved_origin/modified/session_model_id/query_codes，另含 `observed_at`），不另发起全量枚举；compact/full 一致。
- **FEAT-008/023（使用说明）**：README 新增"默认摘要与分页接口一览"：三个默认摘要接口（`creo_list_models`/`creo_inspect_model`/`creo_capabilities`）的 full/section/cursor 取全量方式、32 KiB 页预算与 cursor 失效语义；`creo_list_session_models` 两态 cursor（省略=实时重新采集、携带=约 10 分钟冻结快照分页，会话变化后应省略 cursor 重新查询）。

计划中 DEV-027/030 两项构建遗留已随 0.4.4 交付，本版不重复；会话擦除、FEAT-045（装配只读检查）、装配接管/reconcile、旧 DLL 目录回收按计划另期安排。

## 验收摘要

- 481 项单元（新增 `tests/unit/test_adoption_budget.py` 12 项：真实 16 MiB 边界、四类超限隔离、保护保留与幂等重放、失败收尾二次超限不覆盖原始诊断、轮询降级、NO_CURRENT_MODEL 结构化、invoke 结构化契约）+ `tools/dev_check.py` 通过（变更文件已格式化并重编译 `creo_worker.exe`）。
- 实机（本机 Windows x64 / Creo 12.4.0.0 / 匹配 SDK，stdio 直连工作区新 server 实例，空会话起步）：空窗口结构化拒绝（`reason_code=NO_CURRENT_MODEL`）、`creo_open_file` 两真实零件作业的 `opened_session_model` 字段齐全（`is_current=true`、origin/query_codes/observed_at）、未收养副本打开后正常 inspect 发布 evidence_token。见 [验证记录](validation/BUG076-FEEDBACK042-2026-10-21.md)。
- 既有边界观察（非本版回归，0.4.4 行为相同）：仅 inspect 过的 staging 模型在 `creo_reconcile_model` 中因 owners 恒空无法 `abandon_new`，暂无 MCP 清理路径；reconcile 改进属另期安排。

## 环境与未测范围

- 本机 Windows x64 / Python 3.12 / Creo 12.4.0.0 / 匹配 SDK 与 MSVC。未测：**BUG-076 原环境（Creo 10）超限文件类别、实际字节数、预检 job_id 与部署身份未取得，本机通过不外推为 Creo 10 已通过**；16 MiB 实机文件未构造（隔离回归覆盖逻辑）；装配/钣金收养路径；WorkBuddy 公开黑盒验收（建议作为发布后复核）。
- 升级后请重启目标 MCP 连接器使新诊断逻辑生效；既有会话清单快照、任务与保护语义不变。

历史版本：[0.4.4](RELEASE_NOTES_0.4.4.md)、[0.4.3](RELEASE_NOTES_0.4.3.md)、[0.4.2](RELEASE_NOTES_0.4.2.md)、[0.4.1](RELEASE_NOTES_0.4.1.md)、[0.4.0](RELEASE_NOTES_0.4.0.md)。
