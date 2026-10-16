# BUG-008：重启后损坏启动历史的自动恢复

日期：2026-10-16（Asia/Shanghai）。分支 `codex/bug-008-channel-recovery`，提交基点 `001a4b8088344249c0a04eca0dbe6dc923435950`，dirty=true，服务版本保持 0.3.1。本次继续修复 [WorkBuddy 定向复验](BUG-008-WorkBuddy-retest-result-2026-10-16.md) 尚未通过的自动启动分支；原报告保留不改。精确实现、命令与结果见 [结构化证据](BUG-008-reboot-recovery.json)，不沿用上一轮指纹代表新实现。

后续状态：新 [WorkBuddy 报告](BUG-008-WorkBuddy-reboot-retest-result-2026-10-16.md)已交付并复核，按本机分层证据完成关闭，见 [关闭复核](BUG-008-closure-2026-10-16.md)。本页及 JSON 保留开发验收当时的指纹、结果和时间，不重写为 WorkBuddy 冷态通过。

## 复核与实现

WorkBuddy 已确认旧补丁的单次/真实重叠 retry、实时连接、120 mm³ 实体与参数、保存重载以及 unknown 保护通过。重启后仍因 380 字节 NUL 的共享启动记录停止自动启动；只报告结构化错误没有完成这条恢复路径。

开发者只读预检确认本轮实际记录的创建和修改时间均早于 Windows 于 2026-10-16 00:50:38.5Z 的启动时间。原字节 SHA256 仍为 `08c3e5bbea4fba57201a69d4bf70a0d255df921fdef4924c22da087f9338c2bc`。这支持“旧进程不能跨这次重启继续启动”的前提，不证明记录为何写坏。

