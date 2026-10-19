# FEAT-042/043：WorkBuddy 无盘接管主链验收补录

日期：2026-10-19（北京时间）。关联：FEAT-042、FEAT-043、BUG-071、FEAT-022。

## 证据来源与边界

本记录整理自用户在本对话转贴的 WorkBuddy 报告；未取得完整 MCP 原始响应导出。下列 ID、输入和数值按报告记录，省略的哈希不补全。WorkBuddy 通过公开 MCP 执行，开发者的 UI 素材准备与源码核对另列，不替代黑盒证据。

开发者归档前工作区为 `codex/feat-042-adoption-completion`，提交 `3a9a6166a0bd577ec1d88c03e84f24a73c1ae6e9`，受版本跟踪文件无修改。该 Git 身份不能证明 WorkBuddy 当时运行的服务身份；本段转贴未含运行版本、启动路径、源码指纹、SDK/编译器身份的公开接口输出，均记为无法确认。本机会话 UI 显示 Creo Parametric 12.4.0.0；不外推其他环境。

2026-10-18 开发脚本在首次就绪探测超时、`cases=[]` 的[历史记录](ADOPTION-COMPLETION-2026-10-18.md)保持原样。本次 WorkBuddy 成功不改写该历史，也不证明先前超时根因已经查明。

## 主链结果

素材为通过 Creo UI 新建的 `WB_UNSAVED_01`，毫米、XY 矩形 40×30、Z=0 至 20；未保存、未通过 MCP 建模工具创建。开发者 UI 体积测量为 24000.0 mm³。

| 阶段 | 报告中的公开接口结果 | 判定 |
| --- | --- | --- |
| 会话枚举 | 首次 `busy`、`accepted=false`、`blocking_operation=session_status`、job/model 均 null、`owner_determined=true`、`retry_after_seconds=1`；随后独立查询成功 | 观察到真实忙碌拒绝；没有实际并行调用证据，不能判并发测试通过 |
| 无盘发现 | `WB_UNSAVED_01` 当前、`origin=""`、`has_saved_origin=false`、`modified=true`、`model_id=null`、`session_model_id=524288`、`total=1`、`session_fingerprint=5320798621052244643` | 支持发现无盘未受管模型；session ID 仅为会话提示 |
| inspect | `available=false`、`reason=snapshot_required: use mode=prepare`、`available_modes=["prepare"]`，无 ID/令牌，`source_kind=session_only`；体积 24000、8 特征/6 面/12 边 | 通过 |
| prepare | `succeeded`、`stage=snapshot_prepared`、`adopt_pending`、revision=0、`source_kind=session_snapshot`、保存重载 verified、令牌 600 秒 | 通过；仍需显式确认 |
| 原件与窗口 | prepare 后原件仍当前、origin 空、modified=true；受管副本已在会话中但不是当前窗口 | 准备时原件保留、窗口未切换，通过 |
| 未确认保护 | `creo_regenerate(expected_revision=0)` 拒绝 `Model is not ready; inspect its last job before recovery`；列表仍 pending/revision=0/adopted=false/part_file=null | 通过 |
| 同键重放 | prepare 返回相同 job/model、created_at/finished_at 及哈希；同键换名拒绝 `Idempotency key already belongs to another adoption request` | 公开接口的幂等重放/参数冲突通过；不能仅由相同响应证明内部原生执行次数 |
| apply | `stage=adoption_committed`、ready、revision=1、adopted=true、保存重载 verified、体积 24000.0 | 通过 |
| shell | 顶面 id=56、normal=[0,0,1]、origin=[0,0,20]；内抽壳 2 mm，体积 7152.0、revision=2、保存重载 verified | 核心续作通过，符合 7152±0.01 mm³ |
| 续作后原件 | 原件仍在、非当前、origin 空、modified=true、model_id=null；受管副本为当前、已保存、modified=false | 原件保留，通过 |

### 请求与任务身份

