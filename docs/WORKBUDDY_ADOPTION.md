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

   section=sheets指工程图图纸页，不是钣金壁/折弯/展开数据；不要以该段在零件上不可用判钣金接管失败。公开接口未提供的钣金专有语义保持未验证，features中的other也不作为特征丢失的充分证据。
8. 支持类型外、非毫米、带外部依赖、不健康模型应明确拒绝。若能够实际并行调用，再测试并发；busy应含blocking字段、不排队、不自动重试。无法并行就写并发未验证。

报告逐项记录工具、完整输入、job_id/model_id、终态、revision、几何/参数、保存重载、回滚与原始错误。区分通过、失败、阻断、未验证。内部文件占用、临时文件清理、哈希实现和登记原子性不纳入黑盒通过结论。Creo12.4的结果不外推Creo13或其他环境。

## 2026-10-19字段修正复验

先等待已受理任务结束，由操作者重启指向E盘开发目录的MCP连接器，保留Creo及所有原件。WorkBuddy仅用公开接口记录版本、实际路径、启动源码指纹及source_changed_since_startup=false；确认指纹清单含native/inspection_units.h。未重启、工具缺失或身份仍变化则报告阻断，不用源码/Git/配置补证。

1. 在Creo切到已保存的WB_REJECT_INCH，重新枚举并记录受管列表基线；接管只读inspect仍应available=false、millimeter_units=false，无ID/令牌/副本/登记。嵌套inspection.units应为实际英寸长度单位标识，不能是mm；units_query_code=0。两层volume_mm3都应null，volume_query_code=0仅表示SDK体积查询成功，不表示该量已换算成mm³。不得执行prepare/apply或转换原件单位；核对来源、modified、当前窗口、会话数量与受管列表不变。
2. 待操作者切到仍无盘且无受管关联的独立WB_UNSAVED_03，再创建新prepare任务（新副本名与新幂等键），只轮询该job。预期任务result.adopted=false、adoption.status=adopt_pending、revision=0，compact/full查询和模型列表adopted一致为false。原件仍当前且无来源。显式apply后预期result.adopted=true、ready/revision1及保存重载verified；再重放原prepare键，仍返回原prepare任务及adopted=false，不将历史准备任务改成确认成功，也不回退当前ready登记。

这两项是修正后新增的公开复验，不将修正前的成功或内部隔离SDK/stdio检查算作本轮实机通过。单位查询失败/NaN等内部故障注入只由开发者隔离验证，WorkBuddy不能为此运行本地脚本。真实再生失败、原件关闭、快照改写和实际并发保留各自未验证状态。

## BUG-073 草图引用复验

修复改动涉及Python与原生执行器：先等待已受理任务结束，由操作者重启指向E盘开发目录的MCP连接器，保留Creo及既有模型。WorkBuddy仅用公开接口记录版本、实际路径、启动源码指纹及`source_changed_since_startup=false`；工具数应为86。未重启或身份仍变化则报告阻断，不用源码/Git/配置补证。

1. 自建模型：`creo_execute_plan` 新建零件，第一操作为带标签草图（如`label=wb73_rect`，XY面矩形），第二操作为引用该标签的挤出基准体（如`label=wb73_base`）。只轮询返回job，预期succeeded并记录体积与revision。
2. 用`creo_inspect_model(section=features)`记录该草图特征的真实`id`与`name`（预期name为标签的大写形式，如`WB73_RECT`）；用`section=aliases`记录注册名（预期小写`wb73_rect`）。
3. 同一草图连续四次`creo_extrude`，每次先查当前revision、使用全新标签，仅改`sketch`写法：
   - 特征ID整数（如`sketch=<id>`）。若你的客户端把整数序列化成带引号字符串，如实记录实际到达形式；修复后两种到达形式都应成功；
   - 特征ID纯数字串（如`sketch="<id>"`）；
   - `features`段返回的大写`name`；
   - `aliases`段返回的小写注册名。
   四次均预期succeeded、revision逐一递增、保存重载verified；同截面小深度挤出的体积增量应符合几何预期。
4. 故意传不存在的标签（如`sketch=wb73_no_such`）：预期failed、`rollback_succeeded=true`、错误信息含`available labels`候选列表且列表包含该模型的已注册标签；模型revision、体积、特征数不变。
5. 受管接管模型对照：在现有`wb_fields_managed`（或操作者另备的接管副本）上重复数字串、大写名、小写名三种写法，预期与自建模型行为一致；每次成功revision+1。若其`RECT_40X30`截面挤出落在既有实体内，体积应保持不变，记录实际值。
6. 重复标签保护：用已存在的标签提交应被拒绝且不产生job或模型变化。

报告逐项记录工具、完整输入（含sketch的实际写法）、job_id/model_id、终态、revision、体积、特征数、保存重载、回滚与原始错误全文。区分通过、失败、阻断、未验证。`creo_loft`的实机数字串对照因回调注册需人工前置，本轮可不做，不将未测写成通过；不读源码/Git/本机配置，内部序列化实现细节记"无法确认"。
