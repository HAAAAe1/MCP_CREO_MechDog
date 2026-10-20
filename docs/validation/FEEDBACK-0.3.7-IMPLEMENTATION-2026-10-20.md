# 0.3.7 剩余反馈：实现与验证记录

日期：2026-10-20（Asia/Shanghai）。结论：本批离线实现和检查通过，原生验收被会话连接与桌面访问问题阻断，计划尚未全部完成。未合入 main、未发布新版本。

## 基线与证据范围

按用户要求先 fast-forward 拉取 main 至 `cfcea22284f5eb3735029b1db0e4495a5e7af09f`（0.4.2），随后在 `codex/bug-057-feedback-037` 实施。独立格式整理提交为 `f43de43f682ba7541c9f4db1e499a61178ea1402`（仅 advanced.cpp 格式）；下列功能验证时工作区为 dirty，提交号不单独代表受测功能源码。

环境：Windows 11 x64 / 26100、Python 3.12.14、Creo 12.4.0.0、匹配 Toolkit SDK、MSVC x64。服务源码版本保留 0.4.2，工具数不变。所有开发者 stdio 测试显式运行 E 盘仓库 server.py；本机联调目标仍为 MCP_CREO_MechDog_dev。

两份此前未收录的报告按原字节归档，SHA256 与[清单](feedback-0.3.7-remaining-2026-10-20/manifest.json)一致。用户确认原始诊断 JSON、失败作业日志和 Creo 9 完整请求由其他用户持有，本机没有；报告中的统计为外部自述，不冒充本机复现。已有 Creo 13 与接管报告保持原位置和原字节。

## 本批实现

| 条目 | 变更 | 仍未证明的范围 |
| --- | --- | --- |
| BUG-057 | 主通道锁单次 CreateFileW OPEN_ALWAYS、共享读写且不共享删除，再转交现有字节锁。文件不截断、不预写、不重试、不排队；真实打开错误保留原始 Windows 错误。 | 外部 Windows 10 / Python 3.13 首建失败的根因及修复后复验。 |
| BUG-074 | 新增历史 owner 停止证明：仅缺失身份且所有控制记录和时间早于独立交叉核验的 Windows 启动时刻时可用；绑定令牌，准入和原生执行前后再查。完整活动/权限未知 owner 不走兜底。 | 真实跨系统启动的历史作业四动作、原生续作和 WorkBuddy 验收。 |
| BUG-058 | 状态接口与等待连接阶段附当前桌面窗口观测及对应指引。隐藏启动器与可见挂起窗口分开，访问失败保留 unknown，不推断进程死亡。 | 外部无主窗口 -11 的实际根因和处置复验；本机新发生的连接异常。 |
| FEAT-030 | seed_build_version 无来源为 null；available 明确只代表文件/哈希。真实种子加载记录绑定 SHA256、release、会话和作业，查询只返回有界历史；诊断落盘失败不改变建模终态。 | 当前版本真实加载/建模记录、真实 -16 失败；Creo 9 兼容修复仍归 BUG-034。 |
| BUG-036 | 本机 SDK 明确 PositionGet 返回约束/运动前的初始放置。公开 transform 改取组件路径到装配的当前变换，另保留 initial_transform 与来源标识；旧检查点沿用原矩阵含义，新检查点核验实际变换。没有盲目追加再生调用。 | 实际约束后的面位置/法向、变换、保存重载及原 Creo 9 失败输入。 |
| FEAT-023 | 拉取的 0.4.2 已交付 compact 默认与分节游标，复用现状。 | 其余组件、日志等体积议题仍归原卡，本批不扩展。 |

源码身份清单覆盖新增包模块及实际修改的原生文件。恢复失败可选字段的含义已补 MODEL_RECOVERY 与公开工具说明；没有新增生产故障注入开关。

## 开发者检查