新实现通过有界的 `Win32_OperatingSystem.LastBootUpTime` 查询取得系统启动时间，并与 `GetTickCount64` 核对，差异超过 2 秒即拒绝自动重建。该 WMI 属性的含义见 [Microsoft 文档](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-operatingsystem#lastbootuptime)。查询只读取这一个属性，子进程预算 5 秒，计入既有 preparation 180 秒和总预算，之后的构建不重新获得 preparation 预算。

自动恢复须同时满足：配置允许自动启动、没有指定其他会话、取得该目标的共享启动锁、取得 Toolkit 通道锁、两次进程核对均无现有或身份不确定的 Creo。文件创建和修改时间都须早于经核实的启动时间至少 5 秒。进程出现、同次开机损坏、不可信时钟、查询失败/超时、文件变化、备份或刷盘失败时均保留保护和可解释原因，不盲目启动。

满足条件时，在协调目录的 `history/` 中用独立文件保存原字节并同步刷盘，校验文件身份未变化，再原子、同步写入新的启动状态。随后由原有协调器启动一次配置的 Creo、验证 Toolkit 连接。发出启动请求前的 `launch_reserved=true` 也同步刷盘。原存档不覆盖；`startup_recovery` 返回旧文件哈希、字节数、归档路径、重启依据和状态。备份完成但状态替换失败时明确为 `archived_replacement_failed`，不宣称重建完成。

这里重建的是经重启核对后失效的**启动历史**；未知建模 job 的结果、模型 pending_job、revision 与保存基线继续保留。`connected=true` 不代表历史未知任务已解决。代码不自动退出 Creo、不重新提交原生操作、不改变服务版本或部署 C 盘。

## 本轮验证范围

对应回归位于 `tests/unit/test_startup_reboot.py`、`tests/unit/test_startup_retry.py` 及既有通道/登记测试。包含双协调者单次备份/单次启动、已有/不确定会话、同次启动损坏、备份/替换/刷盘失败、启动时间提供者故障、时钟偏差以及恢复查询与构建共享 preparation 预算。

| 检查 | 本轮结果 |
| --- | --- |
| `tools/test_unit.py` | 最终完整 246 项通过，0 failure / 0 error；本轮新增 16 项重启恢复回归 |
| 改动 Python 文件 Ruff | lint 与格式检查通过 |
| 实际桌面只读预检 | 确认 Windows 启动时间、旧 NUL 记录的前次开机身份、现有 Creo 与实时 code=0；没有写共享状态或模型 |
| 实机损坏历史冷启动 | 09:51:11–09:52:06（Asia/Shanghai）通过；初始无 Creo，两个新 E 盘 MCP 客户端自动协调，原 380 字节 NUL 留档并重建，09:51:28 两端共享本次 ready/verified_at；一端 coordinated=true，只新增一份归档，无人工打开 |
| retry 与建模 | 随后的真实双端 retry RPC 重叠 5.3262 ms，后续单次 retry、实时 code=0 通过。新建与编辑两个写任务均 succeeded / 保存重载 true；120 mm³、RETRY_VERIFIED=1、revision 1→2，交付完成且 disconnect_code=0 |
| 原保护对象与会话 | 历史 unknown 的 job/model/PRT 及 WorkBuddy 原测试模型/PRT 共 5 个文件哈希前后一致。MCP 客户端退出后仍为同一 parametric PID=19712、xtop PID=7936 和创建身份，无第二次启动 |
| 客户端退出后再连接 | 09:55:34–09:55:49 新 E 盘客户端再次连接成功，源码漂移 false、实时 code=0；前后仍为上述同一 Creo 进程身份，5 个保护文件不变 |
| 后续 WorkBuddy | 新实现步骤 1/3/4/5 通过，步骤 2/6 因环境未提供继续未验证；详见独立 [原报告](BUG-008-WorkBuddy-reboot-retest-result-2026-10-16.md) 与 [关闭复核](BUG-008-closure-2026-10-16.md) |

仓库根目录使用 `.venv/Scripts/python.exe` 执行完整单元及 `tools/dev_check.py --work-item BUG-008 --skip-unit`。后者因下述原始报告格式问题退出 1，不能写成通过。实际冷态执行 `tools/test_startup_retry.py --require-cold --expect-reboot-recovery --output build/bug008-reboot-auto/native.json`，经 Explorer 桌面启动两个新 E 盘 stdio 客户端，退出码 0。自动恢复由 MCP 初次连接的后台协调触发，`cold_automatic_startup=true`；显式 retry 发生在已 ready 后，`cold_explicit_retry=false`，不把它写成冷态显式 retry 触发。普通 Codex 宿主连接差异仍不在本项通过范围。

本轮模型 `4ef160e2a26241bbb527ec0ced6fb944`：新建 job `7d67387ed9794346a3967def5eb08b57`，revision=1；编辑 job `24339719a7a54fd68af22f43c590ae52`，revision=2，XY 4×6 矩形拉伸 5、参数 RETRY_VERIFIED=1、体积 120 mm³。原损坏记录自动保存为协调目录 `history/state-unreadable-276a59a26e204f018708b117e45b8a4a.bin`，归档哈希与上述原字节一致。没有预先删除或手工修复 state.json。`startup_recovery` 是触发该恢复尝试的诊断；后续正常 retry 的快照可不再包含它，原字节归档和本轮原始 MCP 输出继续保留。

标准开发检查在本轮受到两份无关原始报告的 Markdown 代码块格式问题阻塞：旧 SDK 编译失败报告、`feedback-2026-10-16/2026-10-16常驻回调注册负担与版本发现缺口.md`。原件与风格基线保持原样；补充语言检查仅排除这两份报告的 Markdown 格式，其余范围不变。标准入口失败与补充检查通过分别记录。

用户已明确允许正常关闭 WorkBuddy 测试用 Creo，再验证冷启动。第一次 `.NET CloseMainWindow()` 没有识别到 Creo 自定义主窗口；随后仅对核实的测试主窗口发送普通 WM_CLOSE。两次均未关闭会话，未强杀或关闭保存/退出确认。用户随后确认已正常退出；新的桌面只读检查确认 process 列表为空后，才执行上述自动启动验收。退出和启动两段过程分别保留在忽略的 `build/bug008-reboot-auto/`；没有将此前仅发出退出请求的尝试计为通过。

未测边界继续保留：历史 transform→保存后挂死→-38 完整链、故意损坏真实 Creo 的无人干预恢复、损坏记录的写坏来源、其他环境。WorkBuddy 对本次新实现的验收单独记录，不把其指纹匹配和已有会话通过改写为 WorkBuddy 自动启动已通过。
