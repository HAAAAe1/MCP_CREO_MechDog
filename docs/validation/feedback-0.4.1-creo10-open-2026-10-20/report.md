# MCP_CREO_MechDog 更新验收报告（v0.4.1）

> **文档命名**：2026-10-20 / CREO 10 / v0.4.1 / 核心问题：**更新后仍无法从磁盘打开既有模型文件，P0 未闭环**
> **验收日期**：2026-10-20
> **验收对象**：MCP_CREO_MechDog v0.4.1（上一轮反馈版本 v0.4.0）
> **文档目的**：基于 2026-10-18 反馈（`2026-10-18_CREO10_v0.4.0_MCP无法打开磁盘既有模型文件.md`）的验收复测，问题未闭环项 + 新发现问题，供作者继续优化

---

## 1. 验收结论（TL;DR）

| 维度 | 结论 |
|---|---|
| 版本升级 | ✅ 已更新：0.4.0 → **0.4.1**（`is_prerelease: true`，current = latest） |
| 会话连接 | ✅ 稳定（Toolkit connected，进程快照正常） |
| 新增能力 | ✅ 已交付：`creo_list_session_models`（会话模型只读清单）+ adopt `prepare` 模式（未保存模型收养） |
| **P0 核心问题（磁盘文件打开入口）** | ❌ **未修复**——仍无任何接受磁盘路径的工具，"打开磁盘既有装配 asm_mx.asm.16" 依旧无法通过 MCP 完成 |
| 上轮 P1/P2 问题闭环 | ❌ 大部分未闭环（详见第 4 节追踪表） |

---

## 2. 测试环境

| 项目 | 值 |
|---|---|
| MCP 版本 | **0.4.1**（v0.4.0 → v0.4.1） |
| Creo | Creo Parametric **10.0.0.0**（`release_numeric: 42`） |
| 工具总数 | 86（`tool_count: 86`，较上轮增加） |
| 会话状态 | connected，窗口无模型（`current_model_code: -8`） |
| 目标文件 | `MX_PCB\asm_mx.asm.16`（存在，装配） |

---

## 3. v0.4.1 新增能力验收

### 3.1 `creo_list_session_models`（新工具）✅ 可用

- 实测调用：返回 `models: []`（会话确为空）、`total: 0`、`complete: true`、`session_fingerprint`、`snapshot_id`、`expires_in_seconds: 599`。
- 设计正确：只读清单、冻结分页快照、不加载/保存/激活/收养，与文档声明一致。
- **但**：这只是**发现层**（发现"会话里已有什么"），不是**加载层**（把磁盘文件放进会话）。用户打开文件这一步仍然只能靠 Creo GUI。

### 3.2 `creo_adopt_current_model` 升级 ✅ 功能已扩展

- 新增 `prepare` 模式：未保存模型可先 prepare（冻结快照，`revision=0`，不切换窗口）→ apply 确认（`revision=1`）。
- 新增 `inspect(model_id=...)`：续期 600 秒证据令牌，无需重复复制。
- 幂等契约保持：不同 key 分两步、同 key 重放不重复执行。

### 3.3 收养范围未变 ❌

能力清单原文（v0.4.1）仍为：

> `"supported": "independent part/sheetmetal, millimeter units, no external dependencies, healthy features"`
> `"limits": "assembly/drawing, non-millimeter units, dependent or unhealthy models are refused"`

**装配依然无法收养**——即使用户手动打开 asm_mx.asm.16，MCP 依然无法接管。

---

## 4. 上轮反馈问题闭环追踪

