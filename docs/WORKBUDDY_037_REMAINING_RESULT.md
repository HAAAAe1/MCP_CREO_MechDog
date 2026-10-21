# 0.3.7 剩余事项公开 MCP 验收结果（WorkBuddy 黑盒）

- 执行时间：2026-10-20 18:39–18:52 为第 1 轮（场景 1/2/5/7 与只读项）；19:34–21:24 为第 2 轮补测（场景 3），两轮之间操作者重启过 Creo
- 执行方式：仅通过已连接 `MCP_CREO_MechDog_dev` 公开工具调用；未读取源码/仓库配置、未运行本地脚本、未编辑 job/model JSON、未结束进程、未清除任何 unknown 保护
- 授权依据：用户明确要求按 `docs/WORKBUDDY_037_REMAINING.md` 完成任务，视为允许当前会话正常建模
- 数据来源：全部为工具返回与 Creo 实际结果；接口未提供的信息记为“无法确认”
- 会话变化：第 1 轮 `session_fingerprint=13310972307263884197`（pid 21184/22648，launch_attempt 19）；第 2 轮 `session_fingerprint=8910005913213731761`（pid 21072/23324，launch_attempt 20，Creo 由操作者重启以准备未保存件）。下表基线以第 1 轮为准，第 2 轮除会话指纹/进程号/Creo 启动次数外其余一致（服务 0.4.2、Creo 12.4 / release 44）。

## 0. 环境与记录基线

| 项目 | 实测值 |
| --- | --- |
| 公开服务版本 | `0.4.2`（`creo_capabilities.server_version`、`creo_session_status.server_version` 一致） |
| 工具数 | `tool_count=87`，`enabled_tool_count=87`，`unavailable_tools=[]` |
| 部署是否陈旧 | 否。`runtime.source_changed_since_startup=false`；`creo_check_update` 为 `up_to_date`（v0.4.2，prerelease，checked_at 2026-10-20T10:39:59Z） |
| Creo | `Creo 12.4.0.0`，`release_numeric=44`（`creo_process_snapshot`：parametric.exe pid 21184 / xtop.exe pid 22648，`matches=true`） |
| 会话 | `connection_state=connected`，`startup.state=ready`，`launch_attempt=19`，`coordinator_pid=2472` |
| session_fingerprint | `13310972307263884197` |
| 起始当前模型 | `WB_RESTART_LOFT`（part，rev4） |
| 单位约定 | `unit=mm`，`angle_unit=degrees`（capabilities 声明） |
| capability 快照指纹 | `882315c107be41092a97ab9a6f6d0affb9cc8dd3346588e3fd39180adbfc9734` |
| 无法确认项 | 服务进程内部构建身份（仅公开指纹）、PTC 许可实际可用性（`feature_creation_license=requires_actual_modeling_test`，以建模结果反证） |

界面/进程现象（保留现场，未处理）：`parametric.exe` 的窗口状态为 `hidden_only`，`top_level_count=3`、`visible_count=0`、`hung_window_observed=true`；`xtop.exe` 可见且 `visible_hung_window_observed=false`。该隐藏窗口在本次所有调用前后保持一致，未做任何干预。

### 0.1 通道异常与恢复（本次唯一一次）

| 时间 (UTC) | 事件 |
| --- | --- |
| 10:42:32 | `creo_startup_status.channel_health = {connected:false, connection_state:"invalid_probe_result", worker_exit_code:1, message:"Toolkit worker returned no valid status result"}`；`state=timeout`、`snapshot.stale=true` |
| 10:42:35 | `creo_session_status` 返回 `busy`，`owner_snapshot={operation:"session_status", pid:24304}`，`blocking_job_id=null` |
| 10:42:35 | 首次 `creo_create_sketch` 被拒：`Creo is not ready (timeout): Toolkit verification was invalidated by a subsequent failure… No modeling job was queued`（未产生作业） |
| 10:43:05 | 按工具指引执行一次显式 `creo_startup_status(retry=true)` → `checking` → `building_worker` |
| 10:43:14 | `state=ready`、`message="Toolkit connection verified; modeling is available"`、`verification_age_seconds≈1.9` |

之后全部提交均正常。全过程**未重启 Creo、未结束任何进程、未清除保护**；该次恢复只重建/校验执行器通道，未重放任何作业。建议单独登记一条通道探针稳定性条目（探针 worker 退出码 1 → 显式重试才恢复）。