- prepare 输入：`{"mode":"prepare","model_name":"wb_managed_01","idempotency_key":"adopt-prep-20261019-01"}`；job `5a2353093dcc43d9bef13996ec060534`，model `16981153f33bfbdf8f83f327ca8bfe4e`。
- prepare 时戳：报告中的 created_at 时间部分为 `03:33:40.989964Z`、finished_at 为 `03:33:47.771633Z`，未补造完整日期。快照 SHA256：`fe2a44216119952aad6321e63c04d15185d0feed5ee0ef2573e2f289ccf6d340`。
- apply 输入使用上述 model、prepare 令牌和 `idempotency_key=adopt-apply-20261019-01`；job `a0ab0414aec0471fa0e2cd8d42b50fec`。`inspection_source=adoption_snapshot_verified`，快照哈希与 prepare 一致。
- shell 输入：上述 model、`expected_revision=1`、`label=shell_open_top`、`thickness=2`、`remove_surfaces=[{"kind":"surface","id":56}]`、`outward=false`；job `785888f3830c4ed29a79b9c6e01f21ff`，stage=verified，9 特征/11 面/24 边，`toolkit_code=0`。报告仅提供保存文件哈希前缀 `058d0848…`。
- shell 返回 `rollback_succeeded=false`，本用例没有触发回滚；不视为失败，也不视为回滚验收通过。

## 待核实：prepare 的 adopted 字段语义

WorkBuddy 报告 prepare 任务 `result.adopted=true`，同时 `result.adoption.status=adopt_pending`、列表 `adopted=false`、`part_file=null`。准备成功不应被客户端解释为已经确认接管；通过依据为 stage、登记状态、revision 与嵌套证据，不取该顶层标志作为 ready 依据。

开发者静态核对见 `native/generic.cpp` 的复制完成路径：prepare 与有文件 apply 共享 `report.adopted=true`；Python `_commit_prepared` 保留原生 result 并补入 pending 的 adoption 证据。此为字段来源线索，不属于 WorkBuddy 源码验证，也尚未以新增回归确认修正方案。在 FEAT-042 内跟踪语义统一，当前验收期间暂不修改运行源码或构建产物。

## 剩余验收与素材

- 冻结后修改/关闭原件、令牌真实过期与续签不重复制、快照改写拒绝、独立来源 abandon_new：未验证。
- 外部目录 clean；已有文件含未保存尺寸、参数、新特征；独立钣金：未验证。不能只凭特征数量判断 dirty 复制语义。
- 不支持类型、非毫米、外部依赖、不健康零件、失败回滚、真实多客户端并发：本段未验证。内部文件故障/原子登记仍以开发者证据为限，不计入 WorkBuddy。
- 会话枚举的真实多页同快照遍历、完整类型矩阵和 unknown 字段：本段未验证。更早一次单模型查询报告不替代真正翻页。
- 连接器升级前/未重启/重启后身份对照：未验证。FEAT-022 保持验收中；BUG-071 的开发单元完成范围保持原状。
- FEAT-042/043 保持验收中，不因主链通过直接关闭。

开发者 UI 准备进度：已新建 `wb_unsaved_02` 空白毫米零件，模板 `mmns_part_solid_abs`，但切换其独立窗口时桌面控制返回 `GetCursorPos failed: 拒绝访问。 (0x80070005)`。50×40×10 实体尚未制作，不能交给 WorkBuddy 当作 20000 mm³ 合格素材。待完成后先由 WorkBuddy prepare 并回报冻结证据，随后再修改原件；abandon_new 使用另一个待确认快照，不能对已 ready 的同一登记重复套用。

## 同日后续：第二份 UI 素材已补齐

用户再次要求重试后，桌面控制恢复。开发者在同一个 `WB_UNSAVED_02` 中完成 FRONT（XY）草绘：以原点为角点，尺寸明确设为 50.00×40.00 mm；实体拉伸深度设为 10.00 mm。Creo「分析→测量→体积」实际返回 **20000.0 mm³**。收起测量浮窗并恢复三维视图，保留该零件为当前模型；本次没有执行保存或 MCP 接管。

第二份素材现已就绪，上段空白素材/控制阻断记录为此前过程。此处仅为开发者 UI 准备证据，尚无第二份素材的 WorkBuddy 枚举或 prepare 结果，不据此声明冻结/续签/放弃通过。下一步由 WorkBuddy 先核对无保存来源及未受管状态，执行 prepare 并回报 job/model、哈希和体积，再修改原件验证冻结语义；当前先保持 50×40×10 不变。

