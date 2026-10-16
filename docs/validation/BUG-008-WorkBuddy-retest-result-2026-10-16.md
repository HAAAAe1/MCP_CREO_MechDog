# BUG-008 retry 修复后的 WorkBuddy 定向复验结果（2026-10-16）

- 执行方：WorkBuddy（仅通过已连接 MCP 工具黑盒验收；未查看/分析/修改源码，未读取本机配置，未运行本地脚本，未检查系统进程，未清除 reservation/pending_job，未自行关闭 Creo）
- 测试提示词：`docs/validation/BUG-008-WorkBuddy-retest.md`
- 上一轮失败报告：[BUG-008-WorkBuddy-acceptance-2026-10-15.md](BUG-008-WorkBuddy-acceptance-2026-10-15.md)
- 服务版本：`creo_capabilities.version` = `0.3.1`；`code_root` = `E:\Projects\MCP_CREO_MechDog`
- 时区：UTC（`Z`）。测试机在 00:23Z–00:55Z 之间**非计划重启**（用户误关机），因此本轮数据分“重启前 / 重启后”两段。
- 结论概览：**单次 retry、真实重叠 retry、实时连接、独立建模、未知保护均通过；结构化失败/人工处理符合预期；自动启动未通过（本次只能记“安全停止，需要人工处理”）；历史故障链未验证。**

> 关键字：`creo_startup_status(retry=true)` 不再出现上一轮的 `Error executing tool` 无明细错误；本轮始终返回**可解释 JSON**，状态机可见 `checking → waiting_for_connection → ready`。

---

## 步骤 1：运行身份与指纹（通过）

`creo_capabilities`（无输入；重启前 00:21Z、重启后 00:55:22Z 各一次）：

| 字段 | 值 |
| --- | --- |
| `version` | `0.3.1` |
| `runtime.code_root` | `E:\Projects\MCP_CREO_MechDog` |
| `runtime.server_entry` | `E:\Projects\MCP_CREO_MechDog\server.py` |
| `runtime.source_changed_since_startup` | `false`（两次均 false，无源码漂移） |
| `scheduling.native_channels` | `1` |
| `scheduling.disconnect_watchdog_seconds` | `20` |
| `scheduling.admission` | `reject_busy_without_creating_a_job` |
| `tool_count` / `enabled_tool_count` | `82` / `82`；`unavailable_tools=[]` |
| `startup.automatic_by_default` | `true` |

指纹对照（`runtime.source_fingerprints_at_startup`，两次均一致）：

| runtime 指纹键 | 预期 SHA256 | 实测 | 结论 |
| --- | --- | --- | --- |
| `server.py` | `8c9db166d313793842b69d59f9f65f59a4c35b3998dde5709843f34cee37ba62` | 同 | ✅ 匹配 |
| `creo_startup.py` | `957108354ec952d5d6864f976f8144d9a21eea9643829210d3c415097fbef85c` | 同 | ✅ 匹配 |
| `src/creo_mechdog/startup_state.py` | `48a54c888a5532d4feba2c35735695e7fb6d175c801e1f52de1113902ebdb4fb` | 同 | ✅ 匹配 |

- 附加指纹（未在提示词预期表中，仅记录）：`src/creo_mechdog/recovery.py` = `f64bc43164e7e75a51b7be1f29e152a5ad588a71c4f055f7cf549f92a4180e4f`；`native/result_delivery.h` = `fb6da37ac0a591f94ec8bbe4fcdc02b37f1ef527de26b7c8a2410a3907130220`。
- coordinator PID 变化：`6900`（重启前）→ `5188`（重启后，Creo 关闭）→ `11888`（人工打开 Creo 后）。
- commit / SDK / 宿主构建身份：接口未提供 → **无法确认**（不据 0.3.1 判定已更新，而以指纹匹配为准）。

**结果：通过。**

---

## 步骤 2：单次 `creo_startup_status(retry=true)`（通过）

