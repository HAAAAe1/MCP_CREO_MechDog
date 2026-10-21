# BUG-056 / DEV-036 通道静默掉线核实记录（2026-10-17）

执行依据 [DEV-036](../work-items/DEV-036.md) G0～G5；缺陷主卡 [BUG-056](../work-items/BUG-056.md)。本文为开发者离线核对与受控取证的原始记录，时间线同时标注 UTC 与北京时间（Asia/Shanghai，UTC+8）；文件系统与日志中的原始时间戳保持原样。

**结论先行：BUG-056 定位为名字服务器（nmsd）侧会话信息失效——连接请求从未到达 Creo 进程；「固定 37～41 秒失效」是客户端轮询节奏叠加快照 30 秒新鲜期的观测伪影；服务侧探测/快照/分类逻辑经核对无缺陷。当前批次 Creo 的异步端点自 11:36～11:42 UTC 起永久失效（10 小时未自愈），T03/T04/T05 等实机复测需先由用户处置环境（重启 Creo），本轮不自动执行。**

## 环境与受测身份

- 工作目录 `E:\Projects\MCP_CREO_MechDog`，分支 `codex/dev-036-toolkit-stability`，基线提交 `37b7463`（与建卡起点一致）。本轮修改 `creo_startup.py`、`server.py`、新增 `tests/unit/test_session_process_snapshot.py`；取证期间源码 dirty，dev_check 记录 `build/development_check.json`（success=true，单元 passed）。
- Windows 11 x64；Creo 12.4.0.0（安装根 C:\Program Files\PTC\Creo 12.4.0.0）；本机 `config.json` 中 `creo_session_id=""`（空，未选择会话）。
- 进程身份（WMI `Win32_Process.CreationDate`，换算 UTC）：

| 进程 | PID | 创建时间（UTC/本地） | 父进程 | 说明 |
| --- | --- | --- | --- | --- |
| nmsd.exe | 25996 | 06:03:04 / 14:03 | cmd.exe 14764 | 批次 B 遗留名字服务，`-noservice -timeout 300`，跨批次存活 15h+ |
| parametric.exe | 18720 | 11:28:18 / 19:28 | explorer.exe | 批次 C，协调器 launch_attempt=8 |
| xtop.exe | 24056 | 11:28:18 / 19:28 | cmd.exe 26440 | 批次 C 主进程（`-ppid 18720`） |
| pro_comm_msg.exe | 12612 | 11:28:20 / 19:28 | xtop.exe | 批次 C 通信代理（xtop 子进程） |
| server.py（venv→runtime 成对） | 8 对 16 个 | 18:36～20:48 本地 | codex.exe×5、ZCode.exe×3 | 多 MCP 客户端服务实例并存 |

## G0：静态核对事实

代码路径（基线 `37b7463` + 本轮修改前状态）：

