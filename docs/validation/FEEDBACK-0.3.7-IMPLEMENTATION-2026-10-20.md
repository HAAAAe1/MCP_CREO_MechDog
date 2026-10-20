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