| 命令 / 证据 | 本次结果 |
| --- | --- |
| 修改前两项原失败单测、`tools/reproduce_toolkit_lock.py --iterations 200` | 本机原失败未复现；absent、empty、one_byte 各 200 轮均 acquired + lock_busy，无打开错误。原报告失败事实保留。 |
| `tools/dev_check.py --work-item BUG-057-BUG-074-BUG-036-FEAT-030` | 455 项单元，0 失败、0 错误；增量语言检查通过，未重建风格基线。不是存量严格风格清零，也不是原生验收。 |
| BUG-057 新回归 | 三种锁文件状态各 200 轮真实双线程竞争；跨进程 busy、释放重入、持句柄删除/替换拒绝；真实打开错误不伪装 busy。 |
| BUG-074 新回归 | 10 项隔离测试：四动作 owner 门槛、同启动/不可核验拒绝、活动/权限未知身份、缺失/时间异常、文件变化过期、幂等审计、准入后变化 before_native 拒绝及四动作登记。模拟原生结果不算实机通过。 |
| FEAT-030 / BUG-058 新回归 | 种子 6 项、窗口观测 3 项通过；原会话快照 7 项及 capabilities/公开恢复夹具回归通过。隔离 stdio 夹具禁止 WMI/原生子进程，启动时间使用显式未知夹具。 |
| `bridge.py build` | 修改后原生执行器在本机匹配 SDK 编译通过。 |
| `tools/test_component_transform.py` | 7 项真实 SDK 声明契约检查通过：路径/方向/API 错误及新旧检查点选择。API 返回由替身提供，未连接 Creo、不证明几何求解或保存重载。 |

全量检查记录：`build/feedback037-dev-check-final.txt`、`build/development_check.json`、`build/unit_test_report.json`。检查开始于 15:37:28（北京时间），受测 HEAD `f43de43f682ba7541c9f4db1e499a61178ea1402`、dirty=true，开发检查源码指纹 `4f732d5dbcf20f4beef42823d813e348ba52132584b524084cdb1ba7461c68d6`。随后仅修正尚未运行的原生测试驱动输入 references 和其源码指纹记录；该驱动不计入上述原生通过结论。

本批原生源码 SHA256（与构建后代码一致，后续没有原生变更）：

| 文件 | SHA256 |
| --- | --- |
| native/component_transform.h | `7d4136dc8ad1e8eb3d0514c9479de41c290de4e0cad568ef1cfa29a6e2604ed8` |
| native/advanced.cpp | `4b8aa906450ac123d5cb66b82fcad5c71de41d6747adb46e7fc8401197f37aef` |
| native/generic.cpp | `c8e55fc3888816fe2bccdd4f49de7196a749b2be2e43328bac404ad7e5184954` |
| native/loft_seed.cpp | `0f989b7c61343bee21b209def7dd79aff73643e07a9634421842673e1db96fae` |

## 实机会话尝试与停止点

未执行故障注入，未清除任何真实 unknown/recovery_pending、模型或原作业。所有失败尝试在就绪门槛前结束，建模 jobs 数量均为 0。

1. 用户先确认已关闭 Creo 等软件。核对无 Creo 后正常启动，连接持续返回 -4；空会话 xtop PID 7932 / launcher 21748，旧 nmsd PID 17948 跨批次存在。记录 `build/feedback037-smoke.json`。
2. 用户明确允许核对后清理上述三个进程并重启。重新匹配映像路径和 UTC 创建时间，持有已核实进程对象后结束且仅结束这三项。保留所有作业/模型/保护记录。
3. 15:33 重启：launcher 23988、xtop 25076、新 nmsd 16036；仍返回 -4 并到达启动预算。因此“只有遗留 nmsd 导致本轮失败”不能成立。xtop 可见窗口未观测挂起，但 UI 显示另有“检索”窗口，不能确认会话可操作。记录 `build/feedback037-smoke-after-cleanup.json`。
4. 桌面控制截图全黑，激活窗口连续报 `GetCursorPos` 拒绝访问（0x80070005）。按 computer-use 工作流刷新并重新绑定窗口后仍失败，停止输入；未猜测坐标关闭对话框。
5. 用户手动关闭 Creo 并重启 Codex，要求再试。15:43 确认无 xtop/launcher，nmsd 16036 仍存在；正常启动新 launcher 16712 / xtop 25284。一次就绪探测在 9 秒预算内超时，未提交建模；只停止自身探测助手，保留 Creo。新窗口绑定后桌面控制仍拒绝访问。记录 `build/feedback037-smoke-after-codex-restart.json`。
6. 只读核对显示当前 RDP 会话 Active，Codex、Creo、nmsd 均在 Session 1。不能据此认定跨 Windows 会话运行；也不能仅凭远程桌面解释 Toolkit -4 或超时。GetCursorPos 要求当前输入桌面及相应访问权限，见[微软接口说明](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getcursorpos)。远程断开/锁屏/桌面切换为待核对条件，不作为已证根因。下一步使用保持连接解锁的桌面，或本地登录做同环境对照，先确认 Creo 可手动操作，再恢复实机验收。

这些现象与外部无主窗口 -11、本机此前 Dashboard 模态 -11 分开记录，不据本轮失败重开已关闭条目或套用旧根因。

## 剩余工作与入口