三种会话状态下各执行一次；**均返回可解释 JSON，无 `Error executing tool`**。

### 2A 重启前，Creo 未运行（历史不可读）
- 调用 00:22:02Z；轮询 00:22:10Z → 终态 `selection_required`，`updated_at=2026-10-16T00:22:06.144364Z`，`coordinator_pid=6900`，`connected=false`，`retry_allowed=true`。
- 记入步骤 6 的结构化失败口径。

### 2B 重启后，Creo 未运行（历史不可读）
- 调用 00:55:56Z 之后；终态 `selection_required`，`updated_at=2026-10-16T00:56:12.746521Z`，`coordinator_pid=5188`，`automatic_launch_allowed=false`。
- 记入步骤 6 的结构化失败口径。

### 2C 人工打开 Creo 后的已有会话（本步骤的通过项）
- 起始 01:11:13.445Z；状态推进：`checking` → `waiting_for_connection`（`01:11:17.111603Z`，`remaining_budget_seconds=296.4`，`phase_remaining_budget_seconds=116.5`）→ `ready`。
- 终态：`state=ready`、`connected=true`、**`verified_at=2026-10-16T01:11:21.988006Z`**（本次验证时间）、`verification_age_seconds=1.86`、`stale=false`、`coordinator_pid=11888`。
- `native`：`toolkit_code=0`、`release_numeric=44`、`worker_exit_code=0`、`disconnect_code=0`。
- 终态 `message`：`Existing Toolkit connection verified; startup history remains untrusted and automatic replacement is disabled`。
- 未出现旧 `ready` 冒充本次 retry 成功后再倒退的现象。

**结果：通过。**

---

## 步骤 3：真实重叠 `retry=true`（通过，真实并发已实施）

### 3A 重启前，Creo 未运行
- 起始 00:22:17Z，同批两个 `retry=true`。
- 返回 1：`state=checking`，`connected=false`，`retry_allowed=false`。
- 返回 2：`state=checking`，**`coordinator_running=true`**、`snapshot=true` → 第二个调用观测到第一个已在推进，**确认真实重叠**。
- 终态（轮询 00:22:25Z）：`selection_required`，`updated_at=2026-10-16T00:22:20.815647Z`，`coordinator_pid=6900`，两端同值，无明细泄漏。

### 3B 人工打开 Creo 后，已有会话（本步骤的通过项）
- 起始 01:11:29.475Z，同批两个 `retry=true`。
- 返回 1：`state=checking`、`retry_allowed=false`。
- 返回 2：`state=checking`、**`coordinator_running=true`**、`snapshot=true` → 真实重叠。
- 中间态 01:11:33.107442Z：`waiting_for_connection`，`remaining_budget_seconds=296.3`，`coordinator_running=true`。
- 终态 01:11:38.016654Z：`state=ready`、`connected=true`、**`verified_at=2026-10-16T01:11:38.016654Z`**、`verification_age_seconds=2.09`、`stale=false`、`coordinator_pid=11888`、`native.toolkit_code=0`。
- 两端最终 `ready`，**无“旧 ready 冒充本轮成功后倒退”**；共享同一协调者 PID。
- `verified_at` 两端不要求相同（本轮观测为同一个收敛时刻）；`coordinated=true` 字段接口未返回。

**结果：通过。**（并发为真实实施，非推断。）

---

## 步骤 4：实时连接与历史未知对象只读核对（通过）

`creo_session_status`：

| 时间 | connected | toolkit_code | connection_state | release_numeric | worker_exit_code | current_model_code |
| --- | --- | --- | --- | --- | --- | --- |
| `01:11:03Z`（打开 Creo 后） | `true` | `0` | `connected` | `44` | `0` | `-8`（无当前模型） |
| `01:13:13.863711Z`（建模后） | `true` | `0` | `connected` | `44` | `0` | `0`（`▩BUG008_RETRY_179210001`） |

