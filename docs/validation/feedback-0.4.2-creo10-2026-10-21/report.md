# MCP_CREO_MechDog v0.4.2 验收报告

> **文档命名**：2026-10-20 / CREO 10 / v0.4.2 / 核心问题：**收养（adopt）链路被 16 MiB 元数据预算阻断，真实零件无法收养**
> **验收日期**：2026-10-20
> **验收对象**：MCP_CREO_MechDog v0.4.2（前两轮：v0.4.0 首轮反馈、v0.4.1 复测）
> **文档目的**：验收 v0.4.2 更新内容；反馈本轮新发现问题，供作者优化

---

## 1. 验收结论（TL;DR）

| 项目 | 结论 |
|---|---|
| 版本 | ✅ 0.4.1 → **0.4.2**（`session_status` 现携带 `server_version`，全部返回分支均带） |
| **P0：磁盘文件打开入口** | ✅ **已闭环**——`creo_open_file` 交付且质量高（实测通过，见 §3） |
| P2-1：capabilities 超限 | ✅ **已闭环**——分页化（compact 单页 ~8KB，`detail=full + section + cursor`，32KiB/页） |
| P2-2：边界显式声明 | ✅ **已闭环**——顶层新增 `support_status`（disk_open=supported / assembly_checks=planned FEAT-045 / adoption=supported_limited） |
| P2-3：版本信息埋藏深 | ✅ **已闭环**——`server_version` 随所有返回分支下发 |
| P1：装配收养 | ⚠️ 未闭环但已规划——`FEAT-045` 跟踪只读装配检查；装配打开有严格守卫（见 §5-1） |
| **新 P0'：adopt 16 MiB 预算阻断** | ❌ **本轮新发现**——真实零件（1MB 的 mx_up.prt）与装配均报 `Adoption metadata exceeds the 16 MiB read budget`，收养链路对真实模型不可用（见 §4-1） |

---

## 2. 测试环境

| 项目 | 值 |
|---|---|
| MCP 版本 | **0.4.2**，tool_count 87（较 0.4.1 +1：creo_open_file） |
| Creo | Creo Parametric 10.0.0.0（release_numeric 42） |
| 会话状态 | connected；当前窗口 HYD_CYLINDER_ASM（外部装配，modified=true），另有 9 个 MCP 托管副本零件常驻 |
| 测试文件 | `MX_PCB\mx_up.prt.7`（1,054,728 bytes）、`MX_PCB\asm_mx.asm.16` |

---

## 3. `creo_open_file` 实测（P0 闭环确认，质量高）

### 3.1 通过项

| # | 测试 | 结果 |
|---|---|---|
| 1 | 打开零件（不带版本号，自动选最高版本） | ✅ 选中 `.prt.7`（目录中最高版本），检索+显示成功，`origin_matches_selected_file: true` |
| 2 | 文件身份审计 | ✅ 提交时与完成后各记录一次 sha256（一致），`source_file_changed_during_open: false` |
| 3 | 只读契约 | ✅ `model_id=null`、`adopted=false`、无托管 revision，源文件未被改动 |
| 4 | 幂等重放（同 key 同路径） | ✅ 返回同一 job_id，未重复执行 |
| 5 | 同 key 不同路径 | ✅ 提交即拒：`Idempotency key already belongs to another open-file request` |
| 6 | 不存在路径 | ✅ 提交即拒且不建 job：`File not found`（测试用 `.prt.9` 确实不存在，行为正确） |
| 7 | 同名同类型会话冲突 | ✅ `SESSION_NAME_CONFLICT`，并附冲突模型完整信息（名称/origin/is_current/session_model_id）与恢复指引 |
| 8 | 装配打开守卫 | ✅ 会话含零件时打开装配被拒：`ASSEMBLY_REQUIRES_EMPTY_SESSION`，语义清晰，无残留文件 |
| 9 | capabilities 分页 | ✅ compact 单页可整读；`detail=full` + 7 个 section + next_cursor 翻页正常 |

### 3.2 错误报文质量（值得表扬）

`creo_get_job` 失败时返回结构化 `failed_stage`（如 `open_file_session_check`）、完整 `native_log_tail`（PHASE 级追踪）、冲突模型详情与可操作恢复指引——这是三版以来最好的错误报文，建议作为全 server 的错误报文标杆。

---

## 4. 本轮新发现问题

### 4.1 【P0'】收养预检 16 MiB 元数据预算阻断真实模型 ⭐核心问题

**现象**：

| 当前窗口模型 | adopt inspect 结果 |
|---|---|
| HYD_CYLINDER_ASM（外部装配） | `Error: Adoption metadata exceeds the 16 MiB read budget` |
| MX_UP（1MB 真实键盘键帽零件，open_file 刚成功打开） | **同样报** `Adoption metadata exceeds the 16 MiB read budget` |

**问题分析**：

1. **零件路径被阻断**：`creo_open_file` 打开了真实零件，契约指引"需要托管编辑请先 adopt"——但 adopt inspect 对这个 1MB 的零件直接撞预算失败。刚修好的"打开 → 收养 → 托管编辑"链路，在真实零件上**第二步就断了**。几何复杂度中等的真实模型（键帽类自由曲面）即触发，说明预检的元数据收集是无界的（或预算对真实模型过小）。
2. **装配路径报错误导**：装配本应被"unsupported"语义拒绝（capabilities limits 明确写着 assembly refused），实际却先进入元数据收集再撞预算——类型门控发生在重量级收集之后，报错误导 agent 去怀疑"文件太大"而非"装配不受支持"。
3. **错误again是裸文本**：无结构化错误码、无 remediation 指引，与 `creo_open_file` 的结构化报文（failed_stage + native_log_tail + 恢复指引）形成明显落差。

