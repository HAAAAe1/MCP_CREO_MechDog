# BUG-008 WorkBuddy 黑盒验收记录（2026-10-15，含重启后复测）

- 执行方：WorkBuddy（仅通过已连接 MCP 工具黑盒验收，不查看/分析/修改源码，不读取本机配置，不运行脚本，不结束进程，不清除 reservation/pending_job）
- 测试提示词：`docs/validation/BUG-008-WorkBuddy-test.md`
- 服务版本：`creo_capabilities.version` = `0.3.1`；`code_root` = `E:\Projects\MCP_CREO_MechDog`（E 盘本次开发实现）
- 会话：Creo 12.4.0.0（`release_numeric=44`），coordinator_pid `3832`
- 时区：UTC（`Z`）
- 说明：13:00Z 首轮进行中，测试机被**人工重启**导致 Creo 通道掉线、`retry=true` 无法恢复；重启后 **人工打开 Creo**，通道恢复，遂在 14:14Z 之后**完整重跑**。本文件为主体（重跑）结果；首轮掉线仅作为环境事件记录。
- 结论概览：**场景 1/2/3/4/5/7 通过；场景 6 retry 恒报错、并发未验证；场景 8 无故障环境 → 未验证。**

> 重要提示：场景 5 需按“**提交一项** = 单个计划内先 `set_parameters` 再拉伸”理解，回滚后该参数才会不存在。按字面拆成两步的旁证另附（见场景 5B），两步会导致参数被单独提交而保留。

---

## 场景 1：能力与运行身份确认（通过）

`creo_capabilities`（无输入，返回体 99,949 字符，落盘解析）关键字段：

- `version`: `0.3.1`；`runtime.code_root`: `E:\Projects\MCP_CREO_MechDog`；`runtime.server_entry`: `E:\Projects\MCP_CREO_MechDog\server.py`
- `runtime.source_changed_since_startup`: `false`（**无源码漂移**）
- `recovery` / `result_delivery` 运行指纹：
  - `src/creo_mechdog/recovery.py` = `f64bc43164e7e75a51b7be1f29e152a5ad588a71c4f055f7cf549f92a4180e4f`
  - `native/result_delivery.h` = `fb6da37ac0a591f94ec8bbe4fcdc02b37f1ef527de26b7c8a2410a3907130220`
- `scheduling.unknown_outcome`: `"Reservation retained; inspect job.recovery. Explicit startup retry only rechecks the channel and never commits/replays an unknown job."`
- `scheduling.disconnect_watchdog_seconds`: `20`；`native_channels`: `1`；`admission`: `reject_busy_without_creating_a_job`
- `tool_count`/`enabled_tool_count`: `82`/`82`；`unavailable_tools`: `[]`
- commit/构建身份、SDK/宿主细节：接口未提供 → **无法确认**

`creo_startup_status`（无输入，14:14:37Z）：`state=ready`、`connected=true`、`verified_at=2026-10-15T14:14:37.274255+00:00`、`snapshot=true`。

**结果：通过。**

---

## 场景 2：等待 ready 后的真实会话确认（通过）

`creo_session_status`（无输入，14:14:37Z 与 14:20:10Z 两次）：
- `connected=true`、`connection_state=connected`、**`toolkit_code=0`**
- `release_numeric=44`、`current_model_code=0`、`disconnect_code=0`、`worker_exit_code=0`
- startup：`state=ready`、`verified_at=2026-10-15T14:20:10.350514+00:00`、`verification_age_seconds=0`、**`stale=false`**

**结果：通过。** 真实连接 `toolkit_code=0` 且为实时验证（非快照）。

---

## 场景 3：历史 unknown job 只读核对（通过，未修改）