## 1. 逐项结论

| 场景 | 结论 | 说明 |
| --- | --- | --- |
| 1 能力输出分页/游标 | **通过** | 无参 compact 单页有界；tools 三页连续无重漏；references/seeds/runtime 单页；evidence 跨页连续；非法与过期游标均被拒 |
| 2 圆角/倒角 + size 别名 | **通过** | 独立与计划入口全部成功；`radius/distance` 归一为 `size` 并回显；size+别名同时出现、别名错配均准入拒绝且 revision/几何不变 |
| 3 无盘接管 | **通过（补测）** | 源件 `WB_UNSAVED_04` 未保存/mm/24000；prepare→`adopted=false / adopt_pending / rev0`；关闭原件窗口后 apply→`adopted=true / ready / rev1`，sha256 与冻结时逐字节一致；shell 去顶面壁厚 2 → rev2、**7152.0 mm³**、保存重载通过 |
| 4 单位与只读枚举 | **部分通过 / 部分未验证** | 会话枚举、null+query_codes、单页完整性通过；英寸件接管拒绝、无盘/钣金/装配/图纸类型未验证 |
| 5 真并发 | **通过（含一处字段说明）** | 同一条消息内同时派发两次不同请求：一获准、一 busy；忙请求未建作业；真同时刻 `blocking_job_id/model_id=null` |
| 6 历史恢复 | **未验证（需操作者指定模型）** | 未对任何既有异常模型执行 reconcile inspect/apply；已列出现存候选供指定 |
| 7 回调 + 双圆截面 loft | **通过** | `ready`（实时 nonce 校验）；计划入口与独立入口体积均 5131.2680 mm³（容差内）；手动启动/注册/重启 0/0/0 |
| 8 Creo 9 种子/筋/装配 | **未验证** | 本机为 Creo 12.4（release 44），无 Creo 9 环境；仅验证种子哈希/版本字段语义 |

## 2. 场景 1：能力输出（通过）

- 无参调用：`detail=compact`，单页，含 `name/version/tool_count/scope/support_status/operations/families/pagination`；页码预算 `page_bytes=32768`。
- `section_counts`：`overview 30 / tools 87 / families 23 / references 9 / seeds 4 / evidence 7 / runtime 10`。
- tools 分页（`limit=5` 起）：
  - 第 1 页 `returned=5, offset=0, complete=false`，`next_cursor` offset=5
  - 第 2 页 `returned=50, offset=5..54, complete=false`，`next_cursor` offset=55
  - 第 3 页 `returned=32, offset=55..86, complete=true`，`next_cursor=null`
  - 合计 5+50+32=87，键 0–86，无重复、无遗漏
- data-heavy 分区跨页：evidence 第 1 页 `returned=3, complete=false`（offset 0→3），第 2 页 `returned=4, complete=true`，合计 7，游标连续。
- references（9）、seeds（4）、runtime（10）均单页 `complete=true`；`families` 仅通过 compact 索引（23 个 family 的 `enabled/tool`）确认，未逐条分页读取全量 family 说明。
- 非法游标：`cursor="not-a-valid-cursor"` → `Error: Invalid query cursor`。
- 过期游标：沿用同一快照（`snapshot_id 755431f5…`）的 offset=55 游标，快照 TTL 归零后调用 → `Error: Capabilities cursor is invalid or the snapshot changed/expired; query again without cursor`；随后不带游标调用即建立新快照。
- 0.3.7 的无参大载荷问题未重开。

## 3. 场景 2：圆角/倒角与 size 别名（通过）

建模路径说明：`creo_create_plate(40,30,10)` 成功（job `5c7b3afe…`，vol 12000，`saved_file_reloaded_and_verified=true`），但其产物**未进入 managed 模型表**（`creo_list_models` 无该模型；`creo_list_session_models` 中 `WB037_ROUND_BOX.model_id=null`），无法 inspect/追加特征。因此长方体改用 `creo_new_part` + `creo_create_sketch`(40×30) + `creo_extrude`(10) 构建，体积 12000 mm³。
结果：`creo_create_plate` 创建的文件可建模但不可作为受管模型追加特征（与工具描述一致，此处记录以免误用）。

