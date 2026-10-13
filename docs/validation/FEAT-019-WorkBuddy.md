# FEAT-019：WorkBuddy 最终 MCP 验收提示词

本提示词用于已部署 FEAT-019 的服务。开始前，由使用者保存并正常退出 Creo，或明确指定“已有会话复用”场景；自动启动开关、故障配置和第二客户端由使用者另行准备。开发者实机验收尚在排查，不能将本文作为通过证据。

可直接复制以下内容：

> 请对已连接的 MCP_CREO_MechDog 做 FEAT-019 最终黑盒测试。全程只调用公开 MCP 工具，不查看、分析或修改源码，不读取 Git 或本机配置，不执行本地脚本、单元测试或终端命令。
>
> 1. 调用 creo_capabilities，记录服务版本、工具数和 startup 字段；确认有 creo_startup_status。版本号本身不能证明构建身份，公开接口无法确认的源码身份记为“无法确认”。
> 2. 轮询 creo_startup_status，记录实际出现的状态、message、connected 和等待时间。检查 MCP 能在等待中继续响应能力查询。若观察到未就绪状态，调用一次 creo_new_part；应返回未就绪错误，不能返回 job_id。若已立即 ready，此项记为未观察到，不模拟通过。遇到 timeout、selection_required、configuration_error 或 launch_failed，保留原始返回并停止建模；人工处理后才能使用 retry=true 复查。
> 3. ready 后调用 creo_session_status，确认 connected=true。提交一次完整计划：XY 面矩形 min=[-10,-5]、max=[10,5]，草图 label=startup_profile；引用该草图拉伸 depth=2，特征 label=startup_solid；断言实体体积 400 mm³。轮询 creo_get_job(detail="full") 到终态，核对 status=succeeded、体积、原生特征及 saved_file_reloaded_and_verified=true，记录 job_id、model_id 和 revision。
> 4. 用返回的 model_id 和当前 expected_revision 调用 creo_set_parameters，设置 STARTUP_SIZE=17.0。仅提交一次，等待任务成功和保存重载通过；再调用 creo_inspect_model，核对参数值 17、体积仍为 400、revision 只递增一次、pending_job=null。
> 5. 若使用者已准备第二个客户端或重连客户端，在同一 Creo 会话上重复状态查询，并使用上述 model_id 检查 revision 和参数。记录是否复用了现有模型；公开 MCP 接口不能直接证明 GUI 启动次数或进程身份，这些内部项记为未验证。
> 6. 只有实际同时发起了多个客户端的状态请求，才能报告并发观察通过；没有第二客户端或并发能力时记为未验证。不要将同一客户端依次查询称为跨进程并发测试。
> 7. 自动启动关闭、正在启动、人工确认、多会话或失效指定 ID，只测试使用者已准备的场景。核对明确的等待/禁用/选择/失败反馈和重试结果，不推测未准备场景通过。不要自动关闭会话或重新提交 unknown_outcome 任务。
>
> 最后按“通过 / 失败 / 未验证”逐项报告，附工具名、实际输入返回、任务与模型 ID、几何、参数、revision、保存重载和原始错误。不要用界面出现、进程存在或启动状态 ready 代替建模成功。明确 Creo 版本；Creo 12 结果单列实验兼容，不能代替 Creo 10 正式基线。