| 上轮编号 | 问题 | v0.4.1 状态 |
|---|---|---|
| **P0** | 无磁盘文件打开/检索入口（file_path 工具缺失） | ❌ **未闭环**。全文检索 capabilities + 多轮 ToolSearch（open/retrieve/load/import/activate/display 等关键词）确认：86 个工具中仍无 file_path 参数入口；scope 仍为 "MCP-owned native ... models" |
| P1-1 | adopt 契约过严（毫米单位/无外部依赖限定） | ❌ 未闭环，限制原文一字未改 |
| P1-2 | reconcile 排除装配/工程图 | ❌ 未闭环，收养仍拒绝 assembly/drawing |
| P2-1 | `creo_capabilities` 输出超限（上轮 105,526 字符） | ❌ 未闭环，**反而增大到 106,380 字符**，仍超宿主单次工具结果上限 |
| P2-2 | 工具命名可发现性 / 边界声明不显式 | ⚠️ 部分改善：新工具命名规范、可被语义检索发现；但顶层仍无显式 "不支持打开磁盘外部文件" 声明，边界依旧只由 "MCP-owned" 措辞隐式表达 |
| P2-3 | 版本信息埋藏深（session_status 无 server_version） | ❌ 未闭环，`creo_session_status` 返回中仍无 `server_version` 字段 |

---

## 5. 本轮新发现问题

### P3-1 adopt 空窗口报错为裸 Toolkit 错误码，无可读指引

- 复现：会话无模型时调用 `creo_adopt_current_model(mode=inspect)`，返回：
  `Error: Toolkit call ProMdlCurrentGet(&current) failed with code -8 during adoption_inspect`
- 问题：`-8` 对 agent 不可读——无法判断这是"当前窗口无模型"还是连接故障。上轮反馈中特别称赞过的 `creo_session_status` 进程快照排障体验，在 adopt 入口没有延续。
- **建议**：包装为语义化错误（如 `NO_CURRENT_MODEL: switch to a model in Creo first`），并提示可先用 `creo_list_session_models` 查看会话清单。

### P3-2 capabilities 体积不降反升，与分页化建议背离

- 上轮建议按 section/cursor 分页；v0.4.1 体积从 105,526 → 106,380 字符，仍超限被宿主截断落盘。agent 每次都要"读文件 + grep"才能确认能力边界，发现成本未降低。

---

## 6. 建议（按优先级）

| 优先级 | 事项 | 说明 |
|---|---|---|
| **P0** | 新增 `creo_open_file`（file_path 参数） | 用户最高频诉求：把磁盘存量模型（尤其 .asm）检索进会话。建议分"只读检入"与"托管收养"两路；收养延续 FEAT-042 证据契约。若暂不开放收养，至少提供检入显示，让 `creo_list_session_models` + GUI 切换形成完整闭环 |
| P1 | 装配收养（至少只读 inspection adoption） | 组件树/transform/mates 快照；配合 `creo_reconcile_model` 同步覆盖装配恢复链路 |
| P1 | adopt 契约细化 | 非毫米单位/有外部依赖时返回明确可操作错误（含单位值、依赖清单），而非笼统 unsupported |
| P2 | capabilities 分页/分节 | 建议 compact 摘要 + `section`/`cursor` 详查（与 `creo_inspect_model` 一致） |
| P2 | 顶层显式 limitation | 在 capabilities 顶层声明"不支持从磁盘打开外部文件"，避免每个 agent 重复踩坑 |
| P2 | session_status 携带 `server_version` | 问题反馈时快速对齐版本 |
| P3 | adopt 报错语义化 | 见 P3-1 |

---

## 7. 复测方法（供作者或后续 agent 复现）

1. `creo_session_status` → 确认 connected、无模型。
2. `creo_capabilities` → 检索 `version`（应为 0.4.1）、`tool_count`（86）、检索 `open|retrieve|file_path|disk` → 确认无磁盘打开工具。
3. `creo_list_session_models` → 确认返回空清单 + 快照元数据。
4. `creo_adopt_current_model(mode=inspect)` → 复现 P3-1 裸错误码。
5. 尝试定位任意接受绝对路径的工具 → 不存在。

---

## 8. 做得好的点（延续上轮）

- 新增工具契约设计依然严谨：`creo_list_session_models` 的快照冻结 + 10 分钟过期 + "Integer session IDs are transient discovery hints, never adoption identities" 的声明，避免了把瞬时会话 ID 误用为托管身份的经典陷阱。
- `prepare` 模式把"未保存模型"这个真实场景补上了，且明确"prepare 不切换窗口、apply 才显示"，副作用控制到位。
- 限制声明总体诚实，`release_status` 仍如实标注 pre-release。

---

*本文档由 AI 助手基于 2026-10-20 对 v0.4.1 的实测调用与 capabilities 全文核实整理。*