已准备 `python -m tools.test_feedback037_modeling`：串行验证装配旧位姿到三平面约束、两截面 straight/smooth 种子实际加载、圆角/倒角独立及计划别名、冲突拒绝、尺寸/体积/revision 与重载。驱动只观察已接受任务，unknown 即停止后续写入；目前未运行成功，不能记作原生证据。

会话恢复后还需运行适用的 `tools/test_general.py`、`python -m tools.test_p1_modeling --cases ribs`，补 BUG-017 当前环境对照；缺失的 Creo 9 完整输入和原环境测试仍保持开放。FEAT-018 四动作真实恢复矩阵、FEAT-042 关闭原件后确认、FEAT-043/BUG-072 单位与枚举边界、FEAT-029 回调 ready/直接放样/升级回退生命周期及真正并发验收均未由本轮完成。不能靠源码或隔离夹具宣布通过。

公开 WorkBuddy 提示词已保存为 [WORKBUDDY_037_REMAINING](../WORKBUDDY_037_REMAINING.md)，仅使用公开 MCP，不读源码或运行开发脚本。本轮未执行 WorkBuddy。原计划和执行状态见[计划](../development/0.3.7-feedback-remaining-plan-2026-10-20.md)。

## 继续执行：不完整进程身份与公开只读复验

用户要求继续计划后，在 `d4097be` 上复核并补齐 BUG-074 的遗漏：只有 PID、没有创建时间的 runner/native_owner，以及仅含 native_pid 的历史检查点，首批实现仍不允许使用跨启动停止证明。两项新增隔离用例在修改前均实际失败，记录 `build/feedback037-pid-only-before.txt`；修复后与相关恢复回归共 53 项通过，记录 `build/feedback037-partial-identity-after.txt`。

兜底现覆盖字段缺失的不完整身份，但完整活动/权限未知身份继续拒绝；同次启动、不可核验启动时间、文件变化仍拒绝。另补格式错误拒绝：非对象身份、布尔 PID、字符串创建时间不能被误判为 PID 已复用，也不能获得跨启动兜底。没有放宽四动作其他条件，没有改真实作业/模型。

通过当前已连接的 MCP_CREO_MechDog_dev 完成开发者公开接口只读复验：`creo_list_seeds` 与全部九次 `creo_validate_seed` 均返回哈希有效、seed_build_version=null、native_compatibility.status=not_verified_for_current_session、observations=[]。运行路径公开核实为 E 盘 Python、server、包和数据根。记录 `build/feedback037-public-readonly-followup.json`；这证明元数据公开语义，不证明种子能在当前会话加载，也不是 WorkBuddy 验收。runtime 页属于冻结快照，不用其旧的 source_changed_since_startup 值证明之后的源码改动已加载。

15:55:54 的一次只读 `creo_session_status` 仍返回 probe_timeout（9 秒）；可见 xtop 窗口未观测挂起。此次没有启动或结束 Creo，没有建模/恢复提交，也没有继续轮询式重连。原生验收仍待可操作会话；最新 Python 变更在正式实测前须重启开发 MCP 连接器并核对源码身份。

同时补齐尚未执行的原生驱动：圆角/倒角分别覆盖独立工具、计划 size、计划别名三个入口；冲突与错配别名采用新的未使用标签，必须返回对应错误文字，随后检查 revision/体积不变，避免仅因标签重复而误记为参数保护通过。该驱动仍不计作实际原生通过。

续做全量 `tools/dev_check.py --work-item BUG-074-partial-identities` 通过：458 项单元，0 失败、0 错误，增量检查通过。开始于 15:59:30（北京时间），HEAD `d4097be3abbdb4c71aef4278c9b67f58c1b0b953`、dirty=true，检查源码指纹 `7da46b298319f13804e47e08e24b205228e6d53e31ab474c6c22227a6cc78cfe`，记录 `build/feedback037-partial-identity-dev-check.txt`。该次已覆盖新的生产恢复保护；原生驱动之后的补充另经 Ruff 检查通过，没有用单元结果宣称其原生场景已执行。当前 build/development_check.json 与 unit_test_report.json 已被本次结果更新；首轮455项的原记录仍保留在 feedback037-dev-check-final.txt。

本次保护代码 SHA256：reconciliation.py = `e0272ae592d2ec2ebeb82e97aa7451469c492a6de6afe48ca8e9f99e99612ebe`，test_legacy_recovery.py = `77de9cb09b00bcab3428938d4439aec28237cee9233c2b0b6bcaa513f0468b96`。原生文件没有变化；本次保护修改后未重新构建或连接 Toolkit。

## 继续执行：会话恢复与原生验收（2026-10-20 16:10 起）