- `startup.stale=false`、`verification_age_seconds=0`（01:13:13Z）→ 实时验证，非陈旧快照。
- 实时连接确认为 **`connected=true` + `toolkit_code=0`**，不依赖 startup 的 stale/age 快照。

历史 unknown 只读核对（未修改、未清锁、未重提）：

- `creo_get_job(job_id=272513b7238040c68dce4b923725d870, detail=compact)`：
  - `status=unknown_outcome`、`readonly=true`、`kind=generic`、`model_id=27143ef77ce641938543e0ca44cc3c03`、`created_at=2026-10-15T08:58:36.576982+00:00`、`operation_count=1`
  - `recovery.automatic_replay_allowed=false`、`native_result_present=false`、`runner.observed=null`（`No recorded process creation identity`）
  - `recovery.model`：`status=ready`、**`revision=9`**、`pending_job=272513b7…`、`last_job=0eef840c…`
  - `recovery.saved_baseline`：`bug009_1792054655.prt.10`，`exists=true`，`sha256=324dd24ebd4d7b682fa9bbb41fbe02bc06b8158b5f43e75dec4b10f0f2323c6e`
- `creo_inspect_model(27143ef7…, detail=compact)`：`status=ready`、**`revision=9`**、`pending_job=272513b7…`、`inspection{has_solid=true, volume_mm3=600.0, features=8, surfaces=6, edges=12, bodies=1}`、`snapshot{source=saved_verified, live_state_verified=false, mutation_pending=true}`

**结果：通过。** 未知状态保留，未被本次重启或 retry 改变。

---

## 步骤 5：新建独立测试件 + 独立建模（通过）

两笔成功写任务，`revision 1→2`，**两笔均 `saved_file_reloaded_and_verified=true`**。

### 写任务 #1 — 新建独立测试件（`creo_new_part`）
- 输入：`model_name=bug008_retry_1792113143`
- 作业 `81929df938eb45168e1d137e0b834bda` / 模型 `5f68fea957134ddc8ecc26016dcf58a4`
- 起止：`created_at=2026-10-16T01:12:26.570064Z`、`started_at=01:12:27.027325Z`、`finished_at=01:12:39.855646Z`
- 终态：**`succeeded` / `stage=verified`**、**`revision=1`**
- 交付：`toolkit_code=0`、`saved_file_reloaded_and_verified=true`、`connected=true`
- 文件：`...\bug008_retry_1792113143.prt.2`，`sha256=3f85f0c49bb6d209a78c1070f53cf94674a67de2155771b4ad427c78dfcda633`
- inspection：`has_solid=false`（空件，符合预期）、`units=mm`、`counts{features=4, bodies=1}`

### 写任务 #2 — 一项计划（`creo_execute_plan`）
- 输入：
  - `model_id=5f68fea957134ddc8ecc26016dcf58a4`，`expected_revision=1`
  - `operations`：
    1. `{op:sketch, label:"retry_profile", plane:"XY", entities:[{type:"rectangle", name:"profile_rect", min:[-2,-3], max:[2,3]}]}`
    2. `{op:extrude, label:"retry_solid", sketch:"retry_profile", depth:5}`
    3. `{op:set_parameters, values:{"RETRY_VERIFIED":1}}`
  - `assertions`：`{require_solid:true, volume_mm3:120}`
- 作业 `9ff454ed424d4920b4f4c7a41ce68bbd` / 模型 `5f68fea957134ddc8ecc26016dcf58a4`
- 起止：`created_at=01:12:46.623617Z`、`started_at=01:12:46.994246Z`、`finished_at=2026-10-16T01:12:54.054438Z`
- 终态：**`succeeded` / `stage=verified`**、**`revision=2`**；`operations` 三项均 `succeeded:true`（`retry_profile` / `retry_solid` / `set_parameters`）
- 断言与几何：
  - `has_solid=true`、**`volume_mm3=120.0`**（`volume_query_code=0`）→ `require_solid=true`、`volume_mm3=120` 均满足
  - body `id=52` bbox：`[-2,-3,0] ~ [2,3,5]`；units=mm
  - `counts{features=8, surfaces=6, edges=12, bodies=1}`
  - 特征：`RETRY_PROFILE`（sketch，`feature_id=40`，草图尺寸 `d2=4.0`、`d3=6.0`）、`RETRY_SOLID`（protrusion，`feature_id=49`，深度尺寸 `d9=5.0`）
