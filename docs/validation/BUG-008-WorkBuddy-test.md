# BUG-008 WorkBuddy 黑盒验收提示词

请仅通过 WorkBuddy 已连接的 MCP 工具验收 BUG-008；不查看、分析或修改源码，不读取本机配置，不运行脚本，不结束进程，不清除 reservation/pending_job。测试发起者应连接 E 盘本次开发实现；本轮没有部署 C 盘。以下为待执行场景，不是通过记录。

1. 调用 `creo_capabilities`、`creo_startup_status`，记录版本、公开 runtime 身份及源码漂移标志、可见工具与会话信息。应能看到 recovery 模块和 result_delivery 的运行指纹，以及 scheduling 中的 unknown_outcome 说明和 20 秒断开预算。接口没有提供的 commit/构建身份、SDK/宿主细节记“无法确认”，不读取仓库补齐。
2. 等待 startup ready，再调用 `creo_session_status`；真实连接须 connected=true、toolkit_code=0。记录 startup 的 verified_at、verification_age_seconds、snapshot、stale；快照不作为实时连接成功证据。初始连接未成功就停止建模并记录环境差异，不把该情况归因于本项恢复失败。
3. 只读查询 job `272513b7238040c68dce4b923725d870`。预期仍未确认，提供 recovery 核对信息、model `27143ef77ce641938543e0ca44cc3c03` 的 pending_job/revision/保存基线；不将进程退出、缺元数据或保存文件存在推断为成功。调用 inspect_model 记录该模型状态。不得修改此历史测试件、清锁或重新提交它的操作。
4. 新建专用零件，取得成功终态和最新 revision。向该件提交以下计划：XY 矩形 `profile`，范围 [-5,-5]～[5,5]；由 profile 拉伸 `solid`，depth=6；断言 require_solid=true、volume_mm3=600。成功后调用 set_parameters 将 `BUG008_MARKER` 设为 8。每次使用最新 revision；记录 job/model、参数、bbox/体积、delivery_complete、disconnect_code 和 saved_file_reloaded_and_verified。所有成功写任务应保存重载 true。
5. 对同一件提交一项预期原生失败：先 set_parameters 增加 `BUG008_SHOULD_ROLLBACK=1`，再以 label=`invalid_extrude`、sketch=`missing_profile`、depth=1 拉伸。记录完整原始错误、失败阶段/调用、回滚结果及 revision。失败后刷新并分页 inspect，核对体积仍为 600、原 MARKER=8、回滚参数不存在，revision 不因失败或只读刷新增加。只读任务不要求保存重载 true。
6. 使用两个真实重叠请求调用 `creo_startup_status(retry=true)`，轮询两端。记录起止时间、状态变化、busy/coordinated 和验证时间；旧 ready 不应先冒充本次 retry 成功再退回 building。waiting_for_channel 应说明可确定的占用者；无法确定时如实为空。retry 的总预算为 preparation 180 秒加配置的 startup 预算（默认总计 300 秒），中途不重置；状态查询应及时返回。到期仍 in-flight 应明确说明、保留保护且不重复启动。若平台无法真正并行调用，写“并发未验证”，不把串行调用称为并发通过。
7. 恢复 ready 后再次确认真实 Toolkit code=0。新建另一独立小件，再向同一件提交计划：XY 矩形 after_profile 范围 [-2,-3]～[2,3]，拉伸 after_solid 深度 5，设置参数 RECOVERED=1，断言 require_solid=true、volume_mm3=120。另建 20×10×3 无圆角无孔的快捷 plate，断言体积 600 mm³。所有接受任务取得终态和保存重载 true；再查询步骤 4 的原件和参数，确认原保存基线仍可用。可额外从原件新建工程图，验证 drawing 的正常收尾与保存重载。
8. 若测试发起者提供了已准备的真实故障环境，记录原 job/model、故障输入、原始错误和 revision，再只用公开状态/查询/retry 核对。保存后无最终结果或断开失败须保持 unknown_outcome，不得宣告成功、自动重做或释放未知模型写保护；connected=true 也不等于原作业已解决。若未提供此环境，明确将“历史 transform→保存后挂死→-38 整条链、受损 Creo 的自动恢复、内部看门狗/进程存活/文件机制”记为未验证。不要自行制造挂死、强杀或关闭用户 Creo 来补场景。

报告请逐场景列出工具名、完整输入、调用起止时间、job/model、终态、实际几何/参数、保存重载、revision、回滚和原始错误。分别列出通过、失败、未验证、需要人工处理；正常 retry、预期建模失败回滚和开发者合成夹具不等于真实受损通道已自动恢复。若 unknown 仍在，继续保留它，并说明需要核对的对象与公开可行下一步。