16:10:45（北京时间）`creo_session_status` 经当前 dev 连接器返回 connected=true、toolkit_code=0、startup state=ready；xtop 25284 可见窗口无挂起。本轮没有启动、结束或重配任何 Creo 进程，没有清除任何保护记录。当前 MCP_CREO_MechDog_dev 连接器进程于 16:09:51 启动，晚于 `e16ad69`（16:04:34）提交，最新 BUG-074 保护源码已随连接器加载；15:40/15:55/15:57 启动的三个空闲 server 实例仍在运行但未持有通道，未触碰。

以下三项原生驱动全部经 stdio 自起新 server 实例执行（加载磁盘最新源码，commit `e16ad69`、dirty 仅未跟踪文件），串行独占 Toolkit 通道：

| 驱动 | 结果 | 证据 |
| --- | --- | --- |
| `python -m tools.test_feedback037_modeling` | success=true，26 个作业调用全部通过 | `build/feedback037-modeling.json`、`build/feedback037-modeling-run.log` |
| `python tools/test_general.py` | GENERAL_CORE_SUCCESS=1 | `build/feedback037-general-run.log` |
| `python -m tools.test_p1_modeling --cases ribs` | success=true，8 个作业全部通过 | `build/p1_modeling.json`、`build/feedback037-ribs-run.log` |

第一项驱动覆盖内容：

- BUG-036：装配链 component_source → assembly → initial_placement（`(-30,20,0)+Z30°`）→ constraints_replace_fixed_pose（三基准面 align）→ assembly_reload。约束替换固定位姿后公开 transform 收敛到单位矩阵、`transform_source=component_to_assembly`、非 underconstrained 且非 packaged；refresh 重载后矩阵一致，revision 递增符合预期。作业 `ba074d7dec71418bb1cb3deebfef573e`。
- FEAT-030：seed_straight / seed_smooth 两截面种子在当前会话实际加载，`seed_load_evidence.status=loaded`、evidence_persisted、creo_release_numeric=44；`creo_validate_seed` 的 observations 绑定对应 job_id，straight 体积按 4900π/3 断言通过。作业 `d52455af61754f8cb9155cc988aeadca`、`7e2c027314b54508bcf59e8fb7461ab1`。
- BUG-019 / DEV-042：round 与 chamfer 各覆盖独立工具、计划 `size`、计划别名三个入口共六组；每次 `operations[].size` 与 compact 载荷回显一致、特征实际尺寸等于输入值；`size` 与别名同时给出返回 "not both"、错配别名返回 "does not accept"；冲突被拒后 revision 与体积不变。

说明：该驱动首次前台运行因 10 分钟 shell 上限在第十一个调用后被截断（此前作业本身全部成功，例如 `1c3784d4933443ff9c8e6970dccb0ef3` 保存重载验证通过）；结论以完整后台重跑的报告为准。

BUG-017 本机对照：L 形基座体积 54000 mm³，加筋后 55250 mm³，flip 取 False/True（对称侧）及 False（正向、负向材料侧）四种组合全部成功，`saved_file_reloaded_and_verified=true`。当前 Creo 12.4 环境下筋特征、flip、材料侧与保存重载正常；原 Creo 9 失败输入仍由其他用户持有，该环境范围保持开放。

仍未完成的开放项不变：FEAT-018 四动作真实恢复矩阵（涉及受控制造 unknown 状态，受 BUG-001 故障注入限制暂不实施）、FEAT-042 关闭原件后确认、FEAT-043 / BUG-072 单位与枚举边界、FEAT-029 回调生命周期、真实并发、WorkBuddy 黑盒（[提示词](../WORKBUDDY_037_REMAINING.md)）以及 Creo 9 / 外部 Windows 10 环境复验。

## 继续执行：真实并发验收与两次保护性事件（2026-10-20 16:28–16:40）

真实并发验收（计划第五节第4条）：`build/feedback037_concurrency_check.py` 起两个 stdio server 实例，作业 A（`wb_conc2_a`）进入 running 后作业 B（`wb_conc2_b`）才提交。结果（`build/feedback037-concurrency.json`）：A succeeded 且 `saved_file_reloaded_and_verified=true`；B 提交立即 `isError=true`、`status="busy"`、`blocking_job_id=bd9ca58774c643ba8f6469d83d9c274d`（即 A）、`blocking_operation="execute_plan"`，不排队、不自动重试，双方连接保持到终态，无新增孤儿。此为通道级真实并发；接管/同模型并发编辑不在本轮范围。

