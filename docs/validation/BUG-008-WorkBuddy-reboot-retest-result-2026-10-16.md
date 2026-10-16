# BUG-008：重启后自动恢复的 WorkBuddy 复验结果（2026-10-16）

- 执行方：WorkBuddy（仅通过已连接 MCP 工具黑盒验收；未查看/修改源码，未读取本机配置，未运行脚本，未检查系统进程，未清除 `pending_job`，未自行关闭 Creo，未制造挂死/强杀/重启）
- 测试提示词：`docs/validation/BUG-008-WorkBuddy-reboot-retest.md`
- 服务版本：`creo_capabilities.version` = `0.3.1`；`code_root` = `E:\Projects\MCP_CREO_MechDog`（E 盘本次开发实现）
- 会话：Creo 12.4.0.0（`release_numeric=44`）；协调者 `coordinator_pid=17164`
- 时区：UTC（`Z`）。执行窗口 `02:07:36Z – 02:09:38Z`
- 结论概览：**运行身份/新指纹、单次 retry、真实重叠 retry、实时连接、独立建模、未知保护均通过；损坏历史自动恢复未验证；异常环境（同次开机损坏/时钟不可核实/备份失败）未验证；历史 `transform→保存挂死→-38` 链未验证。**

> 与上一轮的差异：服务已加载**新实现**，公开接口新增 `startup.unreadable_history`、`startup.boot_verification_budget_seconds`、`launch_state_known`、`automatic_launch_allowed`、`launch_attempt`、`launched_by_coordinator`、`preparation_budget_seconds` 等字段，状态机出现 `building_worker`。

---

## 步骤 1：运行身份与新指纹（通过）

`creo_capabilities`（无输入，02:07:36Z）关键字段：

| 字段 | 值 |
| --- | --- |
| `version` | `0.3.1` |
| `runtime.code_root` | `E:\Projects\MCP_CREO_MechDog` |
| `runtime.server_entry` | `E:\Projects\MCP_CREO_MechDog\server.py` |
| `runtime.source_changed_since_startup` | **`false`** ✅ |
| `startup.unreadable_history` | `Archive/rebuild only verified previous-boot startup history, with no existing session and under startup/Toolkit locks; preserve unknown job/model reservations` |
| `startup.boot_verification_budget_seconds` | **`5`** ✅ |
| `startup.automatic_by_default` | `true` |
| `tool_count` / `enabled_tool_count` | `82` / `82`；`unavailable_tools=[]` |

指纹对照（`runtime.source_fingerprints_at_startup`）：

| 键 | 预期 SHA256 | 实测 | 结论 |
| --- | --- | --- | --- |
| `server.py` | `a2389f8c97d36d1d687e7d508cf3fc3c545cb6574e8b7651267f74d29f6f0e60` | 同 | ✅ 匹配 |
| `creo_startup.py` | `7d803ee8c679da483080c9e3cda31b6cf276178383542a9b5e3fac82885c2a22` | 同 | ✅ 匹配 |
| `bridge.py` | `84eb1e0ec34fd208b28f403816f7bb876f0b67ea982b750b5d5f1eefdc677a85` | 同 | ✅ 匹配 |
| `src/creo_mechdog/startup_state.py` | `5b482745c0dfd93fc2ec699a1071b6c6cac1bca17944e854941bef197cda9e4c` | 同 | ✅ 匹配 |
| `src/creo_mechdog/windows_boot.py` | `4b3d521e3387eed0668317501e1ee6db7a81d32358c9fbd898c24957455bc6da` | 同（字段存在） | ✅ 匹配 |

- commit / SDK / 宿主构建身份：接口未提供 → **无法确认**（以指纹匹配判定已更新，不凭版本号 0.3.1）。

### 启动状态轮询与 `startup_recovery`

首次读取（`creo_startup_status` 无输入）：

- `state=ready`、`connected=true`、`verified_at=2026-10-16T02:07:30.520981Z`、`verification_age_seconds=27.885364`、`stale=false`、`coordinator_pid=17164`
- `launch_reserved=false`、`launch_attempt=1`、`auto_start_enabled=true`、`selected_session_configured=false`
- `coordination_error=null`、`launch_state_known=true`、`automatic_launch_allowed=true`
- `launched_by_coordinator=false`、`native{connected=true, toolkit_code=0, current_model="▩BUG008_RETRY_179210001", release_numeric=44}`
- `message="Toolkit connection verified; modeling is available"`

