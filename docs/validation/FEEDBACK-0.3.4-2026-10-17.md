# 2026-10-17：0.3.4 恢复工具与 Creo 9 反馈补录

按用户要求同步当前 E 盘 [BACKLOG](../BACKLOG.md)，新增缺陷候选 [BUG-055](../work-items/BUG-055.md)，重复主题与建议沿用已有 ID。本次只更新文档、任务范围及原件，不执行报告中的升级、备份、Python 直连、模型放弃、注册、重建或环境修改。

## 原件与身份

[原始报告](feedback-0.3.4-2026-10-17/creo9-recovery-callback-report.md)逐字节归档：11317 字节，SHA256 `da4b778a23d0ee3f962ef84cfadcd6afe39bba476fafe50c2083dd31521dd58b`。完整源路径、原文件名、登记基线和方法边界见[清单](feedback-0.3.4-2026-10-17/manifest.json)，原件设置 `-text`，已有验证文件保持不变。

| 项目 | 报告提供的内容与边界 |
| --- | --- |
| 测试环境 | 2026-10-17 16:00–16:55 GMT+8；Windows 10 / Creo 9.0.0.0 / release_numeric=41 / stdio；服务 0.3.4、84 工具。本轮没有复测该环境 |
| 升级部署 | 报告称发现远端更新后执行升级，源码及种子 ZIP 最终校验一致；种子首次下载不完整，重下校验通过。没有持续异常或服务端损坏证据，不新增分发缺陷 |
| 源码/种子身份 | 报告仅摘录 ZIP SHA256 前后缀、version.py 指纹一致及 source_changed_since_startup=false；未附全量调用/指纹原始输出，不能证明本地后续开发改动已部署。9 个 PRT 摘要不变也不能独立证明其生产版本或跨版本可加载性 |
| 当前登记基线 | E 盘 `codex/bug-054-feedback033` / `65ea3db4578e334575936734b7c2366fabce90c1`，已包含 BUG-054/DEV-033 本机开发与实机验收成果；不是反馈方受测身份。本轮不回退或改写该进度 |
| 方法边界 | 报告混合 MCP 工具调用、本机升级/文件核对、源码分析及 Python 直连/手动驱动。只将真正经 MCP 的操作记为黑盒观察；直接 Python 成功不证明 MCP apply 成功 |

报告未提供完整 job_id/model_id、token/expected_pending 原始请求、同次状态时间线、原始 native.log/job.json 或保存重载链。末尾的 F 盘留痕位置仅为来源说明，本轮未读取该机器资料或用推测补齐。

## 新增缺陷候选

| 项目 | 事实线索 | 登记与下一步 |
| --- | --- | --- |
| [BUG-055](../work-items/BUG-055.md) | failed / revision=0 / baseline=null 的 `wb_reg_pat` inspect 可用，仅 abandon_new；报告的 MCP apply 传 expected_revision=0、expected_pending_job_id=null 被 stale 拒绝，本地 Python 对照可推进到 abandoned | P1 / 待核实 / 未排期。先取得实际 MCP schema、请求形状、服务收到的值及证据状态，分客户端与适配/业务校验定位；标准 null 与空串不是同一个已证实的协议输入 |

报告将其定为 P0 并断言“null 必然变空串、一行可修”，本台账保留为报告判断。本地 None/空串对照只证明比较行为不同，尚不能定位转换层；没有新证据就不能以 `value or None` 放宽 pending/revision/token 校验。BUG-001 的原关闭决定保持，此处是新恢复工具调用路径线索，独立于历史 IPC 卡死根因。

## 去重映射与新增细节