真实边引用（inspect `section=edges`，12 条边）：垂直线 `id=66` 由 `(20,-15,0)→(20,-15,10)`，其余面/边（53/58 为 Z 面，63/65/67/69 为侧平面）。

| 入口 | 参数 | job_id | revision | 体积 (mm³) | size 回显 | 保存重载 |
| --- | --- | --- | --- | --- | --- | --- |
| 独立 `creo_round` | radius=2，edge 66（模型 wb037_box_r） | `020652ac3989400980cfa818e5fcdfba` | 3→4 | **11991.415924140993** | submitted & result `size=2.0` | true |
| 独立 `creo_chamfer` | distance=1，edge 66（模型 wb037_par_a） | `ca82b035bb28460db9ff98c50646f98c` | 3→4 | **11995.0** | `size=1.0` | true |
| 计划 round | `size=2`，edge 66 | `5588730768ca43ffa377bb12209aafc9` | 3→4 | **11991.415924140993** | 2.0 | true |
| 计划 round | `radius=2`（别名），edge 68 | `85a1a194a9f44ff4aadd9f39c37ff13c` | 4→5 | **11982.831803222161** | 归一后 `size=2.0` | true |
| 计划 chamfer | `size=1`，edge 64 | `84e2c99858eb44dda2fb58d2d46f9789` | 5→6 | **11977.831803222161** | 1.0 | true |
| 计划 chamfer | `distance=1`（别名），edge 70 | `38b2e53688d04e12b6a8f953b2a5129d` | 6→7 | **11972.831803222161** | 归一后 `size=1.0` | true |

解析核对：R2 单边圆柱角去料 `(r² - πr²/4)·h = 8.5841 mm³`，C1 单边去料 `0.5·1·1·10 = 5 mm³`，逐级体积与实测完全一致（11991.4159 / 11982.8318 / 11977.8318 / 11972.8318）。

native 与 compact/full 一致性（job `020652ac…`）：
- compact `result.operations[].size = 2.0`；full `result.operations[].size = 2.0`
- native 特征 `EDGE_R2`（type 913）尺寸 `d11 = 2.0`；生成圆柱面 `id=79, radius=2.0`

准入拒绝（均在 wb037_conc_a2，rev3、vol 12000 基线上发起）：

| 请求 | 原始返回 |
| --- | --- |
| round 同时给 `size=2` 与 `radius=2` | `Provide either 'radius' or 'size' for op 'round', not both` |
| chamfer 错配 `radius=1` | `op 'chamfer' does not accept 'radius'; use 'distance' or 'size'` |

拒绝后复核：`revision` 仍为 3、`volume_mm3` 仍为 12000、`part_sha256` 未变、`creo_list_jobs` 无对应作业记录。

## 4. 场景 3：无盘接管（通过，11:34–13:24 UTC 补测）

操作者素材：`WB_UNSAVED_04`（Creo 已重启的新会话，`session_fingerprint=8910005913213731761`，`launch_attempt=20`，pid 21072 / 23324）。准备态取证：

- `creo_adopt_current_model(mode=inspect)` → `available=false`、`reason_code="snapshot_required"`、`available_modes=["prepare"]`（无盘件不走文件 inspect 分支，符合契约）
- 源件：`origin=""`、`source_kind="session_only"`、`has_saved_origin=false`、`millimeter_units=true`、`dependency_free=true`、`healthy=true`、`volume_mm3=24000`（40×30×20）、features 6 / surfaces 6 / edges 12