1. `native/worker.cpp`：探测命令 `status`/`callback-status` 固定 `return result ? 20 : 0`——退出码 20 是探测失败分支结果，非独立错误（确认 BUG-056 既有判断）。`connect_creo()` 读取 `MECHDOG_CREO_SESSION_ID`；仅当该变量非空时做 `ProEngineerConnectIdGet` 会话核对，不匹配则主动断开并返回 `PRO_TK_E_NOT_FOUND`。本机 config 为空串，`native_environment()` 注入前会 pop 掉该变量，**该核对分支从未触发**，全部 -4 直接来自 `ProEngineerConnect` 本身。
2. SDK（本机 12.4 `ProCore.h`）官方语义：`PRO_TK_E_NOT_FOUND (-4)` =「找不到匹配特征的 Creo 会话，**或无法从名字服务器读取该会话的信息**」；`PRO_TK_NOT_EXIST` = 无任何会话；`PRO_TK_E_BUSY` = `timeout_sec` 内未响应初始化；`PRO_TK_CANT_MODIFY` = 未设 `PRO_COMM_MSG_EXE`。当前观测（-4、非超时、非 E_BUSY）唯一指向「名字服务器信息不可读」。
3. `bridge.py`：`session_status()` 持 `toolkit_lock` 串行执行 worker 探测，结果原子写入 `build/toolkit_health.json`；`_record_probe_result` 对 worker 异常输出/disconnect 失败有独立分类（既有单测覆盖）。探测预算 = connect_timeout + min(connect_timeout,15) + 5。
4. `creo_startup.py`：`creo_session_status` 实时路径与启动协商循环均用 `connect_timeout_seconds=2`；`READY_FRESHNESS_SECONDS=30` 使 ready 快照 30 秒后标记 `stale`；`status()` 仅在 `channel_health.checked_at >= verified_at` 且失败时才把 ready 降级——快照陈旧与真实失败已正确区分（对应 T01 行为，不与 BUG-011 的显示问题混淆：本轮不修改 BUG-011）。
5. `generic_bridge.py`：generic 作业连接共用同一 worker 路径与环境；作业内 connect 失败按既有保护转 unknown_outcome（M2 实测一致）。

## 时间线（综合 startup.log、WMI、jobs/、trail、toolkit_health）

startup.log 路径 `%LOCALAPPDATA%\MCP_CREO_MechDog\startup\6235eee86323f49c8d99f96a\startup.log`；以下 UTC（本地+8）：

| UTC | 事件 | 来源 |
| --- | --- | --- |
| 06:03 | 批次 B（用户下午手动会话）启动，nmsd.exe 就位；该批次后被用户关闭，nmsd 存活 | WMI |
| 11:19:47–11:24:35 | 两轮启动协商 waiting_for_connection 循环超时，无 launch（当时无 Creo 进程） | startup.log |
| 11:28:17.8 | 协调器 `starting`（launch_attempt=8），parametric/xtop 11:28:18 创建 | startup.log/WMI |
| 11:28:32.4 | **ready connected=true**（launch 后 14 秒） | startup.log |
| ~11:30:04 | WorkBuddy 观测第一次掉线（BUG-055 记录） | BUG-055 |
| 11:30:19→11:30:25 | 重协商 ready（6 秒）；11:30:50 两协调器实例交错（.525/.172 相隔 1.6 秒）后 11:30:57 ready；11:31:26→11:31:35 ready | startup.log |
| 11:33:20–21 | trail 记录 REC_M2 基线再生未更改；随后**最后一次成功 IPC 初始化**（connected to Pro/E, asynchronous, creo_worker.exe） | trail.txt.26 |
| 11:36:27–11:36:34 | M1 恢复作业 `7715024458344c70832ebfc7ff6311c7` succeeded——**证明 11:31:35 ready 后通道至少存活约 5 分钟** | jobs/ |
| 11:36～11:42 之间 | （失效发生窗口，无探测/作业覆盖） | — |
| 11:42:22–11:42:29 | M2 恢复作业 `194712b5135e424a82f4f76ad18e0eb0` connect -4 → unknown_outcome；trail 中**无任何对应 IPC 初始化记录** | jobs/、trail.txt.26 |
| 12:30:39–12:32 | 开发者 retry 协商 waiting_for_connection 循环超时；当时记录「parametric/xtop 均已退出」——**该观测有误**（见下） | startup.log、BUG-056 补充观测 |
| 13:21:37–13:24:10 | 多实例协商（13:21:37 两实例交错）循环超时，探测持续 -4 | startup.log |
| 13:22:49.3 | `toolkit_health.json` 记录 not_found_or_unreadable/-4/exit20（期间一次真实探测） | toolkit_health |
| 13:31:29.7 | 本轮 G1 单次 MCP `creo_session_status`：-4/exit20 复现 | 本轮 |
| 13:31:54–13:31:59 | 本轮 G3 判别探测：**connect_timeout=30 时 worker 4.8 秒快速返回 -4**（非超时/非 E_BUSY） | 本轮 |