## 同日后续：第二份快照已准备，原件已改宽度

用户随后转贴 WorkBuddy 结果：`WB_UNSAVED_02` 的 origin 为空、has_saved_origin=false、modified=true、无受管关联；prepare 创建 job `20c98c32697d42ad9d9704d69e84b4bd`、model `2abbfbaae70183666f261d45076e2c8d`，副本名 `wb_managed_02`。终态 succeeded/snapshot_prepared/adopt_pending/revision=0，完成时间 `2026-10-19T04:41:16.609320Z`；中途曾有 commit_pending=true，随后收敛为终态。快照体积 `19999.999999999996 mm³`、8 特征/6 面/12 边、保存重载 verified；SHA256 `5c4ca52758fab440ba2f56152b7c3207902d92b282984aeeae3d67b008955f59`、87564 字节。报告称原件仍当前，副本非当前，total=4；令牌有效期600秒，预计北京时间12:51:16过期。该段仍为转贴结果，非完整 MCP 响应导出。

按用户要求，开发者随后通过 Creo UI 编辑原件 `WB_UNSAVED_02` 的原有草绘，将宽度 d1 从 **50.00 改为 30.00 mm**，另一草绘尺寸保持40.00 mm，原拉伸深度10.00 mm；再生后「分析→测量→体积」实际返回 **12000.0 mm³**。操作中误开的新拉伸已取消，未提交新增特征。没有保存、关闭原件或操作受管副本，收起测量窗口后原件仍当前。完成后时钟核对为 `2026-10-19 04:48:43 UTC`（北京时间12:48:43）。

下一步仍由 WorkBuddy 通过公开 MCP 核对副本保持约20000 mm³/8特征，并执行过期拒绝→inspect(model_id)续签→原model确认。原件变化是本段 UI 证据，尚不能据此认定副本冻结、过期拒绝或续签验收已通过。

## 同日后续：过期拒绝/续签报告及原件第二次修改

用户转贴 WorkBuddy 报告：04:51:34Z 使用原令牌与幂等键 `adopt-apply-expired-20261019-02` 提交apply，返回 `Evidence token is missing or expired; inspect again`。随后带原model_id的inspect返回同一模型、同一路径、同一SHA256和新的600秒令牌；会话total保持4。公开接口的过期拒绝与同身份续签已有通过报告；该段尚无确认后的冻结几何结果，不将模型数不变扩展为内部执行次数证明。

报告中普通creo_inspect_model对adopt_pending返回 `part_file=null`、`inspection_available=false`、`snapshot.source=unavailable`。应解读为该查询未暴露准备几何；prepare已经返回保存文件及哈希，不能解释成没有保存快照。续签的current_model仍为约20000 mm³，也不能据此推断原件没有变化。

开发者核对当前源码：`adoption.inspect(model_id)` 调用 `_prepared` 验证保存文件身份，再以 `snapshot["live"]` 构造证据；`_evidence` 将该准备时摘要放入current_model。省略model_id的inspect才派发当前来源原生预检。这是开发者对字段来源的说明，不是要求WorkBuddy读源码；客户端以公开调用分别核对两种摘要。文档和黑盒步骤已澄清，未修改运行源码。

开发者再次进入原件草绘时，UI仍明确显示 **30.00×40.00 mm**，与此前12000 mm³记录一致。按用户要求继续制作可见变化：宽度 **30.00→35.00 mm**，另一尺寸40.00 mm、原拉伸10.00 mm；再生成功，体积实际测得 **14000.0 mm³**。未新增特征、未保存或关闭原件，未操作受管副本；原件仍为当前模型。完成后的时钟为 `2026-10-19 05:21:39 UTC`（北京时间13:21:39）。

后续WorkBuddy应先在当前原件上执行不带model_id的只读inspect，预期得到约14000 mm³，再对原受管model_id续签并apply，确认副本仍约20000 mm³/8特征且保存重载verified。转贴中“12:01:40前有效”与本轮先后时间不一致，不采用该到期时刻；使用最新续签返回的600秒有效期。原件关闭、abandon_new及其他剩余矩阵仍未完成。

