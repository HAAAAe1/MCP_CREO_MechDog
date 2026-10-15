# BUG-009 WorkBuddy 黑盒验收结果（2026-10-15）

依据 `docs/validation/BUG-009-WorkBuddy-test.md` 执行。仅直接调用已连接 MCP 工具，记录工具实际返回与 Creo 实际结果；未读取/分析/修改源码，未执行本地脚本、单元测试或开发检查。时间戳均为工具返回的 UTC 时间。

服务版本：**0.3.1**。

---

## 0. 公开身份与前置

| 项 | 实际返回 |
|---|---|
| 服务版本 | `0.3.1`（capabilities.version 与 startup_status.update.current_version 一致） |
| runtime 入口 | `python_executable=E:\Projects\MCP_CREO_MechDog\.venv\Scripts\python.exe`；`server_entry=E:\Projects\MCP_CREO_MechDog\server.py` |
| code_root / data_root | 均为 `E:\Projects\MCP_CREO_MechDog`；`resource_root` 同 |
| 启动指纹 | `runtime.source_fingerprints_at_startup` 提供 server.py(`2fca4298…`)、bridge.py(`8d41b695…`)、version.py(`03d9ad0a…`) 等哈希；`source_changed_since_startup=false` |
| 工具规模 | `tool_count=82`、`enabled_tool_count=82`、`unavailable_tools=[]`、`disabled_tools_hidden=true` |
| 环境 | Creo `12.4.0.0`；Toolkit 头、ptasyncmd/protkmd_NU/protk_dllmd_NU/ucore/udata 库、通信程序、mmns 模板、编译器脚本均 `exists`；`ready_to_build=true`；`license_usable=unverified_here` |
| 启动时序 | 首查 `state=waiting_for_connection`、`connected=false`、`connection_state=connection_failed`、`toolkit_code=-11`、`worker_exit_code=20`、`launch_attempt=12`；`retry=true` 后 `state=checking`；再查 `state=ready`、`connected=true`、`toolkit_code=0`、`release_numeric=44` |
| 许可 | `feature_creation_license=requires_actual_modeling_test`（仅由实际建模证明） |

`scheduling` 描述（capabilities 原文要点）：`native_channels=1`；`admission=reject_busy_without_creating_a_job`；`busy_error="isError=true with matching JSON text and structuredContent"`；`owner_fields=[blocking_job_id, blocking_model_id, blocking_operation]`；`retry_after_seconds=1`；`retry_interval_is_completion_estimate=false`；`terminal_contract="Model finalized under channel lock; job terminal published after release. Another caller may then occupy the channel."`；`runner_channel_wait_seconds=120`；`queue_guarantees="No public FIFO, capacity or admission-wait guarantee"`；`non_native_queries=[get_job,list_jobs,inspect_model,list_models]`。

无法确认项：无（接口未提供构建 commit/分支等字段，此处未据版本号外推）。

---

## 1. 通过

### 场景 1 —— 矩形草图拉伸与体积断言 ✅

model_id `66a977c8335b43a887701a00cf41eff8`（bug009_rect）

| 步骤 | job_id | 终态 | revision | created → finished (UTC) | 保存重载 |
|---|---|---|---|---|---|
| new_part | `6a7928ce1a64442aab82903a88e34f48` | succeeded | 1 | 09:20:32.330 → 09:20:45.346 | true |
| sketch `rect10` 10×10 | `73e1281be87b412994bf1b214c2d8650` | succeeded | 2 | 09:21:01.560 → 09:21:08.419 | true |
| extrude `ext6` depth=6 | `266e0fd044b34316a1321cefa64d4052` | succeeded | 3 | 09:21:19.651 → 09:21:26.386 | true |

- **体积 = 600.0 mm³**（`volume_mm3=600.0`、`volume_query_code=0`、`has_solid=true`、surfaces=6、edges=12、bodies=1）
- 零件文件 `bug009_rect.prt.4`，sha256 `1d9ea7175d3e2245086397a2ebb24b22e7b8ff03d9c0b96e3a28aaf383c80aaa`
- 每步 `toolkit_code=0`、`saved_file_reloaded_and_verified=true`

### 场景 2 —— 终态后连续写入 20 轮 ✅（附即时性偏差说明，见 §3）

每轮：上次终态 → 立即提交下一项（无额外等待，除轮询本身），全部 `succeeded`，**revision 严格单增 4→23**，save 全部 `saved_file_reloaded_and_verified=true`，`toolkit_code=0`。序列中**未出现 busy**（符合 `terminal_contract`：终态在通道释放后发布）。