`creo_get_job(job_id=272513b7238040c68dce4b923725d870)`：
- `status=unknown_outcome`、`readonly=true`、`kind=generic`、`model_id=27143ef77ce641938543e0ca44cc3c03`
- `operations=[{op:export, format:step}]`；`created_at=2026-10-15T08:58:36.576982+00:00`
- `message="Job exceeded its expected lifetime; inspect runner.log and Creo before retrying"`
- `recovery`：`automatic_replay_allowed=false`、`native_result_present=false`、`runner.observed=null`（`No recorded process creation identity`）、`model={status:ready, revision:9, pending_job:272513b7…, last_job:0eef840c…}`、`saved_baseline={path:...\bug009_1792054655.prt.10, exists:true, sha256:324dd24ebd4d7b682fa9bbb41fbe02bc06b8158b5f43e75dec4b10f0f2323c6e}`
- `recovery_required="Outcome is unconfirmed; preserve reservation and inspect recovery evidence"`

`creo_inspect_model(27143ef7…)`：`status=ready`、`revision=9`、`pending_job=272513b7…`、`inspection{has_solid=true, volume_mm3=600.0, features=8, surfaces=6, edges=12, bodies=1}`、`snapshot{source=saved_verified, live_state_verified=false, mutation_pending=true}`。

**结果：通过。** 与掉线前一致（未被重启改变）；未推断成功、未清锁/重提/修改。

---

## 场景 4：新建专用零件并提交建模计划（通过）

计划：`model_name=bug008_retest_1792073708`，`sketch profile(XY, rect[-5,-5]~[5,5])` → `extrude solid(depth 6)`，`assertions{require_solid:true, volume_mm3:600}`。

- 作业 `78dbbc639ff04f7e89ccfde840bd3a8f` / 模型 `48adbd3415ae469bab470eb151fa8f74`
- 终态 **`succeeded`/`stage=verified`**，`revision=1`
- 几何：`volume_mm3=600.0`、`has_solid=true`、body bbox `[-5,-5,0]~[5,5,6]`、units=mm
- 交付：`delivery_complete=true`、`disconnect_code=0`、`disconnect_budget_seconds=20`、`connected=true`、`toolkit_code=0`
- **`saved_file_reloaded_and_verified=true`**；`part_file=...\bug008_retest_1792073708.prt.2`；`sha256=7fd66dce0f957f48c7fbeaccb3d732b376e63d81b2d0a4f25106fc02e214b5f1`

随后 `creo_set_parameters(model, expected_revision=1, {BUG008_MARKER:8})`：
- 作业 `bb321b2ae21b40c39e1a8c625e675cb9` → `succeeded`、`revision=2`
- 参数 `BUG008_MARKER=8`（type 52）已写入；`volume_mm3=600.0`；**`saved_file_reloaded_and_verified=true`**；`sha256=1bad922ed3c7905b9f248d8083076748c3a29f03c77e7519f8024d50594ac205`

**结果：通过。**

---

## 场景 5：预期原生失败与回滚（通过——单计划流程）

### 5A（主测：单个计划）— 新建独立件后提交“先写参数再失败拉伸”的一项计划
- 基件：`model_name=bug008_s5_1792073875` / 模型 `fbf8a57a3e394bbe97b075de595c5ad2`
  - 计划 `[sketch profile(XY rect[-5,-5]~[5,5]), extrude solid(depth 6), set_parameters{BUG008_MARKER:8}]`，`assertions{volume_mm3:600, require_solid:true}`
  - 作业 `ce4f5192f04845d18db361e45db0eb63` → `succeeded`、`revision=1`、`volume_mm3=600.0`、`saved_file_reloaded_and_verified=true`、`sha256=55801c2fd6e0d24b6120a262769bb742c61dca6e130bd5500d4da691936fda4f`
