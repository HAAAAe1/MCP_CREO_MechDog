# 未知作业与受控模型恢复

当前状态：恢复实现纳入0.3.4；BUG-001按用户决定关闭，FEAT-018仍验收中。Creo卡死根因未定，完整实机及WorkBuddy未完成；关闭与发布不代表这些验证通过。见[本次验证记录](validation/BUG-001-recovery-2026-10-17.md)。本机开发联调只启用指向 E 盘的 `MCP_CREO_MechDog_dev`；这是客户端注册名，不是已发布版本号。

适用于0.3.4提供的 `creo_reconcile_model`；历史公开0.3.3没有该工具。通过 `creo_capabilities` 确认实际部署，更新源码后构建执行器并重新连接 MCP，不能仅凭磁盘上的版本说明判断客户端已经加载新工具。

超时或失联不证明建模没有发生。先保留原 `job_id`，用 `creo_get_job` 查证据；不要重交原计划、编辑 `model.json` 或删除 reservation。`creo_startup_status(retry=true)` 只复核通道，模型处置使用下述独立接口。

## 查询

```json
{"model_id":"<异常模型ID>","mode":"inspect"}
```

持久化查询不连接 Creo，通道忙或没有 Creo 时仍可使用。返回 revision、pending_job、原任务/执行器身份、基线与候选 SHA256、各动作的 `available/reason`、有 10 分钟有效期的 `evidence_token` 及已有处置。查询不会解除模型保护。

需要核对会话时显式加 `"live":true`。实时预检使用同一 Toolkit 通道，繁忙时返回 busy；检查模型来源、健康、单位、外部依赖及相对登记基线的偏离。它不保存、擦除或接受几何。失联或权限不足表示无法确认，不等于安全。accept_live 必须先做实时预检。

## 明确选择动作

| action | 结果 | revision |
| --- | --- | --- |
| restore_baseline | 丢弃本模型受管会话副本的偏离，从摘要匹配的已登记检查点重载核验 | 保持 r |
| accept_saved | 仅选择原作业核验检查点绑定的保存候选，核对几何/特征/参数后保存重载并登记 | r+1，一次 |
| accept_live | 接纳实时预检中明确选中的健康自有会话几何，保存重载核验后登记；不保证原计划全部完成 | r+1，一次 |
| abandon_new | 放弃 revision=0 且无基线的新件，只擦除可证明归属的会话副本；保留文件、输入和审计 | 不推进，状态 abandoned |

只支持可证明独立、受管的 part/sheetmetal。assembly/drawing、外部依赖、未记录进程身份或缺失/改动的基线等不能通过本接口强制接受；保留证据并按返回原因人工核对。没有 model_id 的 legacy plate 产物不在本接口范围。

调用者必须明确选定动作；会丢弃会话修改的 restore/abandon 及会接纳成果的 accept 都不能由 Agent 因超时自行选择。下例只是字段格式，实际值必须来自本次预检，不能照抄占位符：

```json
{
  "model_id":"<异常模型ID>",
  "mode":"apply",
  "action":"restore_baseline",
  "expected_revision":1,
  "expected_pending_job_id":"<本次预检返回的pending_job；为null时发送JSON null或省略字段>",
  "evidence_token":"<本次预检令牌>",
  "idempotency_key":"operator_recovery_001"
}
```

`expected_pending_job_id` 契约：必须逐字等于本次预检返回的 `pending_job`。预检返回 null（无待定作业）时发送 JSON null 或省略该字段，两者等价；**不要发送空字符串 `""`**——空串/空白串会被作为请求缺陷精确拒绝（错误引用实际收到的值），不会与 null 混同，也不会被当作模型 revision 冲突。客户端确实无法发送 null 时优先省略字段；字面字符串 `"null"` 在当前 SDK 下会被预解析为 null，但不要依赖该行为。revision 与 pending 不匹配分别返回独立的 stale 错误并给出模型实际值。

接受后只轮询返回的恢复 `job_id`，不重复提交原计划。同一幂等键与相同输入返回同一恢复任务；换动作或输入必须换键并重新预检。文件、部署、revision 或 reservation 改变会拒绝旧证据。busy 表示本次未获准，遵循其 blocking 字段，不假设排队。

## 判断完成

恢复作业必须 `succeeded`；除 abandon 外还须 `saved_file_reloaded_and_verified=true`。核对处置动作、revision、保存文件与摘要、原生特征/尺寸/参数/体积，再用最新 revision 继续正常编辑。原未知作业仍保持原历史；其 recovery.resolution 和模型 reconciliation 记录此次独立处置，不能把 accept 解释为原计划剩余操作已执行。

恢复再次失败或不确定时保留原 pending 及 recovery_pending，不自动重跑原生动作。登记采用持久化提交决策：决定提交前中断须重新核对；决定提交后查询可仅补全元数据，不再次推进 revision。即使通道已经空闲，也不能据此解除模型保护。

单文件摘要采用流式读取，最多 1 GiB/8 秒，持久化快照预算 12 秒；超过预算准确拒绝。原生恢复/实时预检阶段 90 秒、断开 20 秒、Python 外层 115 秒，仅约束此次执行器，不终止 Creo。构建沿用既有有界流程。新旧版本、开发者注入与 WorkBuddy 黑盒的实测边界见联合任务卡及本次验证记录。
