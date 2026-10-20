# FEAT-044/023/022：WorkBuddy MCP 黑盒验收提示词（0.5.0 开发分支）

请只通过已连接的 MCP 工具验收；不读取、分析或修改源码，不运行本地脚本/单元/开发检查，不检查本机配置或 Git。无法从公开接口确认的身份信息写"无法确认"。本文件是待执行场景，不是通过记录。

修复与新增改动涉及 Python 与原生执行器：先等待已受理任务结束，由操作者重启指向 E 盘开发目录的 MCP 连接器（`MCP_CREO_MechDog_dev`），保留 Creo。WorkBuddy 仅用公开接口记录版本、实际路径、启动源码指纹及 `source_changed_since_startup=false`；工具数应为 **87**（新增 `creo_open_file`）。未重启、工具缺失或身份仍变化则报告阻断，不用源码/Git/配置补证。

测试发起者准备素材：本机一个既有已保存零件（外部目录）、同目录几何不同的 `.prt.1` 与 `.prt.2` 两版本、一个完整小装配（含至少 2 个子件）、一个缺件的装配目录；会话可操作后逐项执行。

## A. 磁盘打开主链（creo_open_file）

1. `creo_session_status`：确认 connected，记录返回中的 `server_version`（应与 capabilities 的 version 一致）。
2. `creo_capabilities`（无参）：默认应返回 compact 摘要页（含 `detail="compact"`、`support_status`、sections 目录与 families 索引），不再是旧全量文档；记录其大小量级。`support_status.disk_open.status` 应为 supported。
3. 打开既有零件：`creo_open_file(file_path=<绝对路径>, idempotency_key=<8-80字符>)` → 返回 job_id，轮询 `creo_get_job`。预期 succeeded、`result.model_id=null`、`result.adopted=false`、`open_file.displayed=true`、`origin` 等于所选文件路径、`model_type` 与文件一致；`identity_before` 与 `identity_after` 一致、`source_file_changed_during_open=false`。用 `creo_list_session_models` 确认该模型入会话且被当前显示；Creo 窗口应显示该模型。源文件字节是否不变如公开接口无独立证据则记未验证。
4. 同 key 重放同路径：应返回原 job（不重复执行）；同 key 换路径应拒绝。
5. 数字版本：对同目录 `.prt.1`/`.prt.2`（几何不同）：省略版本路径应打开 `.2`（最高）；显式 `.prt.1` 应打开 `.1`。以打开后的体积/特征或 origin 尾名核对版本选择。
6. 中文与空格路径：准备含中文与空格目录名的零件路径，应正常打开。
7. 非法输入：相对路径、不存在的文件、非 `.prt/.asm` 后缀、`.prt.0` 应在提交前明确拒绝且不产生 job。
8. 同名冲突：会话已含某模型名时，打开同基名同类型磁盘文件应拒绝（错误含 SESSION_NAME_CONFLICT），不加载；记录会话清单未变。

## B. 装配打开与保护

9. 完整装配：先确保会话无零件/装配（必要时由操作者在 Creo 中关闭）；`creo_open_file` 打开完整装配 → 预期 succeeded、`model_type="assembly"`、显示成功、`model_id=null`。子件入会话由 `creo_list_session_models` 观察。
10. 非空会话装配拒绝：会话存在零件/装配时再开另一装配，应拒绝（ASSEMBLY_REQUIRES_EMPTY_SESSION），不加载。
11. 缺件装配：把装配某子件文件移走（操作者执行），打开该装配 → 预期 failed、错误含 RETRIEVE_FAILED、`missing_components="unknown"`、报告 `remaining_session_models`（可能残留对象，不自动清理）。
12. 打开后不接管：对刚打开的外部模型调用 `creo_adopt_current_model(mode=inspect)`，行为按既有接管契约记录（可接管/拒绝均如实记录）；确认 `creo_open_file` 本身未创建受管模型。

## C. capabilities 分页与诊断（FEAT-023/008）

13. `creo_capabilities(detail="full", section="references")`：按 `next_cursor` 翻页遍历，记录页数、每页条目数、`complete=true` 收尾；页大小应受 32 KiB 约束（记录实际量级）。`section=tools` 应列出 87 个工具条目。
14. 错误处理：未知 section、非法 cursor、compact 下传 section/cursor 应明确拒绝；跨 section 误用 cursor 应拒绝。
15. 顶层支持状态：compact 的 `support_status` 应含磁盘打开、会话枚举、接管、装配检查（FEAT-045 planned）各项状态。
16. 接管诊断：Creo 空窗口时 `creo_adopt_current_model(mode=inspect)` 应返回 `NO_CURRENT_MODEL` 前缀错误（保留 ProMdlCurrentGet 与 -8 原码）；对装配模型 inspect 应拒绝且携带稳定 `reason_code`（如 `unsupported_model_type`）与 `refusal_details`（实际单位、依赖/健康未知标记）。

报告逐项记录工具、完整输入、job_id/model_id、终态、revision、几何/参数、Creo 实际显示与原始错误。区分通过、失败、阻断、未验证。`asm_mx.asm.16` 原场景保持"待原环境复验"，不以本机样件替代。真实并发仅在能实际并行调用时测试，否则记未验证。
