# BUG-009 WorkBuddy 黑盒验收

只直接调用已连接 MCP 工具，记录工具实际返回和 Creo 实际结果。不读取、分析、修改源码，不执行本地脚本或单元测试。仅测试本条通道时序及诊断；无法通过 MCP 观察的内部锁、文件注入与重试预算记为未验证。

## 公开身份与前置

通过 capabilities / startup_status / session_status 记录服务版本、可见工具、环境与会话；核对 `scheduling` 描述。目标为 E 盘开发服务，版本仍是 0.3.1；使用公开 runtime 的入口与启动指纹确认部署，不凭版本号判定。接口未提供的身份字段记为无法确认。等待 ready；不关闭已有 Creo，不盲重试 unknown_outcome。

## 场景

1. 新建 10×10 mm 矩形草图并拉伸 6 mm，断言体积 600 mm³。轮询至 succeeded，写作业保存重载须 true，记录完整 job_id、model_id、revision 和时间。
2. 观察 succeeded 后立刻提交下一项 save 或参数写入，不额外等待；至少 20 轮。逐轮记录上次终态查询起止时间、下次提交起止时间、原始响应和新 job_id。成功写入 revision 递增，保存重载 true。遇 busy 记录占用者；不得把明确拒绝当已接受的任务丢失。
3. 实际同时发起同模型 STL/STEP/IGES 导出，或由两个客户端同时调用。记录客户端标识、每次调用起止时间，证明存在重叠；每项要么返回 job_id 后完成，要么返回结构化 busy。没有实际并行调用时，明确写“并发未验证”。
4. busy 必须保留 MCP 错误标志，同时返回 status=busy、accepted=false、占用 job/model/操作及重试指引。占用 job 可确定时，调用 get_job 核对；探针/构建等没有 job 或无法确定时，ID 可为 null，但要说明原因。retry_after_seconds 仅是重查间隔。等待占用操作结束后，只重试明确被拒绝的请求。
5. 任务运行时并行查询 get_job / list_jobs / inspect_model / list_models；这些查询应可返回持久化状态。refresh_model、导出和 session_status 需要 Toolkit，允许按通道规则拒绝。
6. 使用同一 expected_revision 实际并行写同一模型。核对只接受一次有效修改，另一项为 busy 或过期 revision 拒绝；不得发生丢失更新、重复应用或 revision 倒退。随后用旧 revision 提交，仍应明确拒绝。
7. 在新测试模型上触发明确原生失败（例如计划先写测试参数，再引用不存在的草图做拉伸）。核对失败、回滚标志、revision 和保存检查点；随后刷新并成功编辑。遇 unknown_outcome 停止写入并保留原始证据，不能靠重复提交或清 pending 恢复。

## 报告

分别列出通过、失败、未验证。保存完整调用时间线、入参、原始 busy/错误响应、job/model ID、终态、revision、体积、保存重载与回滚结果。旧任务成功后仍 busy 时，核对是否为另一个当前占用者；没有占用证据的拒绝单独列缺陷。内部锁清理和真实超时无法通过 MCP 安全构造时，不纳入通过结论。