| 步骤 | 调用 | 实测结果 |
| --- | --- | --- |
| prepare | `idempotency_key=wb037-adopt-prep-1020a, model_name=wb037_adopt_box` | job `d71b7d4189c74a808a3e2b2c9621c2ad`；`adopted=false`、`adoption.status="adopt_pending"`、`revision=0`、`source_kind="session_snapshot"`；冻结文件 `wb037_adopt_box.prt.1`，sha256 `1c498a74597e093c630bcdc6a44e1b7662cd1cc3cdacd01148f4c547b92d5cd0`；`evidence_token` 有效期 600 s；`saved_file_reloaded_and_verified=true`；当前窗口仍为原件（未切换） |
| 轮询 | `creo_get_job` | `stage="snapshot_prepared"`，`message="Frozen snapshot prepared; review evidence then apply or abandon_new"` |
| 台账复核 | `creo_list_models` | `wb037_adopt_box`：`status=adopt_pending`、`revision=0`、`adopted=false`、`part_file=null` |
| 关闭原件 | 操作者关闭 `WB_UNSAVED_04` 窗口 | apply 前 `creo_session_status`：`current_model=""`、`current_model_code=-8`（无当前模型） |
| 证据续期 | `mode=inspect, model_id=cac58d75…` | `available=true`，签发新 `evidence_token`（600 s）；未触发任何复制（源已关闭，无重复制条件） |
| apply | `idempotency_key=wb037-adopt-apply-1020a` + 新 token | job `7a87b1f40bd549b49147725be637fe3d`；`stage="adoption_committed"`、`revision=1`、`adopted=true`、`inspection_source="adoption_snapshot_verified"`、`message="Adoption committed as a managed copy; the source model was never modified"`；sha256 仍为 `1c498a74…`（与冻结时**逐字节一致**），`saved_file_reloaded_and_verified=true` |
| 显示核对 | `creo_list_session_models` | `WB037_ADOPT_BOX`：`is_current=true`、`has_saved_origin=true`、`modified=false` |
| 后续建模 | `creo_shell(thickness=2, remove_surfaces=[{kind:"surface", id:49}])`（id49 = Z=20 顶面） | job `8e3a6c5df2894c4991a4d07b423531e6`；`revision 1→2`、**volume_mm3 = 7152.0**（理论 24000 − 36×26×18 = 7152，偏差 0.0，远小于 ±0.01）、`saved_file_reloaded_and_verified=true`、surfaces 6→11、edges 12→24 |
| 终态 | `creo_list_models` | `status=ready`、`revision=2`、`adopted=true`、`snapshot.source="saved_verified"`、`inspection.volume_mm3=7152.0` |

- 冻结副本独立性：apply 前后 `part_sha256` 完全相同（`1c498a74…`），且 apply 时源窗口已关闭，证明 apply 只是确认已冻结快照、**未重新从来源复制**。
- 如实记录一处差异：原件**窗口**已关闭（apply 时 `current_model` 为空），但原件模型仍**驻留会话**——关闭后 `creo_list_session_models` 中 `WB_UNSAVED_04` 仍存在（`has_saved_origin=false`、`modified=true`、`is_current=false`），未被拭除。提示词的“关闭原件”按“关闭窗口”执行；拭除属破坏性操作，未擅自执行。
- 另记录：`mode=inspect, model_id=...` 返回的 `current_model` 块是 prepare 时记录的冻结源身份（`WB_UNSAVED_04`），不是实时窗口状态，读报告时勿当作实时值。
- 补充观察（与本场景同源）：对已托管模型直接 `mode=inspect` 会返回 `reason_code="managed_output"` 并提示改用 model_id，说明“重复接管同一来源”被前置拒绝。

## 5. 场景 4：单位与只读枚举（部分通过）

已通过部分（`creo_list_session_models`，10:48:50）：
- `total=9`、`complete=true`、`truncated=false`、`type_errors=[]`、`snapshot_only=true`、`expires_in_seconds=599`、`session_fingerprint=13310972307263884197`，未切换窗口（`is_current` 仅 `WB037_LOFT_IND` 为 true，其余 false）。
- 类型分布：**全部为 part**（9/9），全部 `modified=false`（clean），全部 `has_saved_origin=true`；未见无盘件、钣金件、装配、图纸。
- 未知/不可判定字段以 `null` + `query_codes` 给出：模板件 `MMNS_PART_SOLID_ABS.model_id=null`、`WB037_ROUND_BOX.model_id=null`（非 MCP 受管），各 `query_codes` 均为 0（查询成功）。
- 单页即完整，无第二页可验证“跨页重复/遗漏”。

未验证部分：
- 英寸独立件的接管拒绝应报 `actual_units="in"`、`volume_mm3=null`（本次无英寸件可测，无法确认该字段在拒绝分支的实际取值）。
- 无盘 / dirty / 钣金 / 装配 / 图纸类型的枚举表现（本会话不存在这些类型，且按要求不为凑矩阵创建）。

## 6. 场景 5：真并发（通过）

同一消息内同时派发两个不同建模请求（客户端并行下发，时间戳来自服务端返回）：