**`startup_recovery` 字段未在任何一次 `creo_startup_status` / `creo_session_status` / `creo_capabilities` 返回中出现**；归档路径、原哈希/字节数均未公开。因此本轮**没有观察到 `status=reconciled_previous_boot` 的恢复记录**。

**结果：通过（身份与字段核对）。** 同时明确记录：本次读到的是**已处于可信状态**的启动快照（`coordination_error=null`、`launch_state_known=true`），且我已确认 Creo 当时已由先前会话保持打开（`launched_by_coordinator=false`）——即属于“**已有会话重连 / 读取恢复后的干净快照**”，**不是**我在损坏历史下完成的冷启动。

---

## 步骤 2：损坏历史下的自动恢复（未验证——环境不满足）

- 提示词要求的场景是“**重启后旧损坏启动历史 + Creo 未打开**”。执行时**该环境不存在**：
  - 首次读取即为 `state=ready`、`connected=true`，`native.toolkit_code=0`、`current_model="▩BUG008_RETRY_179210001"`（上一轮遗留模型）→ **Creo 处于打开且已连接状态**。
  - `launch_state_known=true`、`automatic_launch_allowed=true`、`coordination_error=null` → 启动历史在本次观测前**已处于可信状态**，无可复现的“损坏历史”条件。
- 因此未观察到：
  - 原记录被**归档**（无归档路径公开）
  - `startup_recovery.status=reconciled_previous_boot`
  - 原哈希 / 原字节数
  - 由本环境触发的“无人工打开 Creo 的自动恢复终态”
- 按提示词要求**按实际场景命名**：本项记为 **“已有会话重连 + 读取先前恢复留下的干净快照”**，**不外推为“损坏历史下自动恢复通过”**。

**结果：未验证（环境不满足）。**

---

## 步骤 3：单次与真实重叠 retry（通过）

### 3.1 单次 `creo_startup_status(retry=true)`
- 起始 `02:08:12.224Z`
- `checking`（`connected=false`、`retry_allowed=false`）
- `building_worker`（`02:08:16.215443Z`，`preparation_budget_seconds=180`、`remaining_budget_seconds=296.282`、`phase_remaining_budget_seconds=116.672`、`coordinator_running=true`）
- 终态 `ready`（**`verified_at=2026-10-16T02:08:21.394020Z`**、`verification_age_seconds=2.273012`、`stale=false`、`coordinator_pid=17164`、`native.toolkit_code=0`、`launched_by_coordinator=false`）
- 全程无原始错误。

### 3.2 真实重叠 `retry=true`（同批两个）
- 起始 `02:08:28.136Z`
- 返回 1：`state=checking`、`retry_allowed=false`
- 返回 2：`state=checking`、**`coordinator_running=true`**、`snapshot=true` → 第二个调用观测到第一个正在推进，**确认真实重叠**
- 中间态 `02:08:31.624243Z`：`building_worker`（`remaining_budget_seconds=296.516`、`phase_remaining_budget_seconds=116.953`）
- 终态 `02:08:36.917749Z`：`state=ready`、`connected=true`、**`verified_at=2026-10-16T02:08:36.917749Z`**、`verification_age_seconds=2.118544`、`stale=false`、`coordinator_pid=17164`、`native.toolkit_code=0`

- 两端最终 `ready`；**验证时间已更新**（02:08:36.918Z ≠ 上一轮 02:08:21.394Z）；**无旧 ready 冒充本轮成功后倒退**。
- 未根据协调者 PID 推测 Creo 进程数量。

**结果：通过。**

---

## 步骤 4：实时连接与历史未知只读核对（通过）

`creo_session_status`（无输入，`02:08:48.620950Z`）：

- `connected=true`、**`toolkit_code=0`**、`connection_state=connected`、`release_numeric=44`、`worker_exit_code=0`、`disconnect_code=0`
- `current_model="▩BUG008_RETRY_179210001"`、`current_model_code=0`
- `startup.state=ready`、`stale=false`、`verification_age_seconds=0`、`coordination_error=null`、`launch_state_known=true`、`automatic_launch_allowed=true`

历史未知对象（只读，未修改、未清锁、未重提）：

`creo_get_job(job_id=272513b7238040c68dce4b923725d870, detail=compact)`
- `status=unknown_outcome`、`readonly=true`、`kind=generic`、`model_id=27143ef77ce641938543e0ca44cc3c03`、`created_at=2026-10-15T08:58:36.576982+00:00`、`operation_count=1`
- `recovery.automatic_replay_allowed=false`、`native_result_present=false`、`runner.observed=null`（`No recorded process creation identity`）
- `recovery.model`：`status=ready`、**`revision=9`**、`pending_job=272513b7…`、`last_job=0eef840c…`
- `recovery.saved_baseline`：`...\bug009_1792054655.prt.10`、`exists=true`、`sha256=324dd24ebd4d7b682fa9bbb41fbe02bc06b8158b5f43e75dec4b10f0f2323c6e`
- `recovery_required="Outcome is unconfirmed; preserve reservation and inspect recovery evidence"`

