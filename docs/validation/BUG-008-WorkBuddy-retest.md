# BUG-008 retry 修复后的 WorkBuddy 定向复验

本提示词尚未执行；原失败报告保留在 [BUG-008-WorkBuddy-acceptance-2026-10-15.md](BUG-008-WorkBuddy-acceptance-2026-10-15.md)。本次只验收公开行为，内部损坏记录检查和开发者测试另见 [开发证据](BUG-008-retry.md)。

请只通过已连接 MCP 工具测试，不查看/分析/修改源码，不读取本机配置、运行脚本、检查系统进程或清除 reservation/pending_job。不自行关闭或结束 Creo。真实故障/关闭场景仅使用发起者已准备的环境；没有该环境就明确未验证。

本次公开运行指纹预期值如下，只比较 MCP 返回，不读取文件：

| runtime 指纹键 | SHA256 |
| --- | --- |
| `server.py` | `8c9db166d313793842b69d59f9f65f59a4c35b3998dde5709843f34cee37ba62` |
| `creo_startup.py` | `957108354ec952d5d6864f976f8144d9a21eea9643829210d3c415097fbef85c` |
| `src/creo_mechdog/startup_state.py` | `48a54c888a5532d4feba2c35735695e7fb6d175c801e1f52de1113902ebdb4fb` |

1. 发起者先重新连接 E 盘开发服务。调用 `creo_capabilities` 确认公开 `runtime.code_root` 为 `E:\Projects\MCP_CREO_MechDog`、`source_changed_since_startup=false`，并对照上述指纹。若仍加载旧实现则停止验收，不靠版本号 0.3.1 判定已更新。接口未提供的 commit/SDK/构建身份记“无法确认”。
2. 在已有会话下调用一次 `creo_startup_status(retry=true)`，保存完整输入和原始输出并轮询终态。应取得可解释的 JSON，不再只有 `Error executing tool`。正常结束时为 ready/connected=true，带本次验证时间。若返回忙碌、超时或 selection_required，完整记录原因与处理说明，不能算连接恢复通过。
3. 实施两个真实重叠的 `creo_startup_status(retry=true)` 请求，记录两次起止时间及后续状态。可用会话下两端应最终 ready，无旧 ready 冒充本轮成功后倒退。损坏历史下可能分别探测，verified_at 不要求相同，也不要求 coordinated=true；记录 `coordination_error`、`launch_state_known`、`automatic_launch_allowed`。若没有实际请求重叠，写“并发未验证”。不要从 MCP 无法观察的进程数推断“未重复启动”。
4. 调用 `creo_session_status` 验证实时 connected=true、toolkit_code=0。startup 的 stale/age 是快照提示，不能单独证明实时连接。只读查询历史 job `272513b7238040c68dce4b923725d870` 和 model `27143ef77ce641938543e0ca44cc3c03`，记录 unknown_outcome、pending_job 和 revision=9；保留未知，不修改或重提。
5. 新建独立测试件并取得成功终态，再向该件以最新 revision 提交一项计划：XY 矩形 `retry_profile`，范围 [-2,-3] 到 [2,3]；由该草图拉伸 `retry_solid`，depth=5；设置 `RETRY_VERIFIED=1`；断言 require_solid=true、volume_mm3=120。记录所有 job/model、revision、体积/bbox、参数、delivery_complete、disconnect_code、saved_file_reloaded_and_verified；两次成功写任务应保存重载 true，revision 1→2。所有已接受任务只轮询，不重复提交。
6. 若发起者已准备“Creo 关闭”的场景，先核对公开真实会话不可用，再单次/真实重叠 retry 并记录终态：共享历史无法信任时，预期明确 `selection_required`、`coordination_error.code=startup_state_unreadable`、`automatic_launch_allowed=false` 和人工步骤，不应泄漏成无明细错误。此结果只能记“安全停止，需要人工处理”，不能记“自动启动通过”。若接口表明历史可信且允许启动，则以实际 ready、实时 code=0 和新独立件成功为自动启动证据；无法确认启动前提则如实记录，不推测。没有现成关闭场景则本项未验证。
7. 若发起者随后人工打开 Creo，重复步骤 2–5，可据实际结果记录“人工打开后重连/建模通过”；不得将它归入自动恢复。最后再只读核对历史 unknown 对象保护仍在。历史完整 transform→保存后挂死→-38 没有对应环境时继续未验证。

报告分别列出：单次 retry、真实重叠 retry、结构化失败/人工处理、实时连接、独立建模、未知保护、自动启动及历史故障链。逐项给出工具、完整输入/原始错误、起止时间、job/model、终态、revision、几何/参数和保存重载。分别标明通过、失败、未验证、需要人工处理；本轮可复用原报告中未变路径的历史结果，但不得称为这次已重新测试。