首版脚本（提交后立即关闭连接）意外留下两个 queued/waiting_for_channel 作业（`ef52edc9bfa54f33a69fe48778c44f01`、`63e6b4f77c674b64859d4644aaca700e`，模型 bd429fcc/b52c2555，wb_conc_a/b，revision 0、无保存文件）。reconcile inspect 均返回四动作全部拒绝：runner recorded alive=true 为登记快照、实测 observed alive=false 但带 windows_error=87，worker 身份不可用（"Native owner identity is unavailable"），总拒绝理由 "Job timestamps do not predate the verified Windows boot"——同次启动内创建的作业不满足跨启动停止证明，guidance 要求操作员控制的重启后再 inspect。这是 BUG-074/FEAT-018 保护拒绝路径的一次真实（意外触发）案例，行为符合设计；两个模型保持受保护状态留待下次重启后处理，未绕过、未清除。

期间 startup 一度进入 building_worker（约 16:29–16:31），未提交建模、未干预进程，约 100 秒后自动回到 ready（"Toolkit connection verified"），随后并发验收即在就绪通道上完成。并发验收后通道保持健康，后续未再触发 building_worker。

## 继续执行：重启后的接管链路与桌面访问边界（2026-10-20 16:36–16:58）

用户重启 Creo 后（parametric 19212 / xtop 8632，创建于 16:36:03–04），会话于 16:36:36 验证 ready，`creo_process_snapshot` 显示 xtop 可见窗口无挂起。这是 FEAT-029「正常重启后恢复 ready」的生命周期一环，已由公开接口观察到。

**孤儿模型重启后仍被拒绝**：对 bd429fcc（wb_conc_a）重新 inspect，四种恢复动作继续全部拒绝，理由仍为 "Job timestamps do not predate the verified Windows boot"，worker 身份不可用，guidance 要求操作员控制的重启。因此 BUG-074 的跨启动停止证明以 **Windows 启动** 为基准而非 Creo 启动；只重启 Creo 不构成新证据，工具也未放宽。两个孤儿模型继续受保护，未绕过、未清除。

**接管链路真实验证（FEAT-042 / FEAT-018）**：

| 步骤 | 结果 | 证据 |
| --- | --- | --- |
| `creo_open_file` 打开受管输出 prt | 打开并显示成功，源文件哈希未变 | job 2c88fe21db5d4223a02e432aae7ef081 |
| 对受管输出执行 adopt inspect | 正确拒绝，`reason_code=managed_output`，指引改用已有 model_id | 边界正确 |
| `creo_open_file` 打开外部文件 examples/wb_unsaved_03.prt.1 | 成功显示，identity 前后一致（sha256 f780d629…） | job 345f61c77f5840cb80c4a6292cf4c778 |
| adopt inspect（外部文件） | available=true，6000 mm³ 健康毫米件，证据令牌发放 | model f81404abf33e486784a52985a5d6ab98 |
| adopt apply | adoption_committed，revision 1，`saved_file_reloaded_and_verified=true`，原件未被修改 | job 6bc540234a314ac0b4be7627f1c0103e |
| 误用 prepare 入口（有文件来源） | 原生明确拒绝 "prepare requires a never-saved model; use inspect/apply for a file source"，job 转 unknown_outcome、保护保留 | job 4e9d0cc2a88545a09f0a6ec6bb31bd4c |
| 对上述保护模型 reconcile inspect | worker 身份完整（pid 20456 + 会话指纹）且实测已停，`abandon_new` 判定可用 | model 03d8b89a3f07c94aa6035d50ce38f3f4 |
| reconcile apply abandon_new | reconciliation_committed，原作业历史保留，revision 0 | job b22b6832f86443549882b7f2a84da578 |

这组对比澄清了恢复准入的两种来源：派发过原生 worker 的失败作业可用 worker 停止证据收尾（本批首个真实 abandon_new 正例）；从未派发的历史作业只能靠跨 Windows 启动证明。界面文案也准确区分了 prepare 与 inspect/apply 的适用来源。

**桌面访问边界（关闭原件未执行）**：用户要求直接控制电脑关闭原件窗口。经电脑控制插件核对，本会话未启用 Computer Use（返回 "Computer Use is unavailable for this node_repl session"）。改用窗口级 Win32 观测：Creo 仅有 1 个可见顶层窗口（标题 WB_CLOSE_ORIG），26 个子窗口全部不可见，界面由主窗口自绘；`PrintWindow` 可正常取到完整窗口内容（已核对功能区、模型树为 WB_CLOSE_ORIG.PRT）。原件 WB_UNSAVED_03 因此没有独立窗口，属于会话中未显示模型，正确操作路径是 文件 → 管理会话 → 拭除未显示的。

