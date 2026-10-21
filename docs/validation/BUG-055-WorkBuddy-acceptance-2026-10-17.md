# BUG-055 WorkBuddy 黑盒验收记录（2026-10-17）

执行依据 [BUG-055-WorkBuddy-test.md](BUG-055-WorkBuddy-test.md)；受测服务为本机 `MCP_CREO_MechDog_dev`（E 盘主 worktree，提交 `26a3edd`，修复后错误消息文本仅在本次提交后存在，可由 B-2 实测消息反证受测身份）。环境：用户关闭 Creo 后经 `creo_startup_status(retry=true)` 重启协商（launch_attempt=8），Creo 12.4（release 44）。WorkBuddy 报告原文由用户转述录入本记录；开发者只读核对见文末。

## 关键新证据：客户端 null→空串降级被实测证实

场景 A-2 中 WorkBuddy 客户端对 `expected_pending_job_id` 显式发送 JSON null，**服务端收到的实为空串**（修复后错误消息回显 `received ''`），apply 被精确拒绝且未创建作业；同一调用者改用省略字段（A-3）即成功。这直接闭环了外部 0.3.4/Creo 9 报告的根因链：服务端各层不做 null 转换（见 [BUG-055-fix-2026-10-17.md](BUG-055-fix-2026-10-17.md) G0/G1），**转换发生在客户端序列化层**；旧代码把该输入误报为 "Stale expected_revision or expected_pending_job_id"（外部报告所见），修复后回显实际收到值使其可观察、可按提示改用省略字段。客户端限制按提示词如实记录，未用空串冒充通过。

## 结果矩阵

| 场景 | 实测 | 判定 |
| --- | --- | --- |
| 0 schema 契约 | `expected_pending_job_id` anyOf[string,null]、default null、描述含"null 或省略、绝不空串" | 通过 |
| 1 样本制造 | M1 `rec_m1_7k3x9f2`/M2 `rec_m2_x8q2m1` 均 failed（`ProModelitemInit` -23，execute_set_dimensions），rev 0、无 part 基线 | 通过 |
| A-1 inspect M1 | pending_job=null、abandon_new available=true、token 600s | 通过 |
| A-2 显式 null | 客户端降级为空串 → `received ''` 精确拒绝，未创建作业，模型未变 | 通过（客户端限制如实记录，服务端行为符合契约） |
| A-3 省略字段 apply | 作业 `7715024458344c70832ebfc7ff6311c7` succeeded；模型 abandoned、rev 0、原计划未重放 | 通过 |
| A-4 幂等重放 | 同参重放返回同一 job_id，未产生新作业 | 通过 |
| A-5 历史保留 | 原失败作业 `33514d7f…` 仍可查询且 status=failed | 通过 |
| B-2 空串 | `received ''` 精确拒绝，不含 "Stale"，未创建作业 | 通过 |
| B-3 字面 "null" | 被接受为 null（mcp SDK 预解析兼容分支），作业 `194712b5135e424a82f4f76ad18e0eb0` 创建 | 通过（接受分支与单元协议测试锁定一致） |
| B-3 轮询 | 恢复执行时通道第三次掉线（native `connect_creo` -4）→ unknown_outcome，`recovery_required=true`，按约定停止、未重放、未清保护 | 环境干扰，未取得终态；"unknown 不自动重放、reservation 保留"契约本身按设计生效 |
| B-4 M2 收尾 | 未执行（通道不稳） | 未完成 |

附带模型 `ai_part_588d955f8935`（WorkBuddy 预探测时漏传第三步所建，succeeded/rev 1/24000 mm³）不属测试样本，已如实记录。

## 环境干扰：通道静默失效

本次最大干扰：Toolkit 通道每次验证通过后约 37–41 秒自行失效（`channel_health=not_found_or_unreadable`、`toolkit_code=-4`、`worker_exit_code=20`），共 3 次（11:30:04、11:41 前后、11:43:00 附近）；Creo 进程全程存活（parametric PID 18720、xtop 24056）。M1 两段流程恰好落在两个连通窗口内完成，M2 恢复执行时遭遇第三次掉线。服务未提供掉线根因的可观察字段；该现象超出本卡范围（BUG-001 已按用户决定关闭，不据此重开），是否登记新条目由用户决定。

## 开发者只读核对（2026-10-17，提交 `26a3edd` 工作区）

对本地 `jobs/`、`models/` 持久化记录逐项比对 WorkBuddy 报告：

- 作业：M1 造错 `33514d7f…` failed、M2 造错 `d3e449c8…` failed、M1 恢复 `77150244…` succeeded（action=abandon_new）、M2 恢复 `194712b5…` unknown_outcome（idempotency_key `bug055-m2-litnull-b8n…` 印证字面 null 分支）。全部一致。
- 模型：M1 abandoned/rev 0/recovery_pending 已清；M2 failed/rev 0/`recovery_pending=194712b5…` 保留；附带模型 ready/rev 1。全部一致。
- journal：M1 `intent-*.json` state=committed、`arguments.expected_pending_job_id=None`（省略字段在持久化层即 None）；M2 state=intent（native 未完成）。M1 在 jobs/ 下仅一个 reconciliation 作业，幂等重放未产生新作业。
- M2 native checkpoint：`connect_creo` -4、`completion_stage=before_disconnect`、`delivery_complete=false`。与报告一致。

## 结论与剩余项

BUG-055 的公开契约（null/省略等价、空串精确拒绝并回显实际值、非空精确匹配由既有单测/协议回归覆盖、幂等、历史保留、unknown 不重放）在 WorkBuddy 黑盒下全部按预期行为；外部报告根因链（客户端 null→空串降级 + 旧代码误报 stale）由 A-2/B-2 实测闭环。**核心验收通过。**

未取得证据（不推断通过）：M2 最终 abandoned 终态与稳定通道下字面 "null" 的完整终态；工具总数（`creo_capabilities` 响应 104,266 字符超 WorkBuddy 客户端上限，记为无法确认——次要观察，暂不登记条目）。M2 保持 `recovery_pending` 受保护状态；续做收尾需通道稳定（连续两次间隔 60 秒 `creo_session_status` connected=true）且用户确认掉线非人为/弹窗所致，由发起者明确决定，不自动执行。