- 参数（保存后重载读回，`section=parameters`）：**`RETRY_VERIFIED` = `1`（type 52）** 已存在
- 交付：**`delivery_complete=true`**、**`disconnect_code=0`**、`disconnect_budget_seconds=20.0`、`connected=true`、`toolkit_code=0`、`completion_stage=result_delivery`、`native_pid=12176`
- 保存重载：**`saved_file_reloaded_and_verified=true`**；文件 `...\bug008_retry_1792113143.prt.3`，`sha256=cd0d0e9845ebc1f93f269f7c0215ba7cd056a7826363b141b4798769e5e2117d`
- 回滚：`rollback_succeeded=false`（成功任务，符合预期）

**结果：通过。** 所有已接受任务仅轮询 `creo_get_job` 取得终态，未重复提交。

---

## 步骤 6：结构化失败 / 人工处理（需要人工处理；自动启动未通过）

本次环境在 00:22Z–00:55Z 与重启后均处于“Creo 未运行 + 共享启动历史不可读”状态，属提示词所述场景。

- 前置核对（公开接口）：`creo_session_status` → `connected=false`、`connection_state=not_found_or_unreadable`、**`toolkit_code=-4`**、`current_model_code=-8`、`release_numeric=0`、`worker_exit_code=20`。
- 单次与真实重叠 `retry=true` 终态（两段环境各一组）：

| 时间 | 形式 | 终态 | 关键字段 |
| --- | --- | --- | --- |
| 00:22:02Z | 单次 | `selection_required` | `pid=6900`，`updated_at=00:22:06.144364Z` |
| 00:22:17Z | 两个同批（真实重叠） | `selection_required` | 均 `updated_at=00:22:20.815647Z` |
| 00:55:5xZ | 单次 | `selection_required` | `pid=5188`，`updated_at=00:56:12.746521Z` |
| 00:56:00Z | — | `timeout`（startup 快照） | `message=Toolkit connection is no longer available…` |

- 终态结构化字段（与提示词预期一致，**未泄漏成无明细错误**）：
  - `coordination_error.code = startup_state_unreadable`
  - `coordination_error.launch_state_known = false`；顶层 `launch_state_known = false`
  - `coordination_error.automatic_launch_allowed = false`；顶层 `automatic_launch_allowed = false`
  - `launch_reserved = true`
  - `coordination_error.reason = "JSONDecodeError: Expecting value: line 1 column 1 (char 0)"`
  - `recovery_required` / `message` 给出明确人工步骤：保留 `state.json` 与既有 job/model 预留，检查挂起的启动对话框与配置会话；retry 只能**校验已有会话**，无法自动拉起替代进程；必要时**人工打开 Creo**。
  - `retry_allowed=true`（重试语义保留）；`snapshot=true`、`stale=true`、`verification_age_seconds=null`。

**结论：安全停止，需要人工处理。** 不计入“自动启动通过”。
- 自动启动：本环境 `automatic_launch_allowed=false`，且实际恢复**依赖人工打开 Creo**（见步骤 7）→ 自动启动**未通过/未验证**（无法确认可自动启动的前提）。

---

## 步骤 7：人工打开 Creo 后的重连与建模（通过）；历史故障链（未验证）