输入通道实测不可用：进程位于 Default 桌面（非锁屏的 Winlogon 桌面），但 `GetForegroundWindow()` 返回 0，`SetForegroundWindow` 返回 False，`SendInput` 返回 0 且 `GetLastError`=5（ERROR_ACCESS_DENIED），屏幕捕获 `CopyFromScreen` 报"句柄无效"（首次截图尚可，之后失败）。这些现象与先前记录的 `GetCursorPos` 0x80070005 一致，指向 RDP 客户端断开或最小化后会话失去输入焦点，而非 Creo 故障。为确保不产生未验证的操作痕迹，未继续尝试合成输入，也未用其他 UI 自动化技术替代；「关闭原件」保持未执行。

恢复条件：操作员重新连接 RDP 并保持窗口在前台可见（不最小化、不锁定），或改用物理控制台登录，使 `GetForegroundWindow()` 能返回交互窗口。届时再执行拭除原件并继续验证副本续作。

**RDP 重连后的输入复核（17:0x）**：操作员重新连接远程桌面后，桌面输入部分恢复——`GetForegroundWindow()` 返回有效窗口（先 QQ、激活后 919870），`SendInput` 返回 1，`SetCursorPos`+`GetCursorPos` 回读一致（45,98），全屏 `CopyFromScreen` 恢复正常。Creo 会话未重启（xtop 8632 / parametric 19212 仍为 16:36 启动）。

随后穷举注入路径操作 Creo，全部无效果：`SendInput` 左键按下/抬起（含 90ms 按住间隔）点击"文件"选项卡、`mouse_event` 旧接口同样点击、`PostMessage` WM_MOUSEMOVE/WM_LBUTTONDOWN/WM_LBUTTONUP、键盘 `SendInput` 的 Ctrl+O 与 Alt、点击标题栏后再点"文件"、点击模型树 `WB_CLOSE_ORIG.PRT` 行。界面无任何变化（无 backstage 菜单、无打开对话框、无节点高亮）。

排除项：`IsHungAppWindow(main)=False`、`SendMessageTimeout(WM_NULL)` 立即返回（消息循环正常）、窗口可见且完整渲染（PrintWindow 与屏幕捕获一致）、ZCode 与 xtop/parametric 同为 session 1、屏幕与窗口坐标链路逐项核对一致。`parametric.exe` 有两个隐藏窗口 `ProeMainWinClass`/`Application` 处于 hung，但均为不可见窗口，不构成输入拦截。

结论：该环境下 Creo 不接收自动化注入的鼠标与键盘事件（自绘 UI 过滤注入输入，或经 RDP 的注入事件未被其输入循环处理）。这不是坐标、焦点或窗口症状问题，已排除操作失误。因此"关闭原件"仍须操作员在 Creo 界面手动完成；本批不采用 trail 回放、修改原生代码或其它绕过 UI 的手段，以免在验收流程中引入未评审的实现变更。手动步骤：文件 → 管理会话 → 拭除未显示的 → 选中 `WB_UNSAVED_03` → 确定；随后工具 → 辅助应用程序 → 选中 blend 条目 → 启动。

## FEAT-042 关闭原件后副本续作（2026-10-20 17:50，操作员执行 UI 步骤）

操作员按指引在 Creo 界面完成"文件 → 管理会话 → 拭除未显示的 → 选中 WB_UNSAVED_03"。工具侧核对结果：

| 检查项 | 结果 |
| --- | --- |
| `creo_list_session_models` | 会话仅剩 `WB_CLOSE_ORIG`（is_current=true、modified=false、has_saved_origin=true），原件 `WB_UNSAVED_03` 已不在会话中，`complete=true` |
| 副本续作（`creo_execute_plan`，expected_revision=1） | 在 z=10 顶面新增 10×10 矩形草图 + 5mm 拉伸凸台，作业 `ca35c92d0d4d4f8296f979be26862dee` 终态 succeeded/verified |
| 几何与版本 | 体积 6000 → 6500 mm³（增量 500 mm³ 与 10×10×5 几何一致）；revision 1 → 2；`saved_file_reloaded_and_verified=true` |
| 受管产物 | `models/f81404ab…/output/wb_close_orig.prt.1`（接管时 94345 B）新增 `.prt.2`（114747 B） |
| 原件文件完整性 | `examples/wb_unsaved_03.prt.1` 仍为 92659 B，SHA256 `f780d6296330d24dec80679f37be7aa835c33e796580126f612347c9bc6ca713…` 与接管前完全一致，未被修改 |