| 报告主题 | 归属 | 本次补充与未测边界 |
| --- | --- | --- |
| 恢复 inspect、apply 与证据时效 | [FEAT-018](../work-items/FEAT-018.md)、BUG-055 | inspect 的原作业/owner、动作可用性、token/600 秒与禁止重放为正例；MCP apply 仍未通过。评估令牌时效说明、重新 inspect/人工复核后更新证据；不自动复用过期授权，不承诺延长或自动 apply |
| 回调状态及入队前提示 | [FEAT-029](../work-items/FEAT-029.md) | prepared / readiness=unknown / next_action=人工启动注册，与从未注册的会话相符；报告记录 protocol=3、身份/迁移提示。补两个建模入口的预检/摘要建议，未知不能当 ready，查询不隐式加载 DLL。首次加载、兼容升级、回退及直接放样成功仍未测 |
| 种子加载 -16、生产版本与可用性标签 | [BUG-034](../work-items/BUG-034.md)、[FEAT-030](../work-items/FEAT-030.md) | Creo 9 / 0.3.4 再报失败；available/哈希仅文件完整性。保留 seed_build_version/兼容证据建议，未知生产版本不得猜填；未取得依据前不直接宣称“所有种子由 12.4 构建，Creo 9/10 都不可用” |
| 筋失败与支持文案 | [BUG-017](../work-items/BUG-017.md)、FEAT-008/006 | 再报 Rib regeneration failed on the requested material side，缺全量草图/方向/实体及失败特征证据；补环境与已测范围提示，版本差异不是已证实失败根因，保留本机正例及验收中状态 |
| component_constraints 不更新位姿 | [BUG-036](../work-items/BUG-036.md) | 再报旧 (-30,20,0)+30° transform、underconstrained=false；继续分别核对存储/求解/实际位姿和重载，未提供完整引用与作业标识 |
| round 独立 radius / 计划 size | BUG-019 | 重复参数契约反馈，保留兼容性核对，不新建缺陷 |
| dump_feature_tree 特征引用提示 | [FEAT-006](../work-items/FEAT-006.md)、[FEAT-008](../work-items/FEAT-008.md) | 原生名 H34 未匹配，创建别名 h34 成功。补 label/id/原生名及大小写规则和有界候选指引；没有承诺接受原生名时，不据此认定导出功能不可用 |
| list_models 分页 | BUG-013、FEAT-008 | 报告实际触发 complete=false / next_cursor 的正例，文档强调第一页不等于全量；不以此补齐全部预算边界验收 |
| toolkit_busy 无确定 owner | [BUG-009](../work-items/BUG-009.md) | owner_determined=false 和重试指引符合既有未知占用者回退。没有调用时间线/所有者快照时，不因另一个 dump 后来运行就认定诊断回归；补可关联占用身份线索，不重开已完成条目 |
| 新工具真实 MCP 冒烟 | DEV-006 / DEV-007 | 新增可空字段、默认值、错误传递、inspect→apply 的真实协议覆盖建议；开发者可用受控夹具测协议，WorkBuddy 仅公开工具，不读取源码/配置或执行本地 Python |

FEAT-018/029 仍验收中，BUG-017 维持原验收边界，BUG-034/036/019 维持待核实；BUG-009/033 和 BUG-001 的原完成状态保持。本轮不新建能力 ID、不把旧主题重复插入当前台账。

## 正向证据与排期边界

报告还提供 Ø6×10 孔约 `282.74 mm³` 去料、参数/关系、布尔并集、翼型截面、PDF、特征树 XML、UDF inspect 和文件哈希正例。孔正例补 [BUG-033](../work-items/BUG-033.md) 的外部 0.3.4 观察，其余作为限定环境证据保留；没有完整作业/模型与保存重载链，不宣称全工具或完整 Creo 9 运行时验收通过。`9 个 available` 不能抵消原生种子加载失败。

新增恢复调用问题建议优先核实真实协议形状与证据有效性，再决定修复范围，不执行报告中的 Python 绕行来代替 MCP 验收。DEV-033/BUG-054 的当前开发、实机通过与剩余 WorkBuddy 范围保持；本轮没有实施 BUG-055、修改 token/环境/加载策略、修改源码版本或启动发布，继续遵守当前 Toolkit 联调约束。
