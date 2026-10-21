# WorkBuddy 黑盒验收记录：FEAT-044/023/022（0.5.0 开发分支）

按 [WORKBUDDY_0.5.0_OPEN_FILE](../WORKBUDDY_0.5.0_OPEN_FILE.md) 逐项执行，**16/16 项均有结论**。仅通过 MCP 公开接口调用，未读取或修改源码、未运行本地测试脚本、未检查 Git 与配置文件。操作者配合两次会话清理（第二次为关闭并重启 Creo）。

## 环境与身份（公开接口）

| 项 | 值 |
| --- | --- |
| 时间 | 2026-10-20 12:03–12:46（GMT+8） |
| 连接器 | `MCP_CREO_MechDog_dev`（运行中；期间随 Creo 关闭自动重启，`launch_attempt=18`） |
| Creo | 12.4.0.0（release_numeric=44）。首段 pid 13048/17208；重启后 pid 5624/26244 |
| `server_version` | **0.4.1**（与 `creo_capabilities.version` 一致） |
| 工具数 | **87**，`creo_open_file` 在册，`unavailable_tools=[]` |
| code_root / server_entry | `E:\Projects\MCP_CREO_MechDog` / `…\server.py` |
| python | `…\.venv\Scripts\python.exe` |
| source_changed_since_startup | false（启动指纹含 `open_file.py`、`capability_pages.py`） |
| 会话指纹 | 首段 10698411998226096490；重启后 15809778616245951165 |

版本说明：0.5.0 能力已生效（87 工具、分页 capabilities、`creo_open_file`），但 `version.py` 仍报 **0.4.1**，"0.5.0"未落到版本号。按工具数与身份判据不构成阻断，记为标识不一致一处。

## 结果总览

| # | 场景 | 结论 |
| --- | --- | --- |
| 1 | 会话状态 + 版本一致性 | 通过（版本号差异见上） |
| 2 | compact 摘要页 + disk_open 支持状态 | 通过 |
| 3 | 打开既有零件（外部目录） | 通过 |
| 4 | 幂等重放 / 同键换路径 | 通过（附幂等键跨进程持久） |
| 5 | 数字版本选择（含同目录配对 + 体积） | 通过 |
| 6 | 中文与空格路径 | 通过 |
| 7 | 非法输入 4 例 | 通过 |
| 8 | 同名冲突 | 通过 |
| 9 | 完整装配打开（空会话） | 通过 |
| 10 | 非空会话开装配 | 通过 |
| 11 | 缺件装配 | 通过（错误码为 `RETRIEVE_INCOMPLETE`） |
| 12 | 打开后不接管 | 通过 |
| 13 | capabilities 分页（references/tools） | 通过 |
| 14 | 分页错误处理 | 通过 |
| 15 | 顶层 support_status | 通过 |
| 16 | 接管诊断（空窗口 / 装配） | 通过（`refusal_details` 未在错误表面出现） |

## A. 磁盘打开主链

**1）会话状态**：connected=true、`toolkit_code=0`、`current_model=""`、`current_model_code=-8`、`server_version=0.4.1`（与 capabilities 一致）。

**2）capabilities compact**：`detail="compact"`、7 个 section 目录、23 个 family 索引、`support_status.disk_open.status="supported"`、`tool_count=87`、`enabled_tool_count=87`，不含 runtime/evidence 大对象，整页约 10 KiB 量级（compact 页不返回精确字节数，量级为观测估计）。

**3）打开既有零件**：`wbopen-part-vera-01` → job `475839b601ae4e2d8b2cc081a9415082` succeeded，stage `opened_and_displayed`。
- `model_id=null`、`adopted=false`、`displayed=true`、`model_type="part"`、`origin` = 所选文件、`origin_matches_selected_file=true`。
- `identity_before` 与 `identity_after` 完全一致（99880 B、sha256 `0aa579e4…9ed65f`）→ `source_file_changed_during_open=false`，源文件字节未变有哈希证据。
- `creo_list_session_models`：`WBOPEN_V1` 在会话且 `is_current=true`。Creo 窗口实际画面未经人工目视（公开接口只给 `displayed`/`is_current`），视觉确认记为未验证。