结论：原件从会话移除后，受管副本仍可正常编辑、保存并重载验证，原件文件不受影响。FEAT-042 的"关闭原件后确认"专项由此闭环；其余未测范围（真实再生失败、钣金专有语义等）保持原状。

**同轮发现（待跟进）**：`creo_callback_status` 在 17:50 与 17:51 两次实时探针均返回 `readiness=not_loaded`、`reason=recorded_application_not_active`。注册文件状态正常（`build/blend_callback_protk.dat` 含 `name MCP_CREO_MechDog Blend 2a5f6d01`、`delay_start true`；`build/blend_callback.config.pro` 含 `protkdat` 指向该文件），但 Creo 启动命令行（xtop/parametric）未携带 `-pro` 参数，仓库根目录与 PTC 用户目录下也未发现含 `protkdat` 的 config.pro。因此 FEAT-029 的"加载后 ready / 直接放样"仍需先确认辅助应用程序列表是否列出该条目；若列表为空，需把 `protkdat` 配置进 Creo 实际读取的 config.pro 后再注册。本轮不改动 Creo 启动配置。

**同轮工具侧异常（已定性、非产品缺陷）**：经 ZCode 连接器直接调用 `creo_execute_plan` 时，两次均返回 `InputValidationError: invalid_union (path=operations[0], [1])`；改用 stdio 直连同一 `server.py` 后，同一份 operations 参数在 worker 就绪后正常受理并成功执行。差异来自连接器侧的工具描述缓存与实际 schema 不一致，建模能力本身正常。后续实机验收优先用 stdio 直连驱动，或在连接器重载工具定义后再用界面工具。

**回调未加载的根因（17:53 定位）**：Creo 的实际工作目录为 `build/creo_session`（依据该目录下 `trail.txt.39`）。该目录原本**没有 config.pro**，而 Creo 启动命令行（xtop/parametric）也未携带 `-pro` 参数，因此 `build/blend_callback.config.pro` 从未被读取，`protkdat` 从未注册——辅助应用程序列表中没有 `MCP_CREO_MechDog Blend 2a5f6d01` 条目，`delay_start true` 的手动启动自然无从执行。这也与 `creo_callback_status` 连续返回 `recorded_application_not_active` 一致，不是探针或部署产物问题（`artifact_status=prepared`、loader/callback 哈希均正常）。

已创建 `build/creo_session/config.pro`，内容为 `protkdat E:\Projects\MCP_CREO_MechDog\build\blend_callback_protk.dat`。该路径属于 `build/`（`.gitignore` 第 5 行忽略），是本机运行配置，不进源码或发布附件。此后 Creo 正常重启会读出该条目，但仍需在辅助应用程序中手动启动（`delay_start true`），这正是 FEAT-029 记录的"手动首次设置"路径。当前会话不重启时，可在辅助应用程序对话框用"注册"直接选择该 `protk.dat` 立即加载。

## FEAT-029 回调就绪与直接放样（2026-10-20 18:07，操作员完成注册启动）

操作员按方式 A 在辅助应用程序中注册 `build/blend_callback_protk.dat` 并启动。工具侧核对：

| 检查项 | 结果 |
| --- | --- |
| `creo_callback_status` | `readiness=ready`、`reason=live_identity_verified`；`loaded.process_id=8632`（当前 xtop）、`command=MechDogBlend_71b1093a77c51aa09cbda000_2a5f6d01`、`dll_sha256=71b1093a…`、`initialize_code=0`、`terminated=false`、`active_request=false` |
| 直接放样前置 | 在受管副本上新建 `sk_a`（XY offset=15、圆心 (15,10)、R10）与 `sk_b`（XY offset=35、R6），两作业均 succeeded，revision 2→3→4 |
| `creo_loft`（sections=sk_a,sk_b、straight） | 作业 `bc0dde188ca54eed994f20706f99e2b5` 终态 succeeded/verified，revision 4→5，`saved_file_reloaded_and_verified=true` |
| 几何核对 | 体积 6500 → 10605.0144 mm³，增量 4105.0144 mm³；圆台解析值 π×20/3×(10²+10×6+6²)=4105.0144 mm³，与实测完全一致 |

**参数边界（正确拒绝）**：首次尝试带 `new_body=true` 时，工具返回 "Direct Blend supports solid add into the default body only; cut, surface and new_body are not accepted"，未产生作业、未改动模型。这属于使用方式错误而非能力缺陷，去掉该参数后放样即成功。

**worker 生命周期观察**：stdio 直连每启动一个新 server 实例都会经历一次 `building_worker`（本次 18:07 与 18:08 各一次），数秒到百余秒内自动转 `ready`，期间提交被明确拒绝且未排队（"No modeling job was queued"）。这与既有设计一致，不构成卡死。