| 请求 | 结果 |
| --- | --- |
| `creo_new_part(model_name="wb037_par_a")` | 获准：`job_id=6972984cc409445789de5bd83d48de8e`，`created_at=2026-10-20T10:44:21.660162+00:00`，后 `succeeded / rev1` |
| `creo_new_part(model_name="wb037_par_b")` | 拒绝：`{"status":"busy","code":"toolkit_busy","accepted":false,"blocking_job_id":null,"blocking_model_id":null,"blocking_operation":"submit","owner_snapshot":{"job_id":null,"model_id":null,"operation":"submit","pid":2472,"since":"2026-10-20T10:44:21.637747+00:00"},"owner_determined":true,"retry_after_seconds":1}` |

补充一次近时序提交（第一个作业仍在执行时）：`creo_new_part("wb037_conc_b2")` → busy，`blocking_job_id=0e24424f4f7f4fd1b9c612af42d3e7b0`、`blocking_model_id=fed5d7cad4dd4c2089ee1a2190ad9f96`、`blocking_operation="execute_plan"`、`owner_snapshot.pid=24068`。

- 只允许一个获准：两次均只有一个 `accepted`。
- 忙请求未创建第二个作业：`creo_list_jobs(limit=3)` 仅含实际提交的 3 个作业；`creo_list_session_models` 无 `WB037_PAR_B`、无 `WB037_CONC_B2`。
- 字段说明（如实记录）：**真正同一时刻**派发时 `blocking_job_id/blocking_model_id` 为 `null`，仅 `blocking_operation="submit"` 与 `owner_snapshot.pid`；这是工具文档允许的 “No occupying job could be determined” 分支（获准请求的 reservation 尚未绑定 job）。要在 busy 返回里拿到具体的占用作业，需在占用作业已登记后再提交（即上面的近时序样例）。

## 7. 场景 6：历史恢复（未验证，需操作者指定）

未对任何模型执行 `creo_reconcile_model`（含 inspect）或任何 apply；未改变任何文件。当前会话/台账中可见的既有异常候选（供操作者指定，本次未动）：

| 模型 | 状态 | revision | pending_job | 备注 |
| --- | --- | --- | --- | --- |
| `wb_conc_a` (bd429fcc…) | new | 0 | `ef52edc9bfa54f33a69fe48778c44f01` | 2026-10-20 08:28 创建，未落地 |
| `wb_conc_b` (b52c2555…) | new | 0 | `63e6b4f77c674b64859d4644aaca700e` | 同上 |
| `wb_close_orig` (f81404ab…) | ready / adopted | 5 | null | `source_kind=file`，rev5 正常 |
| `wb_close_orig` (03d8b89a…) | abandoned | 0 | null | 已有 `reconciliation.action="abandon_new"`（08:40:12） |

四动作矩阵（基线、候选、健康 live、无基线归档）与后续“续作/已归档编辑拒绝”核对，均需操作者明确指定模型后另起一轮执行。

## 8. 场景 7：回调 + 双圆截面 loft（通过）

调用前 `creo_callback_status`（10:47:12）：
- `readiness="ready"`，`reason="live_identity_verified"`（实时 nonce + 哈希校验）
- `protocol=3`、`contract="blend-selection-v3-ordered-curves-mm"`、`loader_abi=1`
- `deployed` 与 `loaded` 哈希一致：`dll_sha256=71b1093a…`、`loader_sha256=9ea54464…`；`loaded.process_id=22648`、`active_request=false`、`terminated=false`、`initialize_code=0`
- 手动启动 / 注册 / 重启次数：**0 / 0 / 0**（回调为操作者既有注册，本次未写 config.pro、未加载 DLL、未结束 Creo）

几何验证（两圆截面：R10 @ Z0、R6 @ Z25，`straight`；期望体积 4900π/3 = 5131.26803 mm³，容差 max(0.01, V×1e-6)=0.01 mm³）：

| 入口 | job_id | revision | 体积 (mm³) | 偏差 | 保存重载 |
| --- | --- | --- | --- | --- | --- |
| 计划入口（sketch+sketch+loft，新建件 `ai_part_5d5e3a05e645`） | `332e5c122dc54d35b36075265ca2c2a6` | 1 | **5131.268000863329** | 3.0e-5 | true |
| 独立入口（new_part→sketch→sketch→`creo_loft`，`wb037_loft_ind`） | `a9ec559f48df4f80b471a33a4b76185b` | 4 | **5131.268000863329** | 3.0e-5 | true |