**4）幂等**：同 key 同路径重放返回原 job `475839b6…`（时间戳不变、无二次执行）；同 key 换路径（verB 的 `.prt.2`）拒绝：`Idempotency key already belongs to another open-file request`。
- 附加发现：首次提交用 `wbopen-asm-full-01` 被拒——该 key 属开发侧历史请求。**幂等键区间跨进程持久**，同一路径的历史键长期占用，正式验收必须使用新键。

**5）数字版本**（同目录配对，用体积核对）：
- 显式版本：`t82_ft.prt.1` → `selected_file=origin=…\t82_ft.prt.1`（精确命中）。
- 同基名配对：`verB\wbopen_v1.prt`（省略版本）→ 自动选中 **`.prt.2`**（job `0f646dd56d054e48b61300213e44c88f` succeeded）；随后 `creo_adopt_current_model(mode=inspect)` 得 `volume_mm3=38400.0`、`feature_count=13`。
- 对照：`.prt.1`（verA 与"中文 目录"副本同 sha256 `0aa579e4…`）inspect 得 `volume_mm3=48000.0`、`feature_count=8`。
- 结论：省略版本选数值最高的 `.2`（80×60×8=38400），显式 `.prt.1` 保持原几何（80×60×10=48000），与文件内容一致。
- 另：`bug009_rect.prt`（目录内 .1–.25）→ 选中 `.prt.25`，证明按**数值最大**而非字典序最大。

**6）中文与空格路径**：`…\build\wbopen_tests\中文 目录\测试 零件.prt.1` → job `c5a24d9846194961a8be3d24d70ae189` succeeded，`model_name="测试 零件"`、origin 一致、`displayed=true`、身份哈希前后一致。

**7）非法输入**（全部在 job 产生前拒绝，`creo_list_jobs` 无对应条目）：
- 相对路径 → `file_path must be a Windows absolute path`
- 不存在文件 → `File not found: …; no job was created`
- 非 .prt/.asm 后缀 → `file_path must end with .prt or .asm, optionally with an explicit numeric version such as .prt.3`
- `.prt.0` → `Explicit version numbers start at 1`

**8）同名冲突**：会话已有 `WBOPEN_V1` 时开 `verB\wbopen_v1.prt.2` → job `818fac28cd7844208fb9c82f7bbbec3d` failed，`SESSION_NAME_CONFLICT: a part model with this name is already in the Creo session; the file was not retrieved`，附 `conflicting_session_model`（origin 指向 verA 的 .prt.1）。会话条目数未变（5→5）。

## B. 装配打开与保护

**9）完整装配（空会话）**：`wbopen-asm-full-a1020` → job `bdd697517e244fcaad1453842e6ba2f8` succeeded。
- `model_type="assembly"`、`displayed=true`、`component_count=2`、`model_id=null`、`adopted=false`、origin 匹配。
- 省略版本自动选 `.asm.3`（该目录 .1/.2/.3 中最高）——提示词未要求的装配版本选择顺带验证通过。
- 会话：`WBOPEN_ASM`（is_current）+ `C_2A751644754741DB_0/1`，子件 origin 均在 asm_full 目录。

**10）非空会话开装配**：开 `asm2_missing\wbopen_asm2.asm` → job `9c94e3bdf9d944a4bea563614eef29f1` failed，`ASSEMBLY_REQUIRES_EMPTY_SESSION`、`failed_stage=open_file_session_check`，未检索文件，会话未变。

**11）缺件装配**：空会话 + 子件全部可达副本移走后，开 `asm2_missing\wbopen_asm2.asm`（`.asm.3`）→ job `bce39470a378479fa7eb049dcc067848` failed。
- 错误为 **`RETRIEVE_INCOMPLETE`**（提示词预期写作 `RETRIEVE_FAILED`，实际码不同，建议同步文案）：`the assembly was retrieved but 1 of 1 components did not resolve (names unavailable, marked unknown)`。
- `component_count=1`、`missing_component_count=1`、`missing_components={count:1,total:1,names:"unknown"}`、`displayed=false`、`loaded=true`。
- `remaining_session_models=[WBOPEN_ASM2]`（`modified=true`，残留半成品对象），`nothing was saved or erased`，`failed_stage=open_file_component_check`。
- 前置发现：若不隔离，子件会被 **Creo 工作目录 `build/creo_session/`** 的副本解析掉（同素材首次尝试 succeeded、`component_count=1`、子件 origin 指向该目录）；缺件素材必须同时清掉工作目录与受管输出目录的副本。本轮隔离的两份副本测后已按原 sha256 恢复。

