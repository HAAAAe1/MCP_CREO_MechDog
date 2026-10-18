# DEV-036 WorkBuddy 黑盒验收记录（2026-10-17）

执行依据 [DEV-036-WorkBuddy-test.md](DEV-036-WorkBuddy-test.md)；受测服务为本机 `MCP_CREO_MechDog_dev`（E 盘主 worktree，提交 `4aa56dc` 工作区，用户已重启客户端使 `creo_process_snapshot` 新字段生效）。WorkBuddy 报告原件由用户存于 `build/workbuddy_acceptance_dev036_2026-10-17.md`（忽略目录，不提交），本文为其转录与开发者只读核对；环境为 2026-10-17 处置后的稳定通道（Creo 12.4/release 44，parametric PID 4156/xtop PID 14912，14:12 UTC 批次）。

## 结论：全部通过

| 部分 | 结果 | 要点 |
| --- | --- | --- |
| 0 新字段 | 通过 | `creo_process_snapshot` 首次调用即出现（服务重启生效）：available=true，parametric pid 4156 / xtop pid 14912，created_at=14:12:14/15 UTC，与开发者记录的当前批次完全一致 |
| 1 稳定性对照 | 通过 | 3 次间隔探测（14:47:21→14:49:46 UTC，跨约 3.6 分钟）全部 connected=true/0，无失效 |
| 2 建模闭环（MCP 路径） | 通过 | 新建 rev 0→1 + 编辑 rev 1→2 均 succeeded 且 `saved_file_reloaded_and_verified=true`；体积 15000.0 与 14497.345175425633 均与公式精确吻合——**补齐 T05 的 MCP 传参黑盒**（此前 ZCode 客户端层传参失败仅属该客户端） |
| 3 空值协议（T07） | 通过 | 空串 `""` 精确拒绝（received ''、不含 Stale、状态未变）；**字面 "null" 被接受为 null 并取得完整终态**（apply succeeded→reconciliation_committed→abandoned/rev 0/保护清除/原失败作业保留）——BUG-055 遗留项闭环；同参重放返回同一 job_id（幂等）；显式 JSON null 仍被客户端降级为空串拒绝（与 BUG-055 A-2 实测一致）；省略字段对照（另建 T2）同样 abandoned 闭环 |
| 4 M2 公开状态 | 通过 | `rec_m2_x8q2m1`：abandoned/rev 0/recovery_pending=null/reconciliation.action=abandon_new（recovery_id `a1454f0d…`，即本轮 T08 执行的恢复作业），只读无写操作 |

关键 job/model：建模 `715e11f2…`/`b9ec2a86…`（模型 `42ce221e…`，rev 2）；T 造错 `a23b50e9…`（failed，-23/execute_set_dimensions）；字面 null 恢复 `2a98ca6b…`（abandon_new，key `wb036-literalnull-b2c9-01`）；T2 造错/省略字段恢复 `0610afdb…`/`27a51473…`（key `wb036-omit-b2c9-02`）；模型 `81840790…`（wb_dev036_t07_b2c9）与 `1984b7f4…`（wb_dev036_t07n_b2c9）均 abandoned/rev 0。

## 报告 deviations 处置

1. **`name` 键被静默忽略**（模型名走默认 `ai_part_<前缀>`）：提示词未显式给键名、WorkBuddy 首次用了 `name`，服务端对未知参数键静默忽略（MCP SDK/pydantic 默认行为）。改用 `model_name` 后生效。行为如实记录；是否要求未知键报错属独立接口设计问题，未发现数据风险，暂不立卡，留待用户决定是否登记。
2. **提示词期望体积 14973.6 为开发者算术笔误**：正确期望 15000−π×16×10=14497.35，实测与公式及 `material_removed_mm3`（502.6548）完全吻合，建模结果正确。
3. **T2 补充样本合理**：T 在字面 null 步骤已 committed 无法二次成功 apply，WorkBuddy 另建同计划 T2 完成省略字段对照终态，符合任务书 3⑥ 的对照意图，未越界。

## 开发者只读核对（2026-10-17，`4aa56dc` 工作区）

对本机 `jobs/`、`models/` 持久化逐项比对 WorkBuddy 报告：上表 6 个作业（succeeded/failed 状态、reconciliation 的 action 与 idempotency_key）与 3 个模型（status/revision/recovery_pending/model_name）**全部一致（9/9 OK）**，包括 `name` 键忽略导致的默认模型名 `ai_part_42ce221e7251`。未执行任何新的写操作。

## 汇总

DEV-036 全部验收项完成：T01/T02/T06（夹具）、T03/T04（38 次探测跨 7.5 分钟+空闲对照）、T05（本地路径+本次 MCP 黑盒）、T07（空值协议完整终态）、T08（M2 交接）及 WorkBuddy 黑盒（新字段/稳定性/建模/空值/M2 确认）。BUG-055 的「稳定通道下字面 "null" 完整终态」同步闭环；其「外部 Creo 9 未复测」维持不变。未验证项：服务版本/工具总数（WorkBuddy 未调用 capabilities，记无法确认）、`creo_process_snapshot` 在连接失败场景下的黑盒表现（本轮通道稳定未出现失败，夹具级已由单测覆盖）。