| 轮 | 操作 | job_id | created (UTC) | finished (UTC) | revision |
|---|---|---|---|---|---|
| 1 | set_parameters seq=1 | c7024aba5b354449af5dc9e5032724c7 | 09:21:43.288 | 09:21:49.874 | 4 |
| 2 | save | 8e28638abca5438aa2d6955af54bf5eb | 09:22:01.018 | 09:22:07.431 | 5 |
| 3 | set_parameters seq=3 | f249b62a2c994bf8b90c8fd37928d652 | 09:22:17.660 | 09:22:24.353 | 6 |
| 4 | save | fc76af4def65412b99069e0d091634ca | 09:22:35.342 | 09:22:41.982 | 7 |
| 5 | set_parameters seq=5 | b37d053ed6734e3c832608d8f2000e5a | 09:22:52.806 | 09:22:59.232 | 8 |
| 6 | save | 9d2ccfb85662461397d883ecd3fa8d5b | 09:23:11.820 | 09:23:18.307 | 9 |
| 7 | set_parameters seq=7 | ca82b0e7231b48ff8e08ef724d9a8b30 | 09:23:30.309 | 09:23:36.798 | 10 |
| 8 | save | 715addd932b5449a814eeff7668a17df | 09:23:49.011 | 09:23:55.765 | 11 |
| 9 | set_parameters seq=9 | 587f1870c1bc40e595014da4259e6c1f | 09:24:06.798 | 09:24:13.375 | 12 |
| 10 | save | 741559440ff4487784f405c4588a1250 | 09:29:19.440 | 09:29:26.032 | 13 |
| 11 | set_parameters seq=11 | 5c1e114be5574bb8b2d034c51e4e2256 | 09:29:37.907 | 09:29:44.354 | 14 |
| 12 | save | 781d215425cc44fba7dffee165c7ba95 | 09:29:55.919 | 09:30:02.310 | 15 |
| 13 | set_parameters seq=13 | 5fa157673b724473a0c4ba076deedc13 | 09:30:13.772 | 09:30:20.205 | 16 |
| 14 | save | 5bd97519257b42da8217e0245da5cb0c | 09:30:31.907 | 09:30:38.253 | 17 |
| 15 | set_parameters seq=15 | f451b6242b224b7eb3d9e0f1eabf197a | 09:30:50.386 | 09:30:56.892 | 18 |
| 16 | save | 07d3a00fa0a248689ba3cdce11dd0eec | 09:31:14.476 | 09:31:20.821 | 19 |
| 17 | set_parameters seq=17 | cfcce73e9d644edabdf691f29bec61b9 | 09:31:33.058 | 09:31:39.518 | 20 |
| 18 | save（busy 拒绝后的重试） | 48c5c3f8632a45e6847515a469627eaa | 09:31:50.433 | 09:31:56.784 | 21 |
| 19 | set_parameters seq=19 | a8cc8755d4014402862eed301bf6149d | 09:32:08.686 | 09:32:15.124 | 22 |
| 20 | save | 9138d45698c44bf998bdc1d055cd797f | 09:32:27.758 | 09:32:34.532 | 23 |

备注：第 17 轮运行中额外叠加提交的 save 被明确拒绝（busy，见场景 4），按指引在占用操作结束后重试，即第 18 轮。第 9→10 轮间的约 5 分钟空档来自验收过程被打断后恢复，非服务侧延迟。

### 场景 3 —— 同模型并行导出 ✅（已实际并行）

同一时刻提交 STL / STEP / IGES（同一批次并行调用）：

| 格式 | 结果 | job_id | created (UTC) | finished (UTC) | 产物 |
|---|---|---|---|---|---|
| STL | 接受，succeeded | `772acac7198c498bb3a442b1eed002a6` | 09:32:48.124 | 09:32:54.377 | `jobs\772acac7…\output\bug009_rect.stl` |
| STEP | 结构化 busy（未创建 job） | — | — | — | — |
| IGES | 结构化 busy（未创建 job） | — | — | — | — |

- 三次调用同批发出，STL 被接受并完成（`readonly=true`，`saved_file_reloaded_and_verified=false`，导出不改模型，属预期；`inspection_source=live_query`），STEP/IGES 在通道占用期内被拒 → **存在时间重叠**。
- 两个被拒请求在 STL 终态后重试成功：STEP `226955331250411dad1b597afad9c377`（09:33:09.516 → 09:33:15.533，`bug009_rect.stp`）；IGES `0bceac5608c44b8191120b074dcad54f`（09:33:28.886 → 09:33:34.895，`bug009_rect.igs`）。三者均为 `succeeded`、`toolkit_code=0`。

