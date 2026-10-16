# BUG-008：重启后自动恢复的 WorkBuddy 复验

这是新实现的待执行提示词，不是通过记录。请只使用已连接 MCP 工具，不查看/修改源码、读取本机配置、运行脚本、检查系统进程、清除 pending_job 或自行关闭 Creo。关闭/故障环境由测试发起者预先准备；不要自行制造挂死、强杀或重启电脑。

重新连接 E 盘开发服务后，调用 `creo_capabilities`，要求 `runtime.code_root=E:\Projects\MCP_CREO_MechDog`、`source_changed_since_startup=false`，并核对公开指纹：

| 键 | SHA256 |
| --- | --- |
| `server.py` | `a2389f8c97d36d1d687e7d508cf3fc3c545cb6574e8b7651267f74d29f6f0e60` |
| `creo_startup.py` | `7d803ee8c679da483080c9e3cda31b6cf276178383542a9b5e3fac82885c2a22` |
| `bridge.py` | `84eb1e0ec34fd208b28f403816f7bb876f0b67ea982b750b5d5f1eefdc677a85` |
| `src/creo_mechdog/startup_state.py` | `5b482745c0dfd93fc2ec699a1071b6c6cac1bca17944e854941bef197cda9e4c` |
| `src/creo_mechdog/windows_boot.py` | `4b3d521e3387eed0668317501e1ee6db7a81d32358c9fbd898c24957455bc6da` |

版本仍为 0.3.1，仅凭版本号不能确认更新。接口未提供的 commit/SDK/构建身份记“无法确认”，不读仓库补齐。

1. 记录 `startup.unreadable_history` 和 `boot_verification_budget_seconds=5`。轮询 `creo_startup_status`，保存实际状态、验证时间、新鲜度、错误与 `startup_recovery`。若只观察到开发者先前恢复留下的快照，明确写“读取恢复记录”，不能写自己完成了损坏历史下的冷启动。
2. 若发起者已准备“重启后旧损坏启动历史且 Creo 未打开”的环境，记录初始公开状态，再调用 `creo_startup_status(retry=true)` 并轮询。后台服务可能已在首次连接时开始恢复，应记录实际触发方式。预期原记录被归档、`startup_recovery.status=reconciled_previous_boot`、含原哈希/字节数与归档路径，最终 ready/connected=true，实际 session code=0，无人工打开 Creo。若无法核实这项环境，或当前仅为有效历史下的普通冷启动，就按实际场景命名，不外推为损坏历史恢复通过。
3. 在可用会话下先单次 retry，再做两个真实重叠 retry，记录起止时间和完整输出。两端应最终 ready，验证时间更新，无旧 ready 冒充本轮成功后倒退。不能实际重叠则并发未验证；不根据 coordinator PID 推测 Creo 进程数量。
4. 调用实时 `creo_session_status`，要求 connected=true、toolkit_code=0。只读查询历史 job `272513b7238040c68dce4b923725d870` 与 model `27143ef77ce641938543e0ca44cc3c03`：unknown_outcome、revision=9、pending_job 和保存基线仍保留。不得修改该历史件或重新提交未知操作。
5. 新建独立零件，取得成功终态和 revision=1；以最新 revision 提交一项计划：XY 矩形 `reboot_profile` 范围 [-2,-3] 至 [2,3]，拉伸 `reboot_solid` 深度 5，设置 `REBOOT_VERIFIED=1`，断言 require_solid=true、volume_mm3=120。两笔写任务须 succeeded、revision 1→2、saved_file_reloaded_and_verified=true；编辑任务应有 delivery_complete=true、disconnect_code=0，参数和 bbox/体积正确。已接受任务只轮询，不重复提交。
6. 若发起者另有同次开机损坏、时钟无法核实、已有/不确定会话或备份失败的环境，记录结构化原因与实际行为：不能盲目替换启动历史或重复启动，未知建模任务保护保持。没有相应环境则未验证，不执行本地注入。内部文件刷盘、锁、进程身份、预算机制均由开发证据说明，不纳入 WorkBuddy 通过结论。

报告逐项列出工具、完整输入、原始错误、起止时间、job/model、终态、revision、实际几何/参数、保存重载与回滚。将“损坏历史下的自动恢复”“有效历史普通冷启动”“已有会话重连”“读取过去的恢复快照”“人工打开后恢复”分别记录。未提供的历史 transform→保存挂死→-38 完整链继续未验证。最后复核历史 unknown 保护，没有证据不宣称已解决。