`creo_inspect_model(27143ef7…, detail=compact)`
- `status=ready`、**`revision=9`**、`pending_job=272513b7…`、`part_file=...\bug009_1792054655.prt.10`
- `inspection{has_solid=true, volume_mm3=600.0, volume_query_code=0, features=8, surfaces=6, edges=12, bodies=1}`
- `snapshot{source=saved_verified, live_state_verified=false, mutation_pending=true}`

**结果：通过。**

---

## 步骤 5：新建独立零件 + 独立建模（通过）

两笔写任务，`revision 1→2`，均 `saved_file_reloaded_and_verified=true`。

### 写任务 #1 — 新建独立零件（`creo_new_part`）
- 输入：`model_name=bug008_reboot_1792116533`
- 作业 `8a2e633fe8b34bb3b254725ef79622f7` / 模型 `398b553136a641c1951daf5733bd64bf`
- 起止：`created_at=2026-10-16T02:08:58.016413Z`、`started_at=02:08:58.411635Z`、`finished_at=02:09:04.864300Z`
- 终态：**`succeeded` / `stage=verified`**、**`revision=1`**
- 交付：`toolkit_code=0`、`saved_file_reloaded_and_verified=true`、`connected=true`、`rollback_succeeded=false`
- 文件：`...\bug008_reboot_1792116533.prt.2`，`sha256=1854caa44e1b2f16beb9bc08b7fd0647074cc40813a14b2c87ebcf62ff33cf05`
- inspection：`has_solid=false`（空件，符合预期）、`units=mm`、`counts{features=4, bodies=1}`

### 写任务 #2 — 一项计划（`creo_execute_plan`）
- 完整输入：
  - `model_id=398b553136a641c1951daf5733bd64bf`，`expected_revision=1`
  - `operations`：
    1. `{op:"sketch", label:"reboot_profile", plane:"XY", entities:[{type:"rectangle", name:"reboot_rect", min:[-2,-3], max:[2,3]}]}`
    2. `{op:"extrude", label:"reboot_solid", sketch:"reboot_profile", depth:5}`
    3. `{op:"set_parameters", values:{"REBOOT_VERIFIED":1}}`
  - `assertions`：`{require_solid:true, volume_mm3:120}`
- 作业 `4614241688fd4659bc0c93ee56627be9` / 模型 `398b553136a641c1951daf5733bd64bf`
- 起止：`created_at=02:09:09.901234Z`、`started_at=02:09:10.268200Z`（`stage=connect` → `display_preview`）、`finished_at=2026-10-16T02:09:18.203675Z`
- 终态：**`succeeded` / `stage=verified`**、**`revision=2`**；`operations` 三项均 `succeeded:true`（`reboot_profile` / `reboot_solid` / `set_parameters`）
- 断言与几何：
  - **`has_solid=true`**、**`volume_mm3=120.0`**（`volume_query_code=0`）→ `require_solid=true`、`volume_mm3=120` 均满足
  - body `id=52` bbox：**`[-2,-3,0] ~ [2,3,5]`**；units=mm；`counts{features=8, surfaces=6, edges=12, bodies=1}`
  - 特征：`REBOOT_PROFILE`（sketch，`feature_id=40`，尺寸 `d2=4.0`、`d3=6.0`，重合约束 12 个）、`REBOOT_SOLID`（protrusion，`feature_id=49`，深度尺寸 `d9=5.0`）
  - 别名：`reboot_profile` → `{op:sketch, feature_id:40, entity_ids{reboot_rect_0..3}}`；`reboot_solid` → `{op:extrude, feature_id:49}`
- 参数（保存后重载读回，`section=parameters`）：**`REBOOT_VERIFIED` = `1`（type 52）** 已存在
- 交付：**`delivery_complete=true`**、**`disconnect_code=0`**、`disconnect_budget_seconds=20.0`、`connected=true`、`toolkit_code=0`、`completion_stage=result_delivery`、`native_pid=2416`、`preview_code=0`
- 保存重载：**`saved_file_reloaded_and_verified=true`**；文件 `...\bug008_reboot_1792116533.prt.3`，`sha256=dead826b12d7e7bf301a5971aaf4f9d509bcc693501f373f488cf9fc80a4f16a`
- 回滚：`rollback_succeeded=false`（成功任务，符合预期）
- 已接受任务仅通过 `creo_get_job` 轮询取得终态，**未重复提交**。