### 场景 4 —— busy 结构与占用核对 ✅（含一项偏差，见 §3-a）

**样本 A（占用者可确定）**：第 17 轮运行中提交 save，原文返回：

```json
{"status":"busy","code":"toolkit_busy","accepted":false,
 "blocking_job_id":"cfcce73e9d644edabdf691f29bec61b9",
 "blocking_model_id":"66a977c8335b43a887701a00cf41eff8",
 "blocking_operation":"execute_plan",
 "owner_snapshot":{"job_id":"cfcce73e9d644edabdf691f29bec61b9","model_id":"66a977c8335b43a887701a00cf41eff8","operation":"execute_plan","pid":5840,"since":"2026-10-15T09:31:33.420721+00:00"},
 "owner_determined":true,"retry_after_seconds":1,
 "retry_guidance":"Poll creo_get_job(job_id='cfcce73e…', detail='compact') until terminal; inspect unknown_outcome before retrying. This request was not accepted. Retry this request after 1 second only when the occupying operation has finished; re-read the model revision before writing. Do not resubmit an already accepted job.",
 "message":"Creo Toolkit is busy with another operation"}
```

- 占用者核对：`get_job(cfcce73e9d644edabdf691f29bec61b9)` → 同一 job、同一 model，`succeeded`，revision 20 → **占用 job 与实际一致**。
- 字段齐全：`status=busy`、`accepted=false`、占用 job/model/操作、`retry_after_seconds=1`（重查间隔）、重试指引。

**样本 B（占用者不可确定）**：并行导出的 STEP/IGES 被拒时 `owner_determined=false`、`blocking_job_id/blocking_model_id/blocking_operation=null`、`owner_snapshot=null`，`retry_guidance` 说明"占用者可能是会话探针、构建或另一个客户端"。两个请求均返回结构化 busy，未创建 job。

### 场景 5 —— 任务运行时并行查询 ✅

在第 15 轮（`f451b6242b224b7eb3d9e0f1eabf197a`，`status=running`、`stage=connect`）运行期间，同批并行查询：

- `get_job` → `running`，`stage=connect`
- `list_jobs(limit=5)` → 返回 running 作业 + 既往 succeeded 作业
- `inspect_model` → `ready`、`revision=17`、`pending_job=f451b624…`、`snapshot.mutation_pending=true`、`live_state_verified=false`
- `list_models(limit=5)` → 返回持久化模型列表

四项均返回持久化状态，未因通道占用被拒（符合 `non_native_queries`）。

### 场景 6 —— 同 expected_revision 并行写入 ✅

同一批次、同一 `expected_revision=23` 并行提交两次 `set_parameters`：

| 请求 | 结果 | job_id | revision |
|---|---|---|---|
| `{race_a:1}` | 接受，succeeded | `1bba970af1544e2685fb886b7b17d05d`（09:33:48.177 → 09:33:54.627） | 23 → **24** |
| `{race_b:1}` | 结构化 busy（`accepted=false`、`owner_determined=false`） | — | 未应用 |

- 只接受一次有效修改，revsion 23→24，无丢失更新、无重复应用、无倒退。
- 旧 revision 提交（`expected_revision=23`，当前为 24）→ 明确拒绝：`Error executing tool creo_set_parameters: Stale revision: current model revision is 24`。

### 场景 7 —— 原生失败与回滚核对 ✅

model_id `2dbcf1e387d941fa8a9365ad92ac8378`（bug009_fail）

| 步骤 | job_id | 结果 | revision | created → finished (UTC) |
|---|---|---|---|---|
| new_part | `da65f8bd69684e978af5ad60cacaa911` | succeeded | 1 | 09:34:11.720 → 09:34:18.695 |
| set_parameters `{test_marker:1}` | `0e38a0676f2642b3b83fe1089e37da48` | succeeded | 2 | 09:34:30.332 → 09:34:36.601 |
| extrude `bad_ext` 引用 `no_such_sketch` | `5e6adba848a540308206075158af58e3` | **failed** | 未推进 | 09:34:48.971 → 09:34:54.774 |

