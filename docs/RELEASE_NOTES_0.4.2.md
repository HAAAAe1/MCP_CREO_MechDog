# MCP_CREO_MechDog 0.4.2 版本说明

日期：2026-10-20。版本类型：**PATCH（用户 2026-10-20 明确指定并弃用开发期 0.5.0 编号；包含新增公开工具，按版本约定本应为 MINOR，遵用户指定作为本次例外）**。工具数 86 → **87**。

本版为 v0.4.1 / Creo 10 反馈的整体交付，实施范围与核对结论见[反馈处理计划](development/CREO10-0.4.1-FEEDBACK-PLAN.md)与[反馈核对](validation/FEEDBACK-0.4.1-CREO10-2026-10-20.md)（缺口定性为新增能力需求而非 0.4.1 回归）。

## 新增

- **FEAT-044 `creo_open_file(file_path, idempotency_key)`**：把磁盘既有 `.prt` / `.asm`（含显式 `.N` 数字版本）**只读检索进当前 Creo 会话并显示**。显式版本精确打开；省略版本选择目录内最高数字版本（按数值而非字典序）；无数字版本才用无后缀文件。保护：同名同类型会话模型拒绝（`SESSION_NAME_CONFLICT`）；装配要求会话无零件/装配（`ASSEMBLY_REQUIRES_EMPTY_SESSION`）；前置检查与检索在同一 Toolkit 通道内完成。缺件装配明确失败：Toolkit 检索对缺件不报错，服务以组件完整性核对补上——`RETRIEVE_INCOMPLETE` 报告未解析组件计数（清单不可得时标 unknown）与残留会话对象，不显示、不擦除、不保存。显示失败与检索失败分别报告；源文件身份（sha256）提交与收尾各记录一次，执行期间变化如实标注。成功返回 `model_id=null`、`adopted=false`，不创建受管版本；幂等键跨进程持久，同键同路径重放原 job、换路径拒绝。
- **FEAT-023（capabilities 部分）`creo_capabilities` 摘要与分页**：默认返回 compact 摘要页（实测约 10 KB，旧全量 106 KB），含顶层 `support_status`、section 目录与 families 索引；`detail=full` 按 `overview/tools/families/references/seeds/evidence/runtime` 分节分页（`limit`/`next_cursor`），单页 ≤32 KiB，进程内冻结快照 600 秒，cursor 失效/过期/跨快照明确拒绝；单条超预算输出 oversize 标记，不静默截断。**迁移**：0.4.2 之前该工具返回全量文档，旧消费者需按 section 遍历（见 README 安装节）。

## 改进

- **FEAT-022**：`creo_session_status` 全部返回分支统一携带 `server_version`（capabilities 顶层 `version` 原有）。
- **FEAT-006/008（接管诊断）**：空窗口 inspect 返回 `NO_CURRENT_MODEL` 前缀错误（保留 `ProMdlCurrentGet` 调用名与 -8/`PRO_TK_BAD_CONTEXT` 原码）；接管拒绝携带稳定 `reason_code`（`unsupported_model_type` / `non_millimeter_units` / `external_dependencies` / `unhealthy_features` / `managed_output` / `already_adopted` / `snapshot_required` / `session_name_conflict`）与结构化 `refusal_details`——实际单位可靠取得时给出、未知时显式标记，依赖清单与逐特征健康原因标 unknown，不补造。装配等 native 先于 live 摘要的拒绝同样转结构化返回（不留 staging 登记，preflight job 保留证据）。
- **FEAT-008**：capabilities 顶层新增 `support_status` 支持状态表（磁盘打开 / 会话枚举 / 接管 / 装配检查 FEAT-045 planned / 外部文件受管编辑边界），能力边界从"MCP-owned"隐式措辞变为显式声明。
- **FEAT-043**：`creo_list_session_models` 描述补写 `session_model_id` 可为 0 或跨类型重复（定位用 name+model_type）、`session_fingerprint` 标识连接/进程会话而不随会话内容变化。

## 验收摘要

- 单元 **434 项**（新增 23：open_file 13、capability_pages 8、adoption 结构化拒绝 2）、`tools/dev_check.py` 无语言回归、匹配 Creo 12.4 SDK 构建通过。
- 开发者实机（Windows x64 / Creo 12.4.0.0）creo_open_file 12 场景全过：完整装配（2/2 组件）、隔离缺件装配（`RETRIEVE_INCOMPLETE` 2/2，用户监督复验）、显式与最高数字版本（体积级核对）、同名冲突、非空会话拒绝、中文空格路径、幂等重放、非法输入、源文件身份前后一致；MCP 层 stdio 直连验证 compact/分页/`server_version`/稳定原因码。证据：[FEAT-044-live-2026-10-20](validation/FEAT-044-live-2026-10-20.md)。
- WorkBuddy 黑盒 **16/16 通过**（含体积级版本选择、装配省略版本选 `.asm.3`、`bug009_rect` 数值最大选 `.25`、分页遍历与错误处理）：[WORKBUDDY-0.5.0-open-file-2026-10-20](validation/WORKBUDDY-0.5.0-open-file-2026-10-20.md)（文件名保留验收当日开发期编号）。
- 既有能力回归：原生 general 套件通过（见[发布核对](validation/RELEASE-0.4.2.md)）。

## 环境与未测范围

- 实机验收环境：Windows x64 / Python 3.12.14 / Creo Parametric 12.4.0.0（release_numeric=44）/ 匹配 Toolkit SDK 与 MSVC。Creo 9 实机编译与运行时未验收（本机无 SDK）；Creo 10 独立复测按用户 2026-10-15 决定不作为发布门槛，原反馈 `asm_mx.asm.16` 场景保持"待原环境复验"，不以本机样件替代。
- 未测：显示失败注入、通道断连/超时 unknown_outcome（open_file 路径）、真实并发、钣金件打开、`.asm` 数字版本显式选择实机（黑盒已顺带覆盖装配省略版本）、Creo 窗口视觉显示（黑盒以 `displayed`/`is_current` 判断）、外部 Creo 13 环境。FEAT-044/023（capabilities 部分）保持验收中。
- 并发边界不变：单一 Toolkit 通道，忙碌立即拒绝不排队（BUG-009 现状）；装配受管编辑与 reconcile 仍排除（FEAT-045 后续规划）。

## 升级与迁移

1. 常规安装/升级后**重启目标 MCP 连接器**：工具数从 86 变 87，运行实例不随磁盘源码热替换。
2. `creo_capabilities` 默认返回 compact 摘要页；依赖旧全量返回的脚本改为按 `detail=full&section=...&cursor` 遍历。
3. `creo_open_file` 幂等键持久保存于安装目录 `open_file/`，复用历史键会取回原 job；每轮任务使用新键。
4. 缺件装配素材注意：Creo 会按搜索规则从工作目录（`build/creo_session/`）与受管输出目录解析子件副本，验证"缺件"需连同这些副本一起隔离。

历史版本：[0.4.1](RELEASE_NOTES_0.4.1.md)、[0.4.0](RELEASE_NOTES_0.4.0.md)、[0.3.7](RELEASE_NOTES_0.3.7.md)、[0.3.6](RELEASE_NOTES_0.3.6.md)。
