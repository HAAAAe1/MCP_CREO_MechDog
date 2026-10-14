# BUG-006 最终 MCP 验收提示词

由测试发起者先部署修复并重启目标 MCP，再将以下内容交给 WorkBuddy。只调用 MCP 公开工具，不查看源码、Git、本机配置或执行测试脚本；不可观察的内部规范化和源码身份记为无法确认。本机环境为 Creo 12，Creo 10 由其他机器协助者验证。

> 验收 BUG-006 引用契约修复。先调用 creo_capabilities、creo_startup_status 和 creo_session_status，记录服务版本、实际 Creo 信息、可见工具和就绪状态；未 ready 时停止建模，保留原始状态。
>
> 确认 capabilities.references.by_tool 分别给出 axis_pattern、sheetmetal_flange、round/chamfer、create_sketch 的参数形状。轴示例应包含 axis 几何 id、datum_axis_feature 标签和 datum_feature 兼容标签；说明几何 id 与特征 id 的区别，示例 id 必须由实际模型巡检替换。
>
> 创建一个独立小模型：先创建名为 spin_axis 的基准轴，通过 X/Y 两张基准平面形成 Z 轴；创建中心 40×20、厚 4 mm 的底座；在 Z=4 的 XY 草图上创建圆心 (12,0)、半径 2 mm 的圆并向上拉伸 2 mm，特征标签 boss。只提交一次，轮询实际 job_id，记录初始 revision、体积约 3200+8π mm³、保存重载成功。
>
> 使用 creo_axis_pattern，leader=boss，axis={"kind":"datum_feature","label":"spin_axis"}，count=2，increment_deg=180，expected_revision 取实际最新值。此前报告中的通用标签形式现在应通过，任务必须 succeeded、revision 增加 1、体积约 3200+16π mm³、saved_file_reloaded_and_verified=true。保留完整输入、job_id/model_id、终态、几何和保存信息。
>
> 在另一个相同独立模型上，用 datum_axis_feature 标签或巡检到的真实 axis 几何 ID 执行相同阵列，比较任务结果。若验证 execute_plan，请在独立模型的追加计划中采用相同 datum_feature 标签输入；不得把第二次阵列叠加到同一个已阵列特征上冒充等价验证。
>
> 在可用模型上，以 datum_plane/axis=z 作为 axis_pattern.axis 提交，应在入队前拒绝，并说明需要 axis 几何 ID 或 datum_axis_feature 标签。查询模型确认 revision 未变化、没有新 pending_job；不把基准平面的 axis 字段当作旋转轴。
>
> 对已有其它有效测试场景，按文档核对 flange.edge 的裸边、round/chamfer.references 的集合包装、草图字典 plane 的 reference 包装。未实际实施的工具场景记为未验证，不由能力示例推测建模通过。
>
> 报告逐项记录通过/失败/未验证，附公开版本、模型与任务 ID、原始输入返回、实际几何、revision 和保存重载。未知结果不重复提交，不关闭用户已有 Creo。开发者单元测试不替代本报告。
