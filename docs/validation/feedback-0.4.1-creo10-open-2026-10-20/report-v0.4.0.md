# MCP_CREO_MechDog 问题反馈

> **文档命名**：2026-10-18 / CREO 10 / v0.4.0 / 核心问题：MCP 无法打开磁盘既有模型文件（装配不可收养）
> **反馈日期**：2026-10-18
> **反馈对象**：MCP_CREO_MechDog 作者
> **文档目的**：汇总本次实际使用过程中发现的问题，供作者优化参考

---

## 1. 测试环境

| 项目 | 值 |
|---|---|
| MCP 服务端版本 | **0.4.0**（`is_prerelease: true`，current = latest = 0.4.0） |
| Creo 版本 | Creo Parametric **10.0.0.0**（`release_numeric: 42`） |
| 操作系统 | Windows（win32） |
| Creo 进程 | parametric.exe (pid 46248) + xtop.exe (pid 72884)，安装路径 `D:\Program Files\PTC\Creo 10.0.0.0\` |
| Toolkit 连接 | `connected: true`，`toolkit_code: 0`，连接稳定 |
| 会话内模型 | 无（`current_model_code: -8`，窗口无模型） |

连接层面一切正常，本次问题**全部集中在"既有外部文件入口缺失"这一能力边界上**。

---

## 2. 复现路径

1. 用户请求：通过 MCP_CREO_MechDog 在 Creo 中打开工作空间内既有装配 `MX_PCB\asm_mx.asm.16`（文件确认存在）。
2. 会话已连接、Creo 已启动（如上表）。
3. 在全部工具中寻找"从磁盘路径打开/检索模型"的入口 → **不存在**。
4. 尝试迂回路径（adopt / assemble_component）→ 均被契约排除（见下文证据）。
5. 结论：该需求在 v0.4.0 上**无法通过 MCP 完成**，只能回退到 Creo GUI 手动打开。

---

## 3. 核心问题（P0）：无"从磁盘打开既有模型"的工具入口

### 3.1 现象

MCP_CREO_MechDog v0.4.0 的全部工具中，**没有任何一个工具接受磁盘文件路径（file_path）作为参数**来打开/检索既有模型。用户在磁盘上的存量模型（.prt / .asm）无法经由 MCP 进入 Creo 会话，也无法进入 MCP 的托管体系。

### 3.2 证据链（逐项实测核实）

| # | 检查项 | 结果 |
|---|---|---|
| 1 | `creo_capabilities` 全文（105,526 字符，已完整读取并检索） | 能力范围声明为 `"scope": "MCP-owned native part, sheetmetal, assembly and drawing models"`——所有模型操作均以 MCP 托管 `model_id` 为对象，无 file_path 入口 |
| 2 | ToolSearch 关键词检索（open / retrieve / import / display / file 等） | MCP_CREO_MechDog 命名空间内**零命中**；命中结果全部来自其他 MCP（SolidPilot 等） |
| 3 | `creo_adopt_current_model`（最接近的入口） | 仅能收养**当前窗口已打开**的模型，且文档明确限定 `"Supported: independent part/sheetmetal with millimeter units, no external dependencies and no failed/suppressed features"`——**装配明确不支持** |
| 4 | `creo_assemble_component`（装配入口） | 仅接受 `"Insert a revision snapshot of a verified MCP part/sheetmetal model"`，来源必须是托管 `source_model_id`，**不接受磁盘路径** |
| 5 | `creo_refresh_model` / `creo_inspect_model` / `creo_dump_feature_tree` | 均要求 `model_id`（托管模型），不能作用于会话中任意打开的模型 |

### 3.3 影响场景

- 存量模型（尤其历史装配）无法纳入 MCP 自动化流程，"逆向分析 → 托管重建"链路在第一步即断裂。
- 用户被迫在 Creo GUI 手动打开文件，之后 MCP 仍无法接管（inspect/refresh 等只认托管 model_id；adopt 又不支持装配）→ 形成**"打开了也管不了"的空窗**。
- 与同类 CAD MCP（如 SolidPilot 的 `open_document` 支持原生格式按路径直接打开）相比，存在明显的入口能力差距。

### 3.4 改进建议

1. **新增 `creo_open_file`（或 `creo_retrieve_model`）**：接受绝对磁盘路径，用 ProToolkit `ProMdlRetrieve` 将既有模型检索进会话并显示。
   - 建议区分两条路径：**只读检入**（仅进入会话供 GUI 查看）与**托管收养**（进入 MCP 托管体系，走既有 evidence/idempotency 契约）。
   - 收养前返回身份证据（origin path、sha256、live inspection），与 `creo_adopt_current_model` 的 FEAT-042 契约风格保持一致。
2. **扩展 adopt 支持装配**：至少提供**只读 inspection adoption**（组件树、per-component transform、mates 快照），满足"打开 + 审计"类需求；写操作可继续排除。

---

## 4. 次要问题

### P1-1 `creo_adopt_current_model` 契约过严，真实存量零件难以满足

- 限定"毫米单位、无外部依赖、无失败/抑制特征"。真实历史零件常见英寸单位、外部参考（骨架/坐标系引用）——均会被拒。
- **建议**：单位不符时给出明确、可操作的报错（含当前单位与转换指引），而非笼统 unsupported；有外部依赖时**列出依赖清单**，提示用户先收养依赖项。

### P1-2 装配/工程图在 reconcile 中也被排除

- `creo_reconcile_model` 明确 `"assembly/drawing rejected"`。一旦未来放开装配收养，恢复/对账链路需同步覆盖，否则装配托管将成为"只进不出"的单向门。

### P2-1 `creo_capabilities` 单次输出过大（本次实测 105,526 字符）

- 超出 LLM 单次工具结果上限，被宿主截断落盘为文件，agent 需要"读文件 + grep"才能完整消费，显著增加发现能力边界的成本。
- **建议**：仿照 `creo_inspect_model` 的 `detail` / `section` / `cursor` 分页机制，提供 compact 摘要（工具清单 + 关键限制一句话）+ 按需分节详查。

### P2-2 工具命名可发现性

- 语义检索"open / retrieve / import file"无法命中任何 MechDog 工具，agent 只能通读全量 capabilities 才能确认"没有此能力"。若后续加入 open 类工具，建议命名包含 open/retrieve 等通用关键词；同时在 capabilities 顶层显式声明 *"不支持打开磁盘外部文件"*，把边界从隐式（"MCP-owned"措辞）变为显式，避免每个 agent 重复踩坑。

### P2-3 版本信息位置过深

- 服务端版本（0.4.0）埋在 capabilities JSON 深层。建议在 `creo_session_status` 返回中直接携带 `server_version`，便于问题反馈时快速对齐版本。

---

## 5. 做得好的点（一并反馈）

- **会话连接非常稳**：Toolkit 探针 9 秒预算内返回，`creo_process_snapshot` 附带 pid/进程镜像路径，能明确区分"IPC 失联"与"进程退出"，排障体验好。
- **契约设计严谨**：adopt/reconcile 的 evidence_token + idempotency_key + revision 乐观锁设计，对"AI 操作 CAD"这类高风险场景是正确的防线，值得保持。
- **限制声明总体诚实**：`release_status` 直接承认 "requested complete coverage has not been achieved"，不夸大能力。

---

## 6. 问题优先级汇总

| 优先级 | 问题 | 建议动作 |
|---|---|---|
| **P0** | 无磁盘文件打开/检索入口 | 新增 `creo_open_file`，区分只读检入与托管收养 |
| P1 | adopt 不支持装配、契约过严 | 装配只读收养 + 明确的单位/依赖报错指引 |
| P1 | reconcile 不覆盖装配 | 与装配收养同步规划恢复链路 |
| P2 | capabilities 105KB 超限 | 分页/分节查询机制 |
| P2 | 工具命名可发现性 + 边界声明不显式 | 命名规范 + 顶层显式 limitation |
| P2 | 版本信息埋藏深 | session_status 携带 server_version |

---

*本文档由 AI 助手基于 2026-10-18 实际操作过程整理，所有证据均来自当日对 v0.4.0 工具的实测调用与 `creo_capabilities` 全文核实。*