## 同日后续：冻结确认通过，第三份素材就绪

用户继续转贴 WorkBuddy 公开MCP结果：不带model_id的当前来源inspect实际读到 `WB_UNSAVED_02` 的体积 `13999.999999999996 mm³`、8特征/6面/12边，origin空，未再次prepare。对原model `2abbfbaae70183666f261d45076e2c8d` 续签，仍返回原快照路径及哈希；随后以幂等键 `adopt-apply-20261019-02` 确认，job `120bfdd8823a4e5d9bc01114edb6431b`，stage=adoption_committed、revision=1，完成时间 `2026-10-19T05:39:10.006132Z`。

确认后公开检查副本体积 `19999.999999999996 mm³`、8特征/6面/12边/1实体，SHA256 `5c4ca52758fab440ba2f56152b7c3207902d92b282984aeeae3d67b008955f59` 与prepare一致；`saved_file_reloaded_and_verified=true`、`inspection_source=adoption_snapshot_verified`，状态ready/revision=1/adopted=true/source_kind=session_snapshot、snapshot.source=saved_verified。原件仍在会话、非当前、modified=true、origin空、model_id=null；副本成为当前，总数保持4。原件修改后的冻结几何、同ID续签确认、保存重载与原件保留已有通过报告。过期拒绝只验证过一次超期18秒，不外推更长超期或其他时间边界；副本内部执行次数仍不以会话数量不变推断。

第三份独立素材由开发者经Creo UI创建：`WB_UNSAVED_03`，模板 `mmns_part_solid_abs`，FRONT（XY）草绘30.00×20.00 mm、拉伸10.00 mm；「分析→测量→体积」实际返回 **6000.00 mm³**。本次没有保存、接管或执行abandon，测量浮窗已关闭，第三份原件保持当前。准备时系统没有xtop进程或Creo窗口，经已安装Creo12.4的应用入口启动了新会话；没有新建Toolkit连接、结束进程或清除保护。前一报告的total=4属于此前会话，后续WorkBuddy须重新确认会话就绪和枚举，不复用旧cursor/session_model_id。结束UI操作后的时钟核对为 `2026-10-19 06:30:11 UTC`（北京时间14:30:11）。

下一步为WorkBuddy独立执行新来源prepare→reconcile inspect→abandon_new→普通编辑拒绝，并记录原件与受管登记状态、文件/审计的公开证据；尚无这条放弃链路的通过结果。关闭原件、外部clean/dirty/钣金、拒绝矩阵、快照篡改拒绝和真实并发等剩余范围保持未验证，FEAT-042/043继续验收中。

## 同日后续：第三份素材误保存后重新创建

用户告知误将 `wb_unsaved_03` 保存，该件不再作为从未保存来源使用。开发者保留已保存文件，另经Creo UI新建独立零件 `WB_UNSAVED_03_RETRY`，使用 `mmns_part_solid_abs` 模板；FRONT（XY）草绘明确设置30.00×20.00 mm，实体拉伸10.00 mm，体积工具实际测得 **6000.00 mm³**。本次没有执行保存或MCP纳管，测量浮窗已关闭、选择已清除，新件保持当前。

本轮开始时系统没有xtop进程或Creo窗口，经已安装Creo12.4应用入口重新启动；未操作Toolkit连接或清除保护。后续WorkBuddy应重新确认当前会话，并通过枚举核对新名称、无保存来源和无受管关联，使用新的幂等键及本次返回的model_id继续放弃快照验收。此处仅记录替代素材的UI准备，不声明abandon_new通过。

## 同日后续：放弃快照通过

用户转贴的WorkBuddy报告将来源名称记为 `WB_UNSAVED_03`，枚举显示origin空、has_saved_origin=false、modified=true、当前、无受管关联，session_model_id=524288、session_fingerprint=9090761655684717328、total=1；当前来源inspect读到体积5999.999999999999 mm³、8特征/6面/12边。此前UI曾准备同尺寸的RETRY件，本报告未含名称变化的过程，不将两者静默视为同一身份；本次验收身份以本报告的会话证据和新job/model为准。