- 失败计划（`expected_revision=1`）：`[set_parameters{BUG008_SHOULD_ROLLBACK:1}, extrude{label:invalid_extrude, sketch:missing_profile, depth:1}]`
  - 作业 `98cf170710c84e3aa0911f2916a55ea3` → **`failed`/`stage=executing_feature_plan`**
  - **完整原始错误**：`"Unknown feature label: missing_profile"`；`toolkit_code=-1`
  - 失败阶段/调用：`failed_stage=execute_extrude`、`failed_operation_index=1`、`failed_toolkit_call=null`
  - **回滚**：`rollback_succeeded=true`、`inspection_source=rollback_verified`；`saved_file_reloaded_and_verified=false`（失败作业，符合预期）
  - `native_log_tail` 关键片段：`BUILD_FAILED=Unknown feature label: missing_profile` → `PHASE=rollback_to_saved_checkpoint` → `ProSolidRegenerate=0` → `PHASE=disconnect` → `DISCONNECT=0` → `PHASE=result_delivery_complete`
- 失败后核对（`creo_inspect_model` compact + `section=parameters`）：
  - 体积仍 **600.0**、`has_solid=true`
  - **`BUG008_MARKER=8` 仍存在**（原标记保留）
  - **`BUG008_SHOULD_ROLLBACK` 不存在**（计划内参数被回滚）✓
  - `revision` 仍为 **1**（失败未推进）
- 只读刷新 `creo_refresh_model` → 作业 `5fae8d592bd24547954047ba48e6ad19`（`readonly=true`）→ `succeeded`、`revision=1`（**只读刷新未增加 revision**）、`volume_mm3=600.0`、`inspection_source=live_query`

**结果：通过。**

### 5B（旁证：按字面拆成两步）
- 先 `set_parameters{BUG008_SHOULD_ROLLBACK:1}`（作业 `fe830f8a39bc476994ae27d7650d115b`，`succeeded`，`revision=3`），再单独提交 `extrude{invalid_extrude, missing_profile, depth:1}`（作业 `b45fa39b4fa649fdaf0752593692a6c2`）
  - 该失败作业：`failed`、`message="Unknown feature label: missing_profile"`、`failed_stage=execute_extrude`、`failed_operation_index=0`、`rollback_succeeded=true`、`inspection_source=rollback_verified`、`volume_mm3=600.0`、`toolkit_code=-1`
  - 结果：`MARKER=8` 保留、`SHOULD_ROLLBACK=1` **保留**（因其在失败前已作为独立作业提交并保存）
- 说明：因该参数已被单独提交为检查点，两步流程下“回滚参数不存在”不成立；此旁证说明该场景必须按“单个计划”执行（即 5A）。

---

## 场景 6：重叠 startup retry 与并发协调（未通过——retry 不可用；并发未验证）

在通道 `ready` 状态下发起 retry：

| 时间(UTC) | 形式 | 返回 |
|---|---|---|
| 14:19:20Z | 两个 `creo_startup_status(retry=true)` 同批 | 两者均 `Error executing tool creo_startup_status` |
| 14:19:28→14:19:37Z | 单个 `retry=true`（约 8–9s 返回） | `Error executing tool creo_startup_status` |
| 后续 | 另有 3 次单个 `retry=true` | 均 `Error executing tool creo_startup_status` |

同时刻非 retry 查询：`creo_startup_status` → `state=ready`、`connected=true`、`retry_allowed=false`、`stale=true`（`verification_age_seconds≈308`）；`creo_session_status` → `connected=true`、`toolkit_code=0`、`stale=false`。

- `retry=true` 在 **通道 ready 时也恒报错**（返回无 JSON 明细的 MCP 层错误），未返回可用快照；`verified_at` 未刷新。
- 两个同批 retry 调用**均在调用层直接失败**，未进入协调逻辑 → 无法观测 `busy/coordinated/waiting_for_channel` → **并发未验证（不得称并发通过）**。
- 未观测到 `building/ready` 状态推进；未发生旧 ready 冒充本次 retry 成功再退回 building 的现象（因为 retry 根本未返回）。

**结果：未通过；并发未验证。**

