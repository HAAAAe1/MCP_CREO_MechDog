# BUG-007 WorkBuddy MCP 验收提示词

本提示词用于修复版部署、MCP重启及回调初始化后，交由WorkBuddy直接调用公开MCP工具验收。WorkBuddy不读源码、Git、本机配置或日志，不修改文件，不运行Python或开发脚本。未部署修复版时停止本项测试，由发起者准备环境。

请执行BUG-007最终黑盒验收。长度使用毫米。每次修改只提交一次，轮询同一job_id到终态；若unknown_outcome、提交/轮询响应丢失或持续无进展，停止新的写操作，保存实际返回并报告，不能清pending_job、取消不存在的任务或重交未知任务。先查询creo_capabilities、creo_startup_status和creo_session_status，记录公开版本、runtime.code_root、source_changed_since_startup、direct_blend_callback准备信息与连接状态。准备文件不证明回调已加载；接口不提供的构建身份记无法确认。

只使用新建的独立测试件，不复用用户模型。按下列顺序执行：

1. 用creo_execute_plan创建XY矩形草图（min=[-10,-10]、max=[10,10]、offset=-5），沿正方向拉伸5，断言volume_mm3=2000；记录实体、任务终态和saved_file_reloaded_and_verified。
2. 新建草图检查点：XY圆sk_a，center=[0,0]、radius=10、offset=0；XY圆sk_b，center=[0,0]、radius=6、offset=25。记录creo_inspect_model结果、特征ID和实际revision。调用creo_loft，传model_id、实际expected_revision、label=blend_probe、sections=["sk_a","sk_b"]、mode=add、interpolation=straight、new_body=false。查原生Blend有效、2截面、straight、单实体、volume=5131.268000863329（容差0.01）、bbox=[[-10,-10,0],[10,10,25]]、revision推进一次、原草图ID保留及保存重载。
3. 用三个独立模型串行重复步骤2，第二轮将sections换成检查点公开返回的两个整数feature_id。实际记录每轮耗时，不能以第一轮推测后两轮成功，不能把串行测试称为并发。
4. 另建模型，用creo_execute_plan中op=loft追加相同两截面，查相同几何/原生参数/重载。两个入口必须保持一致。
5. 另建三截面straight：R10@Z0、R8@Z12.5、R6@Z25；检查3截面、同样5131.268000863329体积及重载。另测两/三截面smooth，检查实际原生模式与数量；使用creo_capabilities公开种子信息调用creo_new_loft_part建立匹配的独立种子对照，体积对照容差0.01，不把smooth体积套用straight解析公式。
6. 在步骤1形式的2000mm³已有底座上追加步骤2放样，检查单实体、volume=7131.268000863329、bbox=[[-10,-10,-5],[10,10,25]]、原底座/草图ID和引用保留、revision推进及保存重载。
7. 在独立检查点上调用重复截面、不存在的标签、非XY截面、mode=cut/surface、new_body=true和过期expected_revision。记录实际拒绝与错误；查询模型证明原特征/几何/revision保留。不可把所有拒绝都写成同一个推测原因。
8. 在已成功放样模型追加一个Z40、R1圆草图，同时断言volume_mm3=1，预期作业失败。检查rollback_succeeded、原Blend模式/数量、实际体积及revision保留；调用creo_refresh_model核对恢复模型，再创建新的2000mm³小件验证后续通道和保存重载。
9. 若发起者已准备未初始化/已卸载环境，分别调用creo_loft和execute_plan的loft，预期BLEND_CALLBACK_SETUP_REQUIRED、30秒观察阈值内明确失败、回滚/模型/revision保留，后续小件成功。准备环境和处理加载提示由发起者完成，WorkBuddy不注入锁、不终止进程、不改变Creo安全设置。未准备的首次确认、外部模态、NEVER/ALWAYS实际策略场景记未验证。

报告逐项列出工具输入、job_id/model_id、阶段/终态/耗时、原始错误、体积/bbox/原生参数、保存重载、revision、回滚与实际可见Creo结果。区分通过、失败、受限和未验证。内部DLL调用、临时文件/hash、重试预算等非公开机制不纳入WorkBuddy结论。Creo10由协助者独立验证，不能从Creo12.4结论外推。