- prepare输入：`{"mode":"prepare","model_name":"wb_managed_03","idempotency_key":"adopt-prep-20261019-03"}`；job `b7293ef8c6224cfbb47688b288a8699e`、model `37377d420244b91612bc5671164b5e60`。终态succeeded/snapshot_prepared/adopt_pending/revision=0，报告完成时间部分为08:08:39.799276Z。快照SHA256 `f2fdbdbed026ea28e0ebc71baa31e3a00aff622929370102915ccda059c67c75`、87615字节、体积约6000，保存重载verified。
- reconcile inspect：pending_job=null、original_job_id为上述prepare job、候选哈希一致；runner pid=23032与worker pid=12220均stopped=true。仅abandon_new可用，restore_baseline/accept_saved/accept_live均不可用。
- 第一次apply将expected_pending_job_id显式null传入后，服务错误回显received ''，拒绝空串；省略该可选参数后成功。该现象与[BUG-055](../work-items/BUG-055.md)已记录的WorkBuddy空值序列化行为一致，不据此认定服务新出现null转空串或放宽空串校验。当前报告未提供原始传输包，转换位置本次未独立重验。
- 成功apply使用action=abandon_new、上述model、expected_revision=0、inspect令牌、幂等键reconcile-abandon-20261019-03；job/recovery_id `2782a9e2b93f4ae98621add9d6ff8b5e`，succeeded/reconciliation_committed/revision=0，报告完成时间部分08:09:02.279000Z。success=true、saved_file_reloaded_and_verified=false、rollback_succeeded=false；放弃未执行保存重载或回滚，两个false不作为失败或对应动作验收通过。
- 后续creo_inspect_model返回abandoned/revision=0/adopted=false/part_file=null；对账保留recovery_id、action、original_job_id、original_plan_completion_confirmed=false及resolved_at。shell与regenerate均被Model is not ready保护拒绝。
- 会话total=1，仅原件WB_UNSAVED_03仍当前、origin空、modified=true、model_id=null；受管副本已从会话移除。放弃、后续编辑保护与原件保留有公开通过报告。磁盘快照文件仍保留及完整审计文件内容未在本段通过公开接口证明，不从会话移除推断文件删除或保留。

关闭原件、外部clean/dirty/钣金、拒绝矩阵、快照改写拒绝、真实多页与实际并发等仍待完成。FEAT-042/043继续验收中；prepare的adopted语义问题仍待统一，运行源码本轮尚未更改。

## 同日后续：外部clean与钣金素材已保存

开发者通过Creo12.4 UI将当前WB_UNSAVED_03保存独立副本为WB_EXT_CLEAN；原件未执行保存、改名或擦除。副本保存到工程目录外 `E:\CreoAcceptance\2026-10-19\wb_ext_clean.prt.1`，再通过文件打开载入；Creo体积工具实际测得 **6000.00 mm³**。未执行MCP创建或纳管，后续由WorkBuddy核对origin、modified与受管关联后执行已有文件inspect→apply。

另经UI新建独立钣金件WB_EXT_SHEET，选择 `mmns_part_sheetmetal_abs` 模板，FRONT草绘40.00×30.00 mm矩形，以钣金平面壁生成厚度2.00 mm基板；体积工具实际测得 **2400.00 mm³**。保存到 `E:\CreoAcceptance\2026-10-19\wb_ext_sheet.prt.1`。没有使用MCP建模/接管，不据模板及GUI状态代替公开接口的类型、健康、毫米与依赖检查。

文件只读核验（开发者证据，不属于WorkBuddy黑盒）：clean为86171字节、SHA256 `8d4429d73fe721e5bf62df97a0efef15a9b4588310731d5eec9b19183cd18ba7`；sheet为119555字节、SHA256 `1ca82d8106fdf347ba7a1cf186c2a9ce5ad0d714c2a0e3b1594be74c0553f2d2`。时钟核对为2026-10-19 08:26:30 UTC（北京时间16:26:30）。两份PRT均在仓库外，不加入提交；已有未跟踪examples/wb_unsaved_03.prt.1保留原样，不纳入交付。

收起测量浮窗后以WB_EXT_CLEAN为当前模型。外部clean、钣金接管本轮尚无WorkBuddy执行结果；dirty尺寸/参数/新增特征素材尚未制作，不能声明对应矩阵通过。