### 6.2 补测：用户手动关闭 Creo 后的 retry 实测（14:47–14:50Z，真实通道不可用）
- 前置：用户**手动关闭 Creo**（`tasklist` 仅剩 `nmsd.exe` 许可守护，无 `xtop/parametric`）。
- 过期快照：`creo_startup_status`（无 retry）仍返回 `state=ready`、`connected=true`，但 `verification_age_seconds≈1627`、`stale=true` → **陈旧快照，不作为实时连接证据**（与提示词“旧 ready 不应先冒充本次 retry 成功”一致）。
- 实时状态：`creo_session_status` → `connected=false`、`toolkit_code=-4`、`connection_state=not_found_or_unreadable`、`worker_exit_code=20`。
- 连续 `creo_startup_status(retry=true)`：
  - 14:47:28Z 单次 → `Error executing tool creo_startup_status`
  - 14:47:xxZ 单次 → 同上
  - 14:49:xxZ 两个同批并发 → 均同上
  - 另多次单次 → 均同上
  - 全部**秒级返回、无 JSON 明细**；`coordinator_running=false`、`coordinator_pid` 恒为 `3832`、`updated_at` 未推进
- 结果：约 3 分钟内 retry **始终未启动启动协调者，也未能拉起 Creo**（`tasklist` 恒无 `xtop/parametric`），通道保持 `timeout`。
- 结论：**在本环境实测，MCP 无法通过 `retry=true` 自动拉起已关闭的 Creo**；需人工打开 Creo。并发协调仍**未验证**。

---

## 场景 7：恢复后独立建模与基线核对（通过）

会话再次确认：`creo_session_status` → `connected=true`、`toolkit_code=0`、`release_numeric=44`、`stale=false`。

- 独立小件 `model_name=bug008_after_1792074015` / 模型 `7e7eb8c30c29418aadc75e4ca69d0d3d`
  - 计划 `[sketch after_profile(XY, rect[-2,-3]~[2,3]), extrude after_solid(depth 5), set_parameters{RECOVERED:1}]`，`assertions{require_solid:true, volume_mm3:120}`
  - 作业 `a54bba7f098f4e4492dacb9fd84c2cd4` → `succeeded`、`revision=1`、**`volume_mm3=120.0`**、`has_solid=true`、`RECOVERED=1` 写入成功、**`saved_file_reloaded_and_verified=true`**、`toolkit_code=0`、`sha256=b5c254ff8cc8a7d39ced909cc1bdddd799c81e4a86b2f16e3f652cecc1b49943`
- 快捷 plate 20×10×3（无圆角、无孔）`model_name=bug008_plate_1792074015`
  - 作业 `5d06347e498a4b1ab829107d895b2943` → `succeeded`、**`volume_mm3=600`（`expected_volume_mm3=600`）**、`extrude_count=1`、`round_count=0`、`hole_count=0`、**`saved_file_reloaded_and_verified=true`**、`toolkit_code=0`、`sha256=5f44bce467cf6bdc47c0cf77fc4ab97e433a5421086ba0fbb388ead31f212bbf`
- 场景 4 原件基线核对 `creo_inspect_model(48adbd…)`：`status=ready`、`revision=3`、`volume_mm3=600.0`、`BUG008_MARKER=8` 仍可读 → **原保存基线仍可用**
- 可选工程图：`creo_new_drawing(source_model_id=48adbd…)` → 模型 `4fe4f3739e944c25bf333b53390b7767`
  - 作业 `153263a20076401880ff790f1b7a83ac` → `succeeded`、`drw.1`、**`saved_file_reloaded_and_verified=true`**、`toolkit_code=0`、`sha256=c87b8bab7720d327cdcd1b251366b383163b6b111b6728bbdfaec3b3bf94ac3d`

**结果：通过。** 所有接受的写任务均取得终态与保存重载 true。

---

## 场景 8：真实故障环境核对（未提供 → 未验证）