**BUG-056「12:31 后 parametric/xtop 均已退出」观测证伪**：WMI CreationDate 证明 PID 18720/24056 自 11:28:18 UTC 持续存活至今（与 BUG-055 会话同批同 PID），两 PID 同时复用概率可忽略；当时判断方法存疑，该观测不再作为分类依据。「启动超时+进程退出」与「进程存活但通道失效」两种现象在本记录中已按 DEV-036 要求分开。

## G1：会话进入条件与单次有界探测

进入前按约定记录：BUG-001 根因核对结论见 [BUG-001-hang-offline](BUG-001-hang-offline-2026-10-17.md)（批次 A：连接到达 Creo、初始化 -97、随后 -11 与 AppHangB1，底层诱因未定）；当前批次 C 为 11:28 UTC 新实例，非当年卡死实例。GUI 只读检查（`IsHungAppWindow`，不连接 Toolkit）：xtop 主窗口 `hung=false`，标题 `AI_PART_588D955F8935 (启用的) - Creo Parametric 12`，无可见弹窗窗口。随后执行一次 MCP `creo_session_status`（13:31:29 UTC）：connected=false、not_found_or_unreadable、-4、exit 20——真实连接失败复现。按任务卡「失败即停止」，不进入 G2 间隔探测序列，不调用 retry。

## 根因定位与排除

**已证事实链**：Creo 进程与 GUI 消息循环存活（WMI+IsHungAppWindow）；探测 2 秒与 30 秒预算均快速 -4（非超时类错误）；SDK 语义 -4 = 名字服务器信息不可读；trail 证明失败期的连接请求从未到达 Creo（无 IPC 初始化记录）；nmsd 为上一批次遗留（06:03 UTC）且跨批次存活 15h+。

**结论**：批次 C 早期（11:28–11:36，trail 记录 16+ 次成功 IPC 初始化）经遗留 nmsd 连接正常；11:36～11:42 间 nmsd 停止提供有效会话信息，此后所有连接协商在名字服务器层失败返回 -4，Creo 本身未受影响。与批次 A（BUG-001：请求到达 Creo、初始化失败 -97/-11、AppHang）是**不同层的失败**，不据此重开 BUG-001。

**「固定 37～41 秒」证伪**：11:31:35 ready 后通道存活至 11:36:27（M1 作业成功）超过 5 分钟，不存在通道自身的 ~40 秒周期失效。表观节奏 = 客户端按快照 30 秒 `stale` 期重查 + 轮询间隔 + 探测耗时；三次「验证通过→失效」实为两次短暂抖动（重试即恢复）与第三次永久失效的混合，WorkBuddy 观测到的间隔由其调用节奏决定。

**候选原因处置**：
- 名字服务器陈旧/失效——**主因，证据充分**（nmsd 跨批次 + trail 缺失 + SDK 语义 + 快速 -4）。
- 多 MCP 服务实例并存（8 对 server.py）——**并存因素已证**（startup.log 11:30:50、13:21:37 两处双实例交错），但 toolkit_lock 保证探测串行，不产生并发连接，判定为观测噪声放大器而非 -4 根因。
- 探测缺陷/快照误报/2 秒预算不足/会话 ID 核对分支/进程退出/许可证（全程无 NO_LICENSE 记录）——**逐一排除**（上文事实链）。
- nmsd 内部触发器（为何 11:36–11:42 间失效：批次 B 残留条目清理、空闲超时、连接活动累积等）——**nmsd 黑盒不可观测，列为残余假设**；批次 A std.err 的 12 条 "giving up- peer appn and/or msg module is not alive"（01:35 UTC，强制中断期）证明通信对端死亡消息存在先例，但批次 C 期间 std.err 无新写入，不能把批次 A 的中断链归因到批次 C。

## 最小修复（服务侧）与测试