**12）打开后不接管**：对刚打开的零件调 `mode=inspect` → `available=true`、`healthy=true`、`millimeter_units=true`、`dependency_free=true`，返回 `model_id`（adopt_pending）与 `evidence_token`；未 apply，故未创建受管副本。
- `creo_open_file` 本身不建受管模型：各轮会话清单 `model_id` 与 `adopted_copy_model_id` 全为 null。

## C. capabilities 分页与诊断

**13）分页**：`detail=full, section=references, limit=5` → 第 1 页 5/9 `complete=false` + cursor；续页 `offset=5, returned=4, complete=true`，无重复无遗漏。`section=tools` → `total=87`，`limit=50` 分两页 50+37 收尾 `complete=true`（键 0–86 连续）。每页带 `page_bytes=32768` 上限，实际页未超限。

**14）错误处理**：
- 未知 section → `Unknown section 'not_a_section'; choose one of [...7 项]`
- 非法 cursor → `Invalid query cursor`
- compact 传 section 或 cursor → `compact returns a single summary page; use detail=full with section/cursor`
- 跨 section 误用 cursor（references cursor 配 section=tools）→ 拒绝；文案为通用 `Capabilities cursor is invalid or the snapshot changed/expired; query again without cursor`，未指出 section 不匹配。

**15）顶层 support_status**：`disk_open=supported`、`session_enumeration=supported`、`adoption=supported_limited`、`assembly_checks=planned`（tracking FEAT-045）、`external_file_managed_edit=not_supported_through_open`。

**16）接管诊断**：空窗口 inspect → `NO_CURRENT_MODEL: … (ProMdlCurrentGet(&current) returned -8 PRO_TK_BAD_CONTEXT during adoption_inspect)`；装配为当前模型时 → `unsupported_model_type: only part or sheetmetal models can be adopted; …`（对应 job `e07e97c3abe9467a9341c2d7e360c277` failed，`failed_stage=adoption_inspect`）。稳定 reason_code 以错误前缀可见；**`refusal_details`（单位、依赖/健康标记）未出现在 MCP 错误表面**，该项仅部分可确认。

## 附带发现（非提示词条目）

1. **幂等键跨进程持久**：历史键会长期占用同名路径，验收需用新键。
2. **`session_model_id` 不可靠**：重启后的新会话中，`WBOPEN_V1` 与残留 `WBOPEN_ASM2` 同时返回 `session_model_id=0`；上一会话也出现过装配与其子件同值（5242880）。与工具说明"仅作临时发现提示"一致，但 0/重复值会让使用者误判为同一对象。
3. **缺件素材易被搜索路径掩盖**：`build/creo_session/` 与 `models/<hash>/output/` 的副本会让"缺件装配"照常成功，验收素材需连同这两处一起隔离。

## 未验证 / 边界

- Creo 窗口的实际视觉显示（仅由 `displayed=true` 与 `is_current=true` 推断，未人工目视）。
- `refusal_details` 结构化字段（公开接口未返回）。
- 真实并发（全部串行调用，不主张并发结论）。
- 显示失败注入、通道断连/超时 unknown_outcome、钣金件打开。
- `asm_mx.asm.16` 原场景仍为"待原环境复验"，本轮未涉及，不以本机样件替代。

## 会话残留

验收结束后由操作者在 Creo 中执行「关闭窗口 + 拭除未显示的」清理，`creo_list_session_models` 复核为 `total=0`、`complete=true`，`creo_session_status` 为 connected=true、`current_model_code=-8`（空窗口、Creo pid 5624 未重启）。清理前残留为 `WBOPEN_V1`（只读打开）与 `WBOPEN_ASM2`（第 11 项的残留半成品装配，`modified=true`，未保存未擦除）。被临时移走的子件 `c_ccef2bea0ff94c1b_0.prt.1` 已按原 sha256（`028f7418…608e`）恢复到 `build/creo_session/` 与 `models/ce80637cf3134219b7a46d0055aac4f3/output/`。

补充观察：拭除前后 `session_fingerprint` 保持 `15809778616245951165` 不变，说明该指纹标识连接/进程会话而非模型集合，不能用来判断会话内容是否变化。
