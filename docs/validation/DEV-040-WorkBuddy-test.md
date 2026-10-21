# DEV-040：WorkBuddy 黑盒验收交接

日期：2026-10-18。当前仅准备提示词，尚未执行。当前停止新增 Toolkit 连接的约束有效；本提示词只用于发起者另行确认可联调的隔离环境。不得据此连接当前受限会话或处置历史 unknown 模型。

以下内容交给 WorkBuddy：

---

只使用已连接的 MCP 公开工具验收 DEV-040。不要读取源码、Git、本机配置、日志文件或运行 Python/开发测试；不结束或重启 Creo，不删除任务或模型保护。仅使用发起者提供并明确授权动作的专用测试模型。未提供必要前置状态的场景记为“未验证”，不要通过修改文件、故障注入或反复重交请求来制造状态。

先用公开工具确认服务名称、版本、可见工具与环境。构建身份未由公开接口提供时记“无法确认”；不要仅凭版本 0.3.5 认为已部署 DEV-040。发起者应提供本次部署身份与可操作会话确认。

## 场景与预期

1. **准入前过期凭证。** 对授权测试模型调用 `creo_reconcile_model(mode="inspect")`，保存 revision、pending_job、recovery_pending、动作和 token。等待超过返回的 600 秒有效期后，用同一 token 和原样 revision/pending 调用一次 apply。预期直接报凭证过期，未接受新作业；模型原保护与 revision 不变。需要继续时重新 inspect，使用新幂等键和新凭证，不自动执行旧动作。

2. **已接受但尚未开始原生执行的拒绝。** 仅当发起者已在隔离环境提供可观察此路径的测试条件时执行；MCP 没有控制原生执行暂停的接口，不要求 WorkBuddy 人为制造。调用授权 apply，接受后只轮询同一 job_id。若因执行前证据/会话选择变化拒绝，预期 `status="failed"`、`stage="reconciliation_refused"`、`failure_phase="before_native"`，并有 `reason`、原始 `message` 与 `finished_at`。正常登记清理时 `recovery_pending_released=true`，inspect 不再把此恢复作业列为 recovery_pending；原 pending_job、模型状态与 revision 保持原值。若清理失败，应有 `recovery_pending_cleanup_error` 且不得声称占位已释放；不要手动清理。

3. **原生会话指纹拒绝或原生中断。** 仅在发起者提供相应专用场景且明确准许时执行。出现 `Recovery refused: Creo session changed since recorded evidence` 不代表没有启动原生执行器。此路径预期仍为 `unknown_outcome` / `reconciliation_unconfirmed`，`failure_phase="native_worker_started"`、保留 recovery_pending 和原 pending_job；若返回原生结果，记录 `result.failed_stage`。不要根据消息里的 refused 把它报告成可直接重试的失败；停止新写入并交回发起者。

4. **幂等与可空字段。** 对每个已接受的场景，用完全相同参数和幂等键再次 apply，应返回同一 job_id 和既有状态，不启动第二次恢复。`expected_pending_job_id` 必须等于 inspect 的 pending_job；返回 null 时优先省略该字段，也可发送 JSON null。空串应准确拒绝，不能转换成有效凭证；字面字符串 `"null"` 的客户端行为单独记录。对确定性拒绝后的新恢复必须重新 inspect，并使用新幂等键，动作仍需发起者明确授权。

5. **busy。** 仅当客户端能够真实并行且发起者准许专用操作时执行。通道已有操作时提交应立即返回 `isError=true`、`status="busy"`、`accepted=false` 和 blocking 字段，不排队。记录两次调用的实际时间与原始返回；不能并行则报告“并发未验证”。锁文件占用、删除状态及系统错误码不能仅凭 MCP 黑盒判定，本场景不替代 BUG-057 的开发者复现。

## 报告

逐项记录实际输入、原始响应、job_id/model_id、终态、上述阶段与原因字段、前后 revision/pending/recovery_pending、幂等结果，以及适用的几何/参数、保存重载和回滚证据。compact 与 full 对同一作业的关键拒绝字段应一致。没有实际执行的恢复动作、内部文件机制和其他 Creo 版本全部记“未验证”；不要用本地脚本证据代替本次黑盒结果。

---

开发者离线证据与尚未执行的黑盒范围分别记录在 [DEV-040 执行记录](DEV-040-offline-2026-10-18.md)。