修改 `creo_startup.py`：新增只读 `process_snapshot()`（复用 `inventory()`，输出 pid/name/created_at(FILETIME→ISO)/created_filetime/image/matches/uncertain/observed_at），集成进 `CreoStartup.session_status()` 的实时探测路径（busy/probe_failed/成功/失败各返回路径均携带 `creo_process_snapshot`；coordinator 运行中的快照路径保持不变）；配置或 inventory 失败时置 `available=false, reason=...`，不掩盖原生结果。`server.py` 工具描述同步。**不改变连接/重试/超时/保护行为**（无证据支持其必要性：30 秒同样 -4）。

验收：`tests/unit/test_session_process_snapshot.py` 7 例（进程存活区分端点失效、无进程、inventory 失败、配置错误、busy、成功、快照路径不变）通过；`python tools/dev_check.py` 全量通过（success=true、单元 passed、无新增语言诊断；存量 35 lint/25 未格式化文件为既有基线）。未改 C++，无需重建 worker。**注意：字段在 MCP 服务重启后生效，当前运行中的服务进程仍为旧代码。**

## T 矩阵执行状态

| 场景 | 状态 |
| --- | --- |
| T01 状态与时效 | 快照/实时/陈旧区分经静态核对与既有+新单测验证；会话身份由新增 `creo_process_snapshot` 提供（服务重启后可用）。夹具级完成 |
| T02 失败分类 | -4/20 映射、probe_worker_failed/disconnect_failed/invalid_probe_result 分类既有单测覆盖；连接类错误码语义以 SDK 头文件核对。夹具级完成 |
| T03 时间线与空闲对照 | 未执行：G1 探测失败，通道处于永久失效态，5 分钟间隔探测无意义；时间线取证已以只读方式完成（上表） |
| T04 修复或规避验证 | 未执行：需通道恢复（环境处置）后进行 |
| T05 正常建模闭环 | 未执行：同上 |
| T06 异常与保护回归 | 全量单元（含 reconciliation/recovery 21+ 例）通过，未改保护逻辑 |
| T07 稳定通道下协议对照 | 未执行：需稳定通道 |
| T08 原 M2 交接 | 未执行：M2 保持 recovery_pending 受保护状态，未做任何处置 |

## 环境处置建议（需用户明确决定，本轮未执行）

1. 关闭当前批次 C Creo（仅含预探测附带模型 `ai_part_588d955f8935`，无用户数据）；
2. 确认 nmsd.exe（PID 25996）随之退出；若残留，结束该遗留 nmsd（属结束进程操作，需用户同意）；
3. 清理不再使用的 MCP 客户端会话残留 server.py 实例（8 对，属各客户端宿主管理，建议通过关闭对应客户端会话释放）；
4. 重启 Creo（手动或经协调器 retry），新批次将启动自己的 nmsd；
5. 之后按 DEV-036 T03（空闲对照+间隔探测≥5 分钟）、T04、T05 复测并在 WorkBuddy 生成黑盒对照。

## 未测范围

40 秒窗口的精确机理（窗口已过去且当前为永久失效态，无法受控复现）；nmsd 内部状态（黑盒）；批次 C 期间 Creo 侧无警告对话框的确认仅来自窗口枚举与用户先前陈述；T03/T04/T05/T07/T08 全部待环境处置后执行；新增字段的 WorkBuddy 黑盒验证待服务重启后进行。

## 第二轮：环境处置与复测（2026-10-17，用户授权「直接操作掉」）

### 处置（用户先手动关闭 Creo）

22:0x（北京时间）：核实 parametric 18720/xtop 24056/pro_comm_msg 已随用户关闭退出。开发者经授权执行：`Stop-Process` 结束遗留 nmsd.exe（PID 25996，06:03 UTC 批次遗留）；结束 codex.exe 名下 4 对残留 server.py（PID 12572/17324/26532/17036/27044/16504/4036/9400）；保留当前 ZCode 会话正在使用的 1 对（7716/24336，旧代码实例）。处置后无任何 Creo 侧进程。