失败作业关键字段：`status=failed`、`stage=executing_feature_plan`、`failed_stage=execute_extrude`、`failed_operation_index=0`、`failed_toolkit_call=null`、`message="Unknown feature label: no_such_sketch"`、`toolkit_code=-1`、**`rollback_succeeded=true`**、`inspection_source=rollback_verified`、`saved_file_reloaded_and_verified=false`。

`native_log_tail`（节选）显示执行顺序：`PHASE=execute_extrude` → `BUILD_FAILED=Unknown feature label: no_such_sketch` → `PHASE=rollback_to_saved_checkpoint` → `ProSolidRegenerate(...)=0`，随后重新巡检成功、`DISCONNECT=0`。

失败后状态核对：
- `inspect_model` → `revision=2`（**未推进**）、features=4（仅 3 基准面 + 坐标系）、`has_solid=false`、`pending_job=null`、`last_job=`失败作业；`TEST_MARKER` 参数保留（值 1）
- `refresh_model` → job `06801856756d424db40bea0e57b6fe43`（readonly），09:35:12.770 → 09:35:18.521，`succeeded`、revision 2、`inspection_source=live_query`、`healthy=true`
- 随后成功编辑：sketch `rect_ok` job `c208255fc12d4a55bf1407adb99b51d0` → rev 3；extrude `ok_ext` depth=5 job `d143b25340c341ecbb4b71e8061fec8b` → rev 4，**体积 499.99999999999994 mm³**，`saved_file_reloaded_and_verified=true`
- 全程未出现 `unknown_outcome`，未靠重复提交或清 pending 恢复。

---

## 2. 失败

无失败场景。所有预期成功的操作均 `succeeded`，所有预期拒绝的操作均被明确拒绝且未创建 job。

## 3. 偏差与观察（需开发者确认）

**a. busy 响应的 MCP 错误标志存疑（建议登记缺陷）**

`scheduling.busy_error` 声明 busy 应为 `isError=true`。实测对比（同一客户端、同一会话）：

- busy 响应 → 返回体为纯 JSON 结构（`status/code/accepted/blocking_*/owner_*/retry_*`），**未呈现为工具错误**
- 旧 revision 拒绝 → 呈现为 `Error executing tool creo_set_parameters: Stale revision: current model revision is 24`

两者渲染方式不同，提示 busy 很可能以 `isError=false` 返回，与描述不符。**受本客户端呈现能力限制，无法直接读取协议层 `isError` 字段，故记为"疑似偏差/待确认"**，不作为"通过"结论。

**b. 并发导出被拒时占用者归属缺失**

场景 3 中 STL 导出 job（`772acac7…`）确实在飞行，但同批 STEP/IGES 的 busy 响应 `owner_determined=false`、`blocking_job_id=null`。契约允许 ID 为 null（"探针/构建/另一客户端"），但此处实际占用者是一个可识别的 job，指引文案与实际不符。属可观测性偏差，未造成请求丢失。

**c. 场景 2 的"零延迟立即提交"未严格达成**

终态到下次提交的间隔约 **10.2–12.6 s**，主要由客户端"轮询等待 → 读结果 → 回程"节拍构成；未插入刻意的额外等待，但**不能声称零延迟即时提交**。该间隔不影响 revsion 单调性结论（20 轮无丢失更新）。

## 4. 未验证（不纳入通过）

- **内部锁清理机制**、**文件占用注入**、**重试次数/预算**、**临时文件清理**：无法由 MCP 观察或安全构造，未验证。
- **真实通道超时**（`runner_channel_wait_seconds=120`）：未构造。
- **两个独立 MCP 客户端进程同时调用**：本次为同一客户端同批并行调用，非双客户端；标为未验证。
- **`refresh_model`/导出/`session_status` 在占用期的按规则拒绝**：场景 5 期间未单独复现该分支（`refresh_model` 是在通道空闲时执行）。
- 许可可用性（`feature_creation_license=requires_actual_modeling_test`）：本次实际建模成功，可视为已由建模证明；双版本（Creo 10）未测。

## 5. 证据边界

- 本次验收为 **E 盘开发服务、版本 0.3.1**，通过 runtime 入口与启动指纹确认部署，未凭版本号判定。
- 全部结论基于工具实际返回与 Creo 实际结果；未读取源码、未运行本地测试。
- 采集窗口：2026-10-15 09:19:10Z – 09:35:57Z。
- 受测模型：`bug009_rect`（66a977c8335b43a887701a00cf41eff8，终态 rev 23）、`bug009_fail`（2dbcf1e387d941fa8a9365ad92ac8378，终态 rev 4）。