- 用户**人工打开 Creo** 后：
  - `creo_session_status`（01:11:03Z）：`connected=true`、`toolkit_code=0`、`release_numeric=44`、`worker_exit_code=0`、`stale=false` → **重连通过**。
  - 重复步骤 2–5：单次 retry → `ready`（`verified_at=01:11:21.988Z`）；重叠 retry → `ready`（`verified_at=01:11:38.017Z`）；独立建模 → `revision 1→2`、`volume_mm3=120.0`、`saved_file_reloaded_and_verified=true` → **建模通过**。
  - 本项记为 **“人工打开后重连/建模通过”**，**不计入自动恢复**（`startup.message` 明确 `automatic replacement is disabled`）。
- 建模后只读复核历史 unknown 保护：`creo_get_job(272513b7…)` 仍 `unknown_outcome`/`readonly=true`、`revision=9`、`pending_job` 未变、基线 `sha256=324dd24e…` 存在；`creo_inspect_model(27143ef7…)` 仍 `revision=9`、`volume_mm3=600.0` → **保护仍在，未被本轮操作或重启破坏**。
- 历史完整链 `transform → 保存后挂死 → -38`：本次**未提供对应环境** → **未验证**（未自行制造挂死/强杀/关闭用户 Creo）。

---

## 分项汇总

| 分项 | 内容 | 结论 |
| --- | --- | --- |
| 步骤 1 | 运行身份 / 漂移 / 三枚指纹匹配 | **通过** |
| 步骤 2 | 单次 `retry=true`（已有会话，人工打开后）→ `ready`/`connected=true` + 本次 `verified_at` | **通过** |
| 步骤 3 | 真实重叠 `retry=true` → 两端 `ready`，共享协调者，无倒退 | **通过**（并发真实实施） |
| 步骤 4 | 实时连接 `connected=true`/`toolkit_code=0` + 历史 unknown 只读核对 | **通过** |
| 步骤 5 | 独立建模 `retry_profile`/`retry_solid`，`volume=120`，`RETRY_VERIFIED=1`，`revision 1→2`，两笔均保存重载 true | **通过** |
| 步骤 6 | 不可用会话下的 retry → 结构化 `selection_required` + 人工步骤，无明细泄漏 | **需要人工处理**（安全停止）；自动启动**未通过/未验证** |
| 步骤 7 | 人工打开后重连/建模 | **通过**（不计入自动恢复）；历史故障链**未验证** |

- **通过**：步骤 1、2、3、4、5，以及步骤 7 的“人工打开后重连/建模”。
- **需要人工处理**：步骤 6 的自动启动路径（`automatic_launch_allowed=false`，实际需人工打开 Creo）。
- **未验证**：历史 `transform → 保存后挂死 → -38` 整条链；只能靠源码/本地脚本验证的内部机制（重试预算、看门狗、进程存活、临时文件清理）不纳入结论。

## unknown 处置（本轮）

- job `272513b7238040c68dce4b923725d870` / model `27143ef77ce641938543e0ca44cc3c03` 仍为 **unknown_outcome**：**保留 reservation 与写保护，未重提、未清锁、未宣告成功**。
- 待核对对象不变：该 job 的 native result/checkpoint、runner 创建身份、`bug009_1792054655.prt.10` 基线（`sha256=324dd24e…`）。
- `connected=true` 不等于该作业已解决；若仍无法核对结果，需运维人工对账。

## 未验证声明（避免外推）

- 本轮 retry **真实重叠已实施**，故可报告“并发已实施且两端收敛 `ready`”；但接口未返回 `coordinated=true`，不据此宣称协调细节通过。
- 首轮“重启前 Creo 未运行”与 00:23Z–00:55Z 的机器重启属**环境事件**；通道恢复依赖**人工打开 Creo**，不据此宣称自动恢复通过。
- 上一轮报告中“未变路径”的历史结果（如 600 mm³ 基线、工程图等）本轮**未重新测试**，不作为本轮证据。
- 无法由 MCP 观察的项目（内部重试/预算/看门狗/进程管理）明确记为**未验证**，不推测通过。