两个入口均 `success=true`、`operations[].succeeded=true`、`has_solid=true`、bodies=1、surfaces=4、edges=6。升级/回退/重启与目录并存分支本次未触发（无真实阶段可测），未验证。

## 9. 场景 8：Creo 9 种子/筋/装配（未验证）

- 环境为 Creo 12.4.0.0 / `release_numeric=44`，**无真实 Creo 9**，按提示词该场景整体不执行；不以 Creo 12 结果替代。
- 仅取证与版本无关的种子语义（`creo_list_seeds` / `creo_validate_seed("two_straight")`）：
  - `available=true`，`reason="Hash matches the verified seed manifest"`，`actual_sha256` 与清单一致
  - `seed_build_version=null`、`seed_build_version_source=null`（无来源即空，符合预期）
  - `native_compatibility.status="not_verified_for_current_session"`，其历史 `observations` 绑定 `creo_release_numeric=44` 与旧 `session_fingerprint=7969341675533995546`（≠ 当前 `13310972307263884197`），未越权声称当前会话兼容
  - 种子清单 9 个：two_straight / two_smooth / three_straight / three_smooth / four_straight / four_smooth / five_smooth / six_straight / six_smooth，`available` 均为哈希级通过
- 筋（含 flip 与材料侧）、装配位姿更新到三平面约束、矩阵/面位置/法向重载核对：未验证。

## 10. 本次生成的测试模型（独立命名，未复用用户旧模型）

| 模型 | model_id | 用途 | 终态 |
| --- | --- | --- | --- |
| wb037_round_box | 无（create_plate，非受管） | 40×30×10 基线 | job 成功，vol 12000 |
| wb037_box_r | 610ad063a1754d0484aea71e85927843 | 独立 round R2 | ready rev4，vol 11991.4159 |
| wb037_par_a | 6bd6735d87ee4d1c9ea8382d9a30ec45 | 独立 chamfer C1 | ready rev4，vol 11995 |
| wb037_conc_a2 | fed5d7cad4dd4c2089ee1a2190ad9f96 | 计划 size/别名 四例 + 两次准入拒绝 | ready rev7，vol 11972.8318 |
| wb037_par_a（并发获准件） | 同上 | 场景 5 获准请求 | — |
| ai_part_5d5e3a05e645 | 5d5e3a05e64544d3bdccc2ca50bb31d5 | 计划入口双圆 loft | ready rev1，vol 5131.2680 |
| wb037_loft_ind | d5b25423f6e841a0800b0e7ad9e948ad | 独立入口双圆 loft | ready rev4，vol 5131.2680 |
| wb037_adopt_box | cac58d753c2d0b7052d62ab531f49a25 | 场景 3：未保存 40×30×20 件冻结接管 + shell 去顶面壁厚 2 | ready rev2，adopted=true，vol 7152.0 |

## 11. 未验证清单（汇总）

1. 场景 4 的英寸件接管拒绝字段（`actual_units="in"`、`volume_mm3=null`）与无盘/钣金/装配/图纸类型枚举（无盘件已在场景 3 得到独立证据：`source_kind="session_only"`、`has_saved_origin=false`、`modified=true`）。
2. 场景 6 全部（需指定异常模型后才可 inspect/apply 及四动作矩阵）。
3. 场景 8 全部（需 Creo 9 实机）。
4. 场景 1 中 `families` 分区仅核对 compact 索引与计数，未逐页读取全量 family 说明。
5. 内部故障注入类场景（快照改写、真实再生失败、恢复再中断）按提示词未人为制造；本次会话未自然出现。
6. 场景 7 的升级/回退/重启与目录并存分支（无真实阶段可测）。

## 12. 需要操作者配合的下一步

1. **场景 4**：准备一个英寸（in）独立件为当前窗口，用于接管拒绝分支取证。
2. **场景 6**：从第 7 节候选或其它模型中指定一个异常模型及其允许的动作，再执行不带 live 的 inspect 与后续 apply。
2. **场景 4**：准备一个英寸（in）独立件为当前窗口，用于接管拒绝分支取证。
3. **场景 6**：从第 7 节候选或其它模型中指定一个异常模型及其允许的动作，再执行不带 live 的 inspect 与后续 apply。
4. **场景 8**：在真实 Creo 9 + Toolkit 9 环境复跑种子/筋/装配三项。