FEAT-029 已验收：加载后 ready、直接放样及保存重载。尚未验收：正常重启后条目与 ready 的持续性（需重启 Creo 并确认 `build/creo_session/config.pro` 生效）、兼容升级、回退及目录并存。

## FEAT-029 正常重启验证（2026-10-20 18:16–18:18）

**关闭过程**：17:16 先确认会话唯一模型 `WB_CLOSE_ORIG` 为 `modified=false`（已存 `wb_close_orig.prt.5`），向主窗口发送 `WM_CLOSE`。Creo 正确弹出"确认"对话框（"Creo Parametric 将终止，确定要退出？"），证明主窗口接受系统消息；但该对话框完全自绘、无子控件，`WM_COMMAND`（IDYES/IDOK）与坐标点击均无效——与主窗口一致的"注入输入被忽略"特性。因模型已保存且操作员已授权重启，18:17 强制结束 xtop 8632 与 parametric 19212（保留 nmsd 16036 常驻服务）。

**重启与连接**：MCP 协调器自动启动 Creo（`launched_by_coordinator=true`，`launch_attempt=19`），新进程 parametric 21184 / xtop 22648（18:17:34/35），18:17:49 `creo_startup_status` 返回 `state=ready`、`connected=true`。这是 FEAT-029「正常重启后恢复」的首个本机正向证据。

**工作目录与配置**：新 `build/creo_session/trail.txt.40`（PID 22648）确认工作目录仍为 `build/creo_session`，`config.pro`（`protkdat …blend_callback_protk.dat`）在位。trail 中出现 `~ Activate pse_abnorm_exit_dlg psh_continue`，说明强制结束被 Creo 识别为异常退出并自动继续，未阻塞启动。trail 无 blend 加载记录，符合 `delay_start true` 不写启动轨迹的预期。

**回调状态**：重启后 `creo_callback_status` 为 `readiness=not_loaded`、`registration_status=unknown`、`reason=recorded_application_not_active`。按 FEAT-029 既有语义，`unknown` 表示注册状态无法由工具侧确认，`not_loaded` 在 `delay_start` 下是预期结果（应用存在于列表但未启动）。因此 config.pro 是否被 Creo 读取，仍需操作员在辅助应用程序列表中目视确认条目 `MCP_CREO_MechDog Blend 2a5f6d01` 是否存在；存在即可确认持久化注册生效，点击启动后应转 `ready`。

## FEAT-029 重启后持久化与建模链路（2026-10-20 18:37 收尾）

操作员确认重启后的辅助应用程序列表中**存在** `MCP_CREO_MechDog Blend 2a5f6d01` 并点击启动，这直接证明 `build/creo_session/config.pro` 的 `protkdat` 被 Creo 读取、持久化注册生效（此前该目录无 config.pro，条目从未出现）。

| 检查项 | 结果 |
| --- | --- |
| 重启后回调状态 | `readiness=ready`、`reason=live_identity_verified`、`loaded.process_id=22648`（新 xtop）、`command=MechDogBlend_71b1093a77c51aa09cbda000_2a5f6d01`、`dll_sha256=71b1093a…`、`initialize_code=0`、`terminated=false` |
| 重启后建模链路 | `creo_new_part`（wb_restart_loft，revision 1）→ `sk_low`（z=0、R10、revision 2）→ `sk_high`（z=20、R6、revision 3）→ `creo_loft` 直纹圆台（revision 4）全部 succeeded |
| 几何核对 | 体积 4105.0144 mm³，圆台解析值 π×20/3×(10²+10×6+6²) = 4105.0144 mm³，偏差 0.000000 |
| 持久化 | `saved_file_reloaded_and_verified=true` |

FEAT-029 本机生命周期主线由此完成：首次注册 → 启动 → ready → 直接放样 → 关闭 → 重启（MCP 协调器自动拉起、`state=ready`）→ 条目仍在列表 → 再次启动 → ready → 再次放样且几何精确。仍开放：兼容升级（不同版本热更回调代际）、回退及多目录并存场景，需其他环境配合，本机无对应条件。

**本轮关闭方式的备注**：Creo 的退出确认对话框不接受 `WM_COMMAND` 或注入点击，最终以结束进程完成关闭；重启后 Creo 自行弹出 `pse_abnorm_exit_dlg` 并继续，未影响连接与建模。若后续要在不干预进程的前提下走完整退出流程，需要可用的交互桌面（供操作员点确认）或受支持的关闭接口。