**建议**：

1. **类型门控前置**：收集元数据前先读 `ProMdlType`，装配/工程图直接返回 `MODEL_TYPE_UNSUPPORTED` 语义错误。
2. **证据收集分节化/有界化**：身份证据（origin/sha256/基本参数）与全量 inspection 解耦；预检只需要身份证据 + 健康特征（failed/suppressed 标志），不必一次拉全 geometry/surfaces/edges。参照 `creo_inspect_model` 的 section+cursor 模式按需取用。
3. **预算超限时报错语义化**：返回结构化 `ADOPTION_METADATA_BUDGET_EXCEEDED` + 已收集大小/预算 + 建议（如按节收集）。
4. **收养后的 inspection 快照**同样建议分节存储，避免托管成功但 `creo_inspect_model` 也超限的后续问题。

### 4.2 【P1】无会话模型清理工具，装配打开链路无法全自动闭环

- `creo_open_file` 打开装配要求会话中**零 part/assembly**；`SESSION_NAME_CONFLICT` 的恢复指引是"Close or erase it in Creo first"——但 MCP **没有任何擦除/关闭会话模型的工具**。
- 实际后果：本会话常驻 9 个 MCP 托管副本零件（C_* 系列），装配打开路径被**永久堵死**，必须用户手动在 GUI 里逐个擦除。open_file 交付的"全自动打开装配"能力，实际依赖一个 MCP 自身无法达成的先决条件。
- **建议**：新增 `creo_erase_session_model`（只擦除 modified=false 的模型、永不保存、MCP 托管模型默认拒绝并指向 reconcile 流程）；或在 `creo_open_file` 增加 `auto_prepare_session` 选项（自动擦除未修改的只读模型前明确列出清单）。

### 4.3 【P2】`creo_list_session_models` 快照在 open_file 之后不自动失效

- open_file 成功后立即调用 `creo_list_session_models`，仍可能返回 10 分钟快照的旧内容（快照语义如此设计，可理解）；但 agent 在"open → list → adopt"链路中容易拿到过期清单。建议在返回中显式标注"自 snapshot_id 以来会话已发生变化"（Toolkit 侧有 channel 时可低成本探测），或在 open_file job 结果中直接附上 opened 模型的 session 条目（当前已附 `conflicting_session_model`，成功路径可同样附 `opened_session_model`）。

### 4.4 【P3】上轮 P3-1（adopt 空窗口裸错误码 -8）未能复测

- 本轮会话始终有当前模型，无法验证空窗口路径是否已修复。从 16 MiB 裸文本错误看，adopt 家族的错误包装仍未达到 open_file 的水准，请一并处理。

---

## 5. 上轮问题闭环追踪

| 上轮编号 | 问题 | v0.4.2 状态 |
|---|---|---|
| **P0** | 无磁盘文件打开入口 | ✅ **闭环**（creo_open_file，实测通过） |
| P1-1 | adopt 契约过严（毫米/无外部依赖） | ➡️ 未变，但被 4.1 的预算问题暂时掩盖（真实模型根本走不到契约校验） |
| P1-2 | reconcile 排除装配 | ➡️ 未变；FEAT-045 已规划装配只读检查，建议 reconcile 同步纳入规划 |
| P2-1 | capabilities 超限 | ✅ **闭环**（分页化，compact ~8KB） |
| P2-2 | 边界声明不显式 | ✅ **闭环**（support_status 显式四级：supported / supported_limited / planned / not_supported） |
| P2-3 | session_status 无 server_version | ✅ **闭环**（所有分支携带） |
| P3-1 | adopt 空窗口裸错误码 | ❓ 本轮无法复测；但 adopt 出现新的裸文本错误（见 4.1） |

---

## 6. 建议优先级

| 优先级 | 事项 |
|---|---|
| **P0'** | adopt 预检重构：类型门控前置 + 证据收集分节有界化 + 预算错误语义化（§4.1） |
| P1 | `creo_erase_session_model`，打通装配打开链路（§4.2） |
| P1 | FEAT-045 装配只读检查按期落地；reconcile 同步覆盖装配 |
| P2 | open_file 成功结果附 `opened_session_model`；list_session_models 过期提示（§4.3） |
| P3 | adopt 家族错误报文对齐 open_file 标准（结构化 failed_stage + 指引） |

---

## 7. 复测方法

1. `creo_session_status` → 确认 0.4.2 + `server_version`。
2. `creo_capabilities`（compact）→ 检查 `support_status` 与 `pagination`。
3. `creo_open_file`（真实 .prt，不带版本号）→ get_job 轮询 → 确认 opened_and_displayed + sha256 双记录。
4. 同 key 重放 → 应返回同 job_id；换路径 → 应提交即拒。
5. 打开 .asm（会话含零件）→ 应得 `ASSEMBLY_REQUIRES_EMPTY_SESSION`。
6. **关键复现**：open_file 打开任意真实零件后切为当前窗口 → `creo_adopt_current_model(mode=inspect)` → 复现 `Adoption metadata exceeds the 16 MiB read budget`。

---

## 8. 亮点（本版显著进步）

- `creo_open_file` 的交付质量是三版以来最佳：契约严谨（只读、不收养、幂等、版本解析规则明确）、错误语义化、审计链完整（双 sha256 + native PHASE 日志）。
- `support_status` 四级透明度（supported / supported_limited / planned+FEAT 跟踪号 / not_supported）是 API 设计的好实践，agent 可以直接据此规划工作流而不必试错。
- capabilities 分页 + `section_counts` 让能力发现成本大幅下降。
- 三轮反馈 P0/P2 全部闭环或给出跟踪号，响应速度和诚意可见。

*本文档由 AI 助手基于 2026-10-20 对 v0.4.2 的实测调用整理。*