测试发起者**未提供**已准备的真实故障环境。以下记为**未验证**，未自行制造挂死、强杀或关闭用户 Creo：

- 历史 `transform → 保存后挂死 → -38` 整条链
- 受损 Creo 的自动恢复
- 内部看门狗 / 进程存活 / 文件机制（属只能靠源码或本地脚本验证的内部机制，不纳入结论）

---

## 环境事件与差异（需注意）

- 首轮 13:00Z `creo_session_status` 成功（`toolkit_code=0`）后，测试机被人工重启；13:28Z 起 `creo_startup_status` 变为 `configuration_error`（`Expecting value: line 1 column 1 (char 0)`）→ `timeout`，`coordinator_pid` 由 `23136` 变为 `17076`，`toolkit_code=-4`、`worker_exit_code=20`；`retry=true` 无法恢复。
- 重启后 `creo_startup_status` 先为 `configuration_error`，`coordinator_pid=3832`；`tasklist` 显示 **Creo 未运行**（无 `xtop/parametric`）。**人工打开 Creo** 后（`xtop.exe` 加载完成）通道即 `connected=true`、`toolkit_code=0`。
- 说明：重启后 MCP 的自动拉起 Creo 未生效，需人工打开 Creo；这是一次真实的可用性事件，非 BUG-008 恢复能力本身。
- `creo_check_environment`：Creo 12.4.0.0 可执行、Toolkit 库、mmns 模板、编译器 vcvars 均存在，`ready_to_build=true`。

---

## 分项汇总

| 场景 | 内容 | 结论 |
|---|---|---|
| 1 | 能力 / 运行身份 / 漂移 / recovery+result_delivery 指纹 / unknown_outcome+20s 断开预算 | **通过** |
| 2 | 实时会话确认（connected=true, toolkit_code=0, stale=false） | **通过** |
| 3 | 历史 unknown_outcome job 只读核对（未修改） | **通过** |
| 4 | 新建零件 + 600 mm³ 建模 + MARKER=8 | **通过** |
| 5 | 预期失败 + 回滚（体积 600 / MARKER=8 保留 / 计划内参数回滚 / revision 不变） | **通过**（须按单计划执行） |
| 6 | 重叠 retry / 并发协调 | **未通过**；retry 恒报错；**并发未验证** |
| 7 | 恢复后独立建模（120 mm³）+ plate（600 mm³）+ 基线核对 + 工程图 | **通过** |
| 8 | 真实故障环境链（transform→保存挂死→-38 等） | **未验证**（未提供环境） |

- **通过**：场景 1、2、3、4、5、7
- **未通过**：场景 6（`creo_startup_status(retry=true)` 在 ready 与不可用两种状态下均返回无明细错误，无法观测并发协调）
- **未验证 / 需人工处理**：场景 6 的并发部分、场景 8

## unknown 处置

- job `272513b7238040c68dce4b923725d870` / model `27143ef77ce641938543e0ca44cc3c03` 仍为 **unknown_outcome**：**保留 reservation 与写保护，未重提、未清锁、未宣告成功**。
- 待核对对象：该 job 的 native result/checkpoint、runner 创建身份、`bug009_1792054655.prt.10` 基线（`sha256=324dd24e…`）。
- 公开可行下一步：用 `creo_session_status` 复查通道；**connected=true 不等于该作业已解决**；若仍无法核对结果，需运维人工对账。

## 未验证声明（避免外推）

- 只有真实实施并发调用才可报告并发通过；本轮 retry 并发调用**在调用层即失败**，故**并发未验证**。
- 首轮掉线与重启属**环境事件**；重启后通道恢复依赖**人工打开 Creo**，不据此宣称“受损通道自动恢复”已通过。
- 只能靠源码或本地脚本验证的内部机制（重试次数/预算、临时文件清理、进程存活、看门狗）**不纳入结论**。