### 重启与新批次身份

本地 `CreoStartup.start(retry=True)`（与 MCP `creo_startup_status(retry=true)` 同路径）：14:12:14 UTC `starting`（launch_attempt=9），**14:12:27 UTC ready**（连接验证通过，release 44）。新批次：parametric PID 4156、xtop PID 14912、pro_comm_msg PID 4048（xtop 子进程）、**nmsd PID 22452——随新批次启动的全新名字服务**（遗留 nmsd 已不在）。

### T03 时间线与空闲对照 — 通过

- 前置空闲对照 60 秒（14:12:56–14:13:56 UTC，无任何 Toolkit 调用）。
- 间隔探测 38 次（10 秒周期，`bridge.session_status(2)`，与 MCP `creo_session_status` 同路径）：14:13:56–14:21:24 UTC 跨度约 7.5 分钟，**38/38 全部 connected=true、toolkit_code=0、exit 0**，单次探测耗时约 4.9 秒（2 秒 connect + 2 秒 disconnect + 进程开销）。第 30 次后插入 60 秒空闲对照（14:18:51–14:19:56），空闲后终探 connected=true。全程无任何失效、无约 40 秒模式。原始记录 `build/dev036_t03_timeline.json`、`build/dev036_t03_extra.json`。
- T04 同批满足：≥5 分钟串行探测 + ≥60 秒空闲后探测全部成功；窗口内 xtop GUI 保持可操作（末次 `IsHungAppWindow=false`）。该窗口只覆盖本次环境。

### T05 正常建模闭环 — 通过

模型 `dev036_t05_probe`（model_id `c27ccf7ffe614e9fbd22baabda323ca4`）：新建（草图矩形+拉伸 8mm）作业 succeeded、revision 0→1、`saved_file_reloaded_and_verified=true`；编辑（顶面圆草图画孔 `through_all` cut）作业 succeeded、revision 1→2、`saved_file_reloaded_and_verified=true`；两作业均仅轮询原 job_id 到终态。保存文件 `…\output\dev036_t05_probe.prt.3`；**体积 4573.805328941535 mm³ 与理论值（30×20×8−π×3²×8）精确一致**；任务后空闲 60 秒再探测 connected=true（14:24:03 UTC）；GUI 窗口标题更新为 `DEV036_T05_PROBE (启用的)` 且 hung=false。原始记录 `build/dev036_t05_record.json`。

备注（如实）：本会话 MCP 客户端层对 `creo_execute_plan` 传参做 union 校验失败（两次重试均未到达服务，客户端限制），T05 改用与 server.py 工具相同的 `generic_bridge.submit`/`bridge.get_job` 本地路径执行；此差异不改变建模闭环的验收含义，WorkBuddy 黑盒在服务重启后另行覆盖。

### 复测结论

- BUG-056「修复/规避」验收判据满足：按指引处置（清理跨批次遗留 nmsd + 重启 Creo）后，连续 ≥5 分钟探测无掉线且一次完整建模任务（新建→编辑→保存重载→空闲→探测）全程不掉线。
- 「复现」判据按另一分支闭环：原现象不可再复现，且当时环境的唯一性说明已给出——失效发生在「遗留 nmsd（批次 B）+ 新 Creo（批次 C）」的跨批次组合下，清理遗留 nmsd 后同机同版本不复现。
- 服务侧无行为变更（本轮修复仅为只读可观测性字段），unknown 作业处置契约未动；M2 保持 recovery_pending。
- 残余：nmsd 内部触发器仍为黑盒假设；T07（稳定通道空值协议对照）与 T08（M2 受保护交接）待 WorkBuddy/发起者明确决定后执行；新增 `creo_process_snapshot` 字段的黑盒验证待 MCP 服务重启。
