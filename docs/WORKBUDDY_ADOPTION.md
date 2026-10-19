# FEAT-042/043：WorkBuddy MCP 黑盒验收提示词

请只通过已连接的 MCP 工具验收；不读取、分析或修改源码，不运行本地脚本/单元/开发检查，不检查本机配置或Git。无法从公开接口确认的身份信息写“无法确认”。本文件是待执行场景，不是通过记录。

测试发起者先确认会话可操作，并在同一 Creo 会话手工准备001.PRT：毫米、XY矩形40×30、Z=0至20的长方体，从未保存。其他场景另备外部目录已保存零件、含未保存尺寸/参数/新特征的零件和独立钣金件。

1. 用公开环境/会话/能力接口记录运行身份及工具清单。应能看到 `creo_list_session_models` 和接管prepare模式；如果未部署或仍为旧连接器，报告阻断，不猜测源码已生效。
2. 枚举会话，记录001的名称、类型、当前状态、origin、has_saved_origin=false、modified。使用limit=1和cursor遍历同次快照；未知字段保持null。对limit=51、非法cursor检查明确拒绝。查询前后当前窗口不变，不产生新受管模型。
3. 对当前001做只读接管inspect，预期提示prepare，无可用ID/令牌。执行prepare（独立幂等键），只轮询返回job。预期成功、保存重载verified、adopt_pending/revision=0、体积24000。原001仍在会话且无保存来源、窗口仍为001。
4. 未确认时尝试普通regenerate，预期拒绝且revision不变。重放同一prepare请求应得到同一job/model；相同键更换名称应拒绝。检查列表来源类别，分别记录任务result.adopted、result.adoption.status、列表adopted与revision；字段语义矛盾时单独报告，不以顶层布尔值判断已确认。相同响应支持公开幂等重放，内部原生执行次数若无公开证据则保持未验证。
5. 检查result.adoption证据并apply（新键），预期ready/revision=1。通过inspect找到Z=20的顶面，用thickness=2的shell去顶面，预期7152±0.01 mm³、revision=2、保存重载verified。原001仍保留。
6. 独立再准备一份无盘快照，由操作者在prepare后修改或关闭原模型再确认。修改场景先保持原件当前，用 `creo_adopt_current_model({"mode":"inspect"})`（不带model_id）记录当前来源几何，无盘原件仍应返回prepare指引；只记录摘要，不再次prepare。带model_id的续签响应中current_model沿用准备时来源摘要，不用于证明原件当前几何。普通creo_inspect_model在adopt_pending时没有几何结果，也不表示准备文件不存在。等令牌过期后先检查apply明确拒绝，再按原model_id续签、记录同一快照身份并确认；不得重新创建副本。apply后检查副本仍为准备时几何，并与已变化的原件摘要对照。使用独立来源测试放弃快照，预期abandoned、后续普通编辑拒绝。

   放弃快照时，reconcile inspect若返回pending_job=null，apply优先省略expected_pending_job_id；若返回非空job ID则逐字传回该值。WorkBuddy曾将显式null序列化成空串，服务会以received ''准确拒绝；不要把空串当null，也不要绕过其他证据/版本保护。该客户端行为沿用BUG-055记录。

7. 分开测试已有文件clean、dirty及钣金接管。dirty场景要事先明确并记录未保存尺寸、参数及新增特征；逐项检查副本，不只比较特征数。原件文件是否字节不变如公开接口无独立证据则记未验证，不推测通过。
8. 支持类型外、非毫米、带外部依赖、不健康模型应明确拒绝。若能够实际并行调用，再测试并发；busy应含blocking字段、不排队、不自动重试。无法并行就写并发未验证。

报告逐项记录工具、完整输入、job_id/model_id、终态、revision、几何/参数、保存重载、回滚与原始错误。区分通过、失败、阻断、未验证。内部文件占用、临时文件清理、哈希实现和登记原子性不纳入黑盒通过结论。Creo12.4的结果不外推Creo13或其他环境。