**结果：通过。**

---

## 步骤 6：异常环境（同次开机损坏 / 时钟不可核实 / 已有或不确定会话 / 备份失败）（未验证）

- 发起者**未提供**上述任一环境；执行时唯一会话是“重启前遗留且保持打开”的会话（`selected_session_configured=false`、`current_model="▩BUG008_RETRY_179210001"`），不构成“同次开机损坏 / 时钟不可核实 / 备份失败”的条件。
- 未执行本地注入，未制造挂死/强杀/重启。
- 可观测到的保护行为（**不构成该项通过**）：
  - `coordination_error=null`，未出现盲目替换启动历史；
  - unknown 建模任务保护保持（见步骤 4 与文末复核）；
  - `creo_startup_status` 在不改动历史的前提下返回可解释快照。
- 内部文件刷盘、锁、进程身份、预算机制属开发证据范围，**不纳入 WorkBuddy 结论**。

**结果：未验证（未提供环境）。**

---

## 场景归类（按提示词要求分别记录）

| 场景 | 本轮实际观测 | 结论 |
| --- | --- | --- |
| 损坏历史下的自动恢复 | 未复现该环境；无 `startup_recovery`、无归档记录 | **未验证** |
| 有效历史普通冷启动 | 未提供；服务启动后首次读取即 `ready` | **未验证** |
| 已有会话重连 | `launched_by_coordinator=false`、复用既有会话（`▩BUG008_RETRY_179210001`），单次/重叠 retry 均 `ready` | **通过**（本轮实际场景） |
| 读取过去的恢复快照 | 首次读取即 `coordination_error=null`、`launch_state_known=true`、`launch_attempt=1`，属**读取恢复后的干净快照** | 已识别，**不计为自测通过** |
| 人工打开后恢复 | 本轮**无人工打开动作**（Creo 自上一轮保持打开） | **未发生** |
| 历史 `transform→保存挂死→-38` 完整链 | 未提供环境 | **未验证** |

---

## 分项汇总

| 分项 | 内容 | 结论 |
| --- | --- | --- |
| 步骤 1 | 运行身份、5 枚新指纹、`unreadable_history`、`boot_verification_budget_seconds=5` | **通过** |
| 步骤 2 | 损坏历史下自动恢复（归档 + `reconciled_previous_boot` + 无人工开 Creo） | **未验证**（环境不满足） |
| 步骤 3 | 单次 retry 与真实重叠 retry → `ready`、验证时间更新、无倒退 | **通过** |
| 步骤 4 | 实时 `connected=true`/`toolkit_code=0`；历史 unknown 保护保留 | **通过** |
| 步骤 5 | 独立零件 `revision=1` → 计划 `revision=2`、120 mm³、`REBOOT_VERIFIED=1`、保存重载 true | **通过** |
| 步骤 6 | 异常环境结构化行为 | **未验证**（未提供环境） |

## unknown 处置（本轮）

- job `272513b7238040c68dce4b923725d870` / model `27143ef77ce641938543e0ca44cc3c03` 仍为 **unknown_outcome**：**保留 reservation 与写保护，未重提、未清锁、未宣告成功**。
- 文末复核（`02:09:38Z`，建模之后）：job 仍 `unknown_outcome`/`readonly=true`；model 仍 `revision=9`、`pending_job=272513b7…`、基线 `bug009_1792054655.prt.10`（`sha256=324dd24e…`）存在、`volume_mm3=600.0` → **保护未被本轮操作破坏**。
- `connected=true` 不等于该作业已解决；若仍无法核对结果，需运维人工对账。

## 未验证声明（避免外推）

- 本轮**未提供**“重启后损坏启动历史 + Creo 未打开”环境，故**不宣称**损坏历史自动恢复通过；也未观察到 `startup_recovery`/归档证据。
- 首次读取到的 `ready` 快照属**先前已恢复/既有会话**留下的状态，**不能**记为本轮完成冷启动。
- 真实重叠 retry 已实际实施，故并发部分可报告“已实施且两端收敛 `ready`”。
- 未提供的 `transform→保存挂死→-38` 完整链继续**未验证**。
- 只能靠源码或本地脚本验证的内部机制（刷盘、锁、进程身份、预算）不纳入结论。
