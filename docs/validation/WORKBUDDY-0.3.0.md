# WorkBuddy 0.3.0 全量实测补录

补录日期：2026-10-14。整理条目：[DEV-014](../work-items/DEV-014.md)。[原始报告](MCP_CREO_MechDog_0.3.0_全量实测问题报告.md) 已交付并归档，原文不改写。来源：`E:\Projects\workcreo\MCP_CREO_MechDog_0.3.0_全量实测问题报告.md`；SHA256：`83dbac0673a8a4a2fb3bf62c846d68ce09ebd28556c4453eb4fd6018f2e6e06a`。

## 完成情况与范围

**全量实测已完成，报告已交付；这表示本轮测试执行结束，不表示全部工具验收通过或全部问题已修复。**

报告时间为 2026-10-14 14:53–15:45（GMT+8）。报告环境为 Windows x64 / Creo Parametric 12.4.0.0（release_numeric=44）/ MCP 0.3.0 / 82 工具 / stdio / mm；服务目录为 `C:\MCP_CREO_MechDog`。仅适用于此环境，Creo 10 仍由其他机器补充验收。

| 报告汇总类别 | 数量 | 含义与边界 |
| --- | --- | --- |
| 正向通过 | 74 | 报告声称成功作业几何及保存重载通过；本次未重新调用 MCP 或独立复核全部作业 |
| 调用级失败或挂死 | 5 | loft、drawing_view_update、rib、dimension_pattern、create_feature_tree；失败不等于五项均已确认实现缺陷，后两项有输入适用性限制 |
| 前置条件受限 | 2 | inspect_udf、create_udf 缺 `.gph` 库；仅确认校验拒绝，未完成 UDF 正向验收 |
| 语义疑点 | 1 | solidify(cut) 报成功但体积和 bbox 不变，待确认输入与工具语义 |
| 合计 | 82 | 原报告称“82/82 全部完成调用”，但第七节同时说明 inspect_model / check_environment 等只读项复用了注册表或先前证据；缺少逐工具本轮调用清单，不能据此认定 82 个工具均有本轮新调用 |

导出覆盖 STEP/STL/IGES/JPEG，PDF 未单独验证；未覆盖每个工具的全部参数分支。串行忙碌拒绝与收尾竞态有报告记录，但未附真实并行提交的调用时间线，不能登记并发通过。无效最小元素树、存在几何争议的尺寸阵列不计为已确认建模缺陷。rib 输入合法性和 solidify 剪裁语义仍需复核。

## 证据分层

本项目 WorkBuddy 约定为只调用 MCP 的黑盒验收。本报告包含安装命令、Git 提交、job.json/native.log/model.json、源码定位和进程检查，属于混合来源报告；原文保留为用户交付材料，其内部机制分析不作为 MCP 黑盒通过结论，也不据此改变后续 WorkBuddy 测试约定。

- **报告中的 MCP 可见现象**：0.3.0 / 82 工具、connected=true 的初始会话、更新检查 up_to_date / 预发布标识、引用兼容别名通过、作业运行阶段和终态、几何/保存重载、错误响应。台账按“外部报告记录”引用，不冒充本次 Codex 复测。
- **开发者待复核线索**：DLL/UI 宏是 loft 卡点、worker 断开连接挂死、锁与终态发布竞态、TimeoutExpired 的异常捕获、counts 重算、回滚状态判断及复杂件保存失败。报告的源码定位、因果关系和建议方案均待当前源码复现确认，不能直接视为已证实根因。
- **身份与原始数据缺口**：报告提供升级 `b0851ef → a558ee8` 的本地记录，但未附完整受测源码指纹或 dirty 状态，不能用版本号/短提交替代实际受测身份。未交付完整逐工具输入输出、job_id/model_id 清单、重载返回或原始日志附件；已给出的模型名、feature id、revision 和体积按原文记录，不补造缺失 ID。
- **不一致的总体表述**：原报告摘要称失败均回滚，而 P1-7 明确记录 transform 的 rollback_succeeded=false、模型 status=failed；总体“失败安全通过”须保留这个例外。概括“全部命中解析解”的表中种子放样/叶片等没有解析期望，部分项目只有定性比较，按具体证据范围使用。

