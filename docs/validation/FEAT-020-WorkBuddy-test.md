# FEAT-020 最终 MCP 验收提示词

以下供测试发起者在部署本项源码并重启目标 MCP 后交给 WorkBuddy。只通过已连接 MCP 的公开工具验收，不查看、分析或修改源码，不运行本地脚本、单元或开发检查。Creo 10 由协助者在其他机器执行，Creo 12 在本机执行，报告分别保留实际版本与范围。

> 验收 MCP_CREO_MechDog 的 FEAT-020：版本检查与提醒。
>
> 首先通过 MCP 确认服务版本、可见工具和 Creo 环境。应有 `creo_check_update`，共 82 个工具，`creo_capabilities` 与 `creo_startup_status` 应含 `update` 字段。使用公开 runtime 信息确认目标部署；接口未提供的构建身份记为“无法确认”。如果缺少新工具，记录当前返回并停止本项验收，不要求读取配置、Git 或仓库来补齐。
>
> 1. 调用 `creo_check_update(force=true)`，保留完整原始结果。确认 current_version、latest_version、预发布标记、官方 release_url/download_url、时间、缓存来源、过期标记和错误信息。再调用默认更新检查、能力和启动状态，比较相同缓存时刻的 update 字段；正在刷新时允许 status=checking，启动/能力查询应及时返回。不得仅凭版本号推断本项已部署。
> 2. 由测试发起者准备公开发布数据：公开版本高于当前时应返回 update_available、两个官方入口和手动升级说明；相同或本地更高时不建议降级；最高公开版本为预发布时仍能发现并标识。发起者无法提供该场景时记为未验证，不能要求 WorkBuddy 修改版本或发布数据。没有可比较候选时只能返回 unknown，不能宣称已是最新版。
> 3. 由发起者准备 GitHub 网络不可用、超时或限流条件；若进程已有成功缓存，可在适当时机主动刷新。实际返回必须是 failed/unknown，不能宣称最新版。若保留上次成功目标，须有 stale=true 和本次 error。失败冷却期间 force 也可能返回缓存失败结果；通过 MCP 可见返回记录实际情况，不推断内部重试次数或缓存时长。
> 4. 网络失败期间继续查询能力与启动状态。只有启动 state=ready 后，调用 `creo_create_plate(length=20,width=10,thickness=2)` 创建一个小零件，不指定已有名称。只提交一次并轮询 job_id，必须 status=succeeded、体积约 400 mm³、saved_file_reloaded_and_verified=true；记录 model_id、revision、特征及保存文件信息。若启动未就绪，记录原始状态并把建模记为未验证，不关闭现有 Creo 或重复提交未知结果任务。
> 5. 若客户端实际支持并发，真正并行调用多个更新检查，并同时调用能力/启动状态，保留每次输入返回和时间。未实际并行则报告并发未验证；不能由工具列表或串行结果推断并发通过。
> 6. 出现 update_available 且 stale=false 时，向用户转述当前版本、新版本、预发布标记、版本说明与下载链接以及手动升级流程；同一会话对同一 latest_version 不反复提醒。不得执行下载、安装、关闭 Creo 或强制中断建模。实际 UI 提醒由客户端展示，不要求弹窗。
>
> 报告逐项给出通过、失败、未验证或无法确认，保留工具名、输入、原始返回、实际服务/Creo 版本、job_id/model_id、终态、revision、几何和保存重载结果。发布后更高版本可发现、真实断网和外部数据条件均以实际实施为准。本地开发者测试不能替代此报告；所有未实施场景明确列出，不推测通过。