## 关键问题与当前结论

| 现象 / 本轮材料 | 台账去向 | 当前结论 |
| --- | --- | --- |
| t30_loft2：sk_a=R10@Z0、sk_b=R6@Z25，loft add/straight 停在 activate_blend_context，报告称约 600 s 后 unknown_outcome；种子放样 40650 mm³ 通过 | [BUG-007](../work-items/BUG-007.md) | 挂死与通道占用待开发者复现；不能用种子新建件通过替代已有件追加放样通过 |
| transform 失败后 new_part 已保存但无终态，后续 -38；startup retry 长时间无进展，重启 Creo 后恢复 | [BUG-008](../work-items/BUG-008.md) | 断开、通道失效与协调器恢复待核实；涉及用户会话的恢复方式须保护现有模型 |
| running 时 refresh_model 等被 busy 拒绝，succeeded 后立即提交偶发仍 busy | [BUG-009](../work-items/BUG-009.md) | 占用诊断和收尾竞态待复现；没有真实并发通过证据 |
| drawing_view_update(scale=2) 失败，toolkit_code=-1、operations=[]、rollback_succeeded=true | BUG-010 | 缩放更新失败待复现；位置更新仍须另测 |
| session_status 空错误、startup_status 缓存仍 connected=true | BUG-011 | 用户可见诊断/缓存新鲜度问题待核实，异常捕获方案仅为建议 |
| t30_probe 的 transform：feature_id=478，保存返回 -1；体积 9646.19、revision 未推进，模型被标 failed；干净件 t30_rb 成功 | BUG-012 / BUG-015 | 回滚语义和模型可用性、复杂件保存分别立项，不把几何完好等同于保存检查点已验证 |
| list_models(limit=20) 约 844447 字符；无 compact | BUG-013 | 用户可见载荷问题待复现，不需等建模能力扩展 |
| plate 80×60×20 / R5 / 3孔体积约 91989.38 正确，但 compact counts=0；失败 inspection 为 null/占位/实值三种形态 | BUG-014 | 统一 inspection 和计数契约；成功几何不掩盖返回结构问题 |
| solidify(cut) 在 z=30 基准面剪裁 z=20..40 实体，体积 81399.81861641473 不变 | BUG-016 | 保留语义疑点，不直接判定静默失败 |
| rib 再生失败；dimension_pattern 与最小 feature_tree 失败但缺元素诊断 | BUG-017 / FEAT-006 | rib 先复核输入；诊断缺口独立于无效输入是否应失败 |

其余历史复现、新增建议和次要问题逐项映射在 [统一台账](../BACKLOG.md#workbuddy-030-全量实测问题映射)，不另建排期清单。

## 已有条目的证据补充

BUG-006：本轮报告第四节 P0-1 明确记录 axis_pattern 的 datum_feature 兼容别名归一化通过，references.by_tool 覆盖 15 个工具；补强此前用户 N1 确认，保持已完成。其他工具包装写法的逐工具回归仍属 FEAT-008，不能全部算进 BUG-006。

FEAT-020：本轮升级并重启连接器后，creo_check_update 可调用，capabilities.update / startup_status.update 存在，current=latest=0.3.0、up_to_date、is_prerelease=true。本报告未补齐公开高版本提醒、实际客户端提醒去重、真实断网/限流和网络失败期间建模；维持验收中。早先 0.2.6 更新模块报告中的缓存与并发证据保留原日期，不能改名为本轮 0.3.0 全量回归。

DEV-013：发布完成与本轮发布后测试报告均可记录；发现新问题不改写已完成的分发验收，也不表示本版全量原生发布回归通过。DEV-002、BUG-005 和 Creo 10 未测范围保持原状态。
