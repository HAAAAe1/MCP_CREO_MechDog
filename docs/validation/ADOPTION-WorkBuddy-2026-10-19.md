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

## 同日后续：外部clean接管通过

用户转贴WorkBuddy公开MCP报告：接管前WB_EXT_CLEAN当前、origin为 `E:\CreoAcceptance\2026-10-19\wb_ext_clean.prt.1`、has_saved_origin=true、modified=false（query_codes.modified=0）、model_id/adopted_copy_model_id均null、session_model_id=524290；同会话另有无盘WB_UNSAVED_03和已保存sheetmetal WB_EXT_SHEET，total=3。

inspect返回available=true、adopt_pending、source_kind=file、model `d573a11f766c4679aae4e46858b8e803`，文件86171字节，SHA256 `8d4429d73fe721e5bf62df97a0efef15a9b4588310731d5eec9b19183cd18ba7`；当前来源体积5999.999999999999 mm³、8特征/6面/12边，毫米/无依赖/健康均true，默认副本名adopt_d573a11f、令牌600秒。此时会话枚举model_id仍null：inspect创建待确认登记不证明原件已受管，不能用该登记ID直接编辑原件；apply后需分别检查副本model_id与原件adopted_copy_model_id。

apply输入为mode=apply、上述model及inspect令牌、model_name=wb_ext_copy_01、idempotency_key=adopt-apply-clean-20261019；job `0f9f80e854024e90befc5695334abfcf`，adoption_committed/revision=1，完成 `2026-10-19T08:30:39.713191Z`。后续检查副本ready/revision=1/adopted=true/source_kind=file，体积5999.999999999999 mm³、8特征/6面/12边/1实体，saved_file_reloaded_and_verified=true、inspection_source=adoption_verified、snapshot.source=saved_verified。保存路径为models下本model的output/wb_ext_copy_01.prt.1，SHA256 `afcc1b944f542645c009b80de3ccca727143b7d1445c8e10afe11d2f2f8034e9`；独立副本重新保存后的哈希无需等于来源文件。

原件WB_EXT_CLEAN仍在会话、origin不变、modified=false、model_id=null，adopted_copy_model_id指向上述model；窗口切到WB_EXT_COPY_01，total=4。外部clean接管、保存重载、原件保留和来源/副本关联有通过报告。WorkBuddy未取得接管后独立读取源文件哈希的公开证据，其“源文件字节未变”仍记未验证，不以任务消息中的未修改声明代替核验。

开发者随后只读Get-FileHash复核源文件：86171字节、SHA256仍为 `8d4429d73fe721e5bf62df97a0efef15a9b4588310731d5eec9b19183cd18ba7`，与准备素材时及WorkBuddy inspect时一致；核对时钟2026-10-19 08:32:57 UTC（北京时间16:32:57）。这补充开发者的磁盘前后字节一致证据，单独记录，不将其归入WorkBuddy公开MCP验收。未修改原件、重试接管或创建新登记。

钣金、dirty尺寸/参数/新特征、关闭原件、拒绝/分页/真实并发等剩余矩阵继续未验证，FEAT-042/043保持验收中。

开发者随后仅通过Creo UI激活已有WB_EXT_SHEET窗口；窗口清单明确显示 `WB_EXT_SHEET (启用的)`，未保存、编辑或纳管该件。后续WorkBuddy应重新枚举确认当前来源为外部wb_ext_sheet.prt.1、sheetmetal、modified=false且无受管关联，再执行已有文件inspect→apply，核对40×30×2/2400 mm³、ready/revision1、保存重载与原件保留。钣金接管结果尚未取得。

## 同日后续：外部钣金接管通过

用户转贴WorkBuddy公开MCP报告：WB_EXT_SHEET为当前sheetmetal，来源 `E:\CreoAcceptance\2026-10-19\wb_ext_sheet.prt.1`、has_saved_origin=true、modified=false/query_codes.modified=0、model_id与adopted_copy_model_id均null，session_model_id=3145729。会话total=4，session_fingerprint=9090761655684717328，另有WB_UNSAVED_03、WB_EXT_CLEAN及WB_EXT_COPY_01。

- inspect完整输入为 `{"mode":"inspect"}`，返回available=true、adopt_pending、source_kind=file；model `ec76df179b254f688c79acf85f858d91`、default_model_name=adopt_ec76df17、600秒令牌。来源119555字节、SHA256 `1ca82d8106fdf347ba7a1cf186c2a9ce5ad0d714c2a0e3b1594be74c0553f2d2`。当前摘要为sheetmetal、2400.0 mm³、8特征/6面/12边/1实体，has_solid/healthy/millimeter_units/dependency_free均true。
- apply输入为 `{"mode":"apply","model_id":"ec76df179b254f688c79acf85f858d91","evidence_token":"75a56a735aac48daa8777df31c0f4258","model_name":"wb_ext_sheet_copy_01","idempotency_key":"adopt-apply-sheet-20261019"}`。job `f5d28fad3c7f4aa787ed8ef3a9572bfe`，报告时刻部分created_at=08:37:44.614Z、finished_at=08:37:52.330Z；阶段intent_persisted→connect→adoption_save_and_reload→adoption_committed，终态succeeded、revision=1、adopted=true、connected=true。rollback_succeeded=false，未触发回滚，不作为回滚失败或通过的证据。
- 后续副本ready/revision=1/adopted=true/source_kind=file、pending_job=null；体积2400.0 mm³、8特征/6面/12边/1实体、has_solid=true、units=mm。saved_file_reloaded_and_verified=true、inspection_source=adoption_verified、snapshot.source=saved_verified。文件models下本model的output/wb_ext_sheet_copy_01.prt.1，SHA256 `d241ee7f763e6b0da72a1c64aae5058fb5fd8e059ee3d255faab289c3a894d87`；副本重新保存不要求与来源字节相同。
- 原件仍在会话、origin不变、modified=false、model_id=null，adopted_copy_model_id指向上述model；副本为当前，total=5、fingerprint未变。外部独立钣金的接管、几何摘要、保存重载、登记与原件关联通过；未验证其他钣金特征或展开行为。

WorkBuddy还报告section=sheets返回unavailable_sections:["sheets"]、data.sheets=[]，features中type=942的特征标为other。此处保留其观察，但纠正段名解释：开发者静态核对native/drawing.cpp的drawing_inspection，sheets由ProDrawingSheetsCount/SheetSizeGet/SheetNameGet生成，是工程图图纸页；不是钣金壁、折弯或展开表。该段在钣金零件上不可用不能作为钣金缺陷。type=942的名称映射及钣金专有语义未从本报告证明，不从总体计数一致推断逐项一致；本轮未新增或扩大支持声明。

WorkBuddy未独立取得接管后源文件哈希，其源字节不变仍记未验证。开发者随后只读核对磁盘源文件仍为119555字节、SHA256 `1ca82d8106fdf347ba7a1cf186c2a9ce5ad0d714c2a0e3b1594be74c0553f2d2`，与素材准备及inspect一致；文件核对在2026-10-19 08:42:14 UTC时钟读数之前完成。该证据单列为开发者结果，不计入WorkBuddy结论。

## 同日后续：dirty独立基线已保存，界面覆盖阻断修改

开发者通过Creo UI从WB_UNSAVED_03保存独立副本WB_EXT_DIRTY，路径 `E:\CreoAcceptance\2026-10-19\wb_ext_dirty.prt.1`；原件没有保存、改名或擦除。磁盘基线86408字节、SHA256 `0c90ff2e18f39a9ca5cf87a40f67c34f928be28ef7690294093a71adef7b5a24`，复制来源为此前30×20×10/约6000 mm³素材。本段尚未重新打开dirty副本或独立测量其磁盘重载体积，不把来源体积当作本段重载断言。

准备打开副本时桌面出现QQ截图/取色覆盖层，输入定位明确返回 `point (189, 31) is over QQ.exe "Chrome Legacy Window", not target window xtop.exe "WB_UNSAVED_03 (启用的) - Creo Parametric 12"`。重新获取Creo窗口、激活并重试一次后仍被同一覆盖窗口拒绝，随后停止UI输入；未操作远程协助控件、结束进程或建立Toolkit连接。dirty尺寸、参数和新特征修改均尚未完成，不能交给WorkBuddy作为合格dirty素材。待覆盖层退出后继续打开该独立副本、完成改动并保持未保存。

当前尚未完成dirty尺寸/参数/新特征、关闭原件、拒绝矩阵、快照改写拒绝、真实多页与实际并发等；FEAT-042/043保持验收中。准备顶层adopted的pending语义仍待统一，运行源码和构建产物本轮未改变。

## 同日后续：dirty几何修改完成，参数确认前桌面控制中断

用户确认已退出QQ浮层后，开发者重新取得Creo当前窗口，通过文件打开载入独立外部WB_EXT_DIRTY。UI核对原草绘为30.00×20.00 mm，将宽度30.00改为35.00 mm并完成编辑、再生；原实体拉伸未修改。随后在FRONT新建草绘2：边长5.00 mm的等边矩形，横向偏移8.00 mm、纵向偏移6.00 mm；完成后创建拉伸2，Creo自动切换为移除材料，明确设置深度10.00 mm并确认。UI出现贯通方孔，模型树保留草绘2及拉伸2。按这些设置，预期体积35×20×10−5×5×10=6750 mm³；本轮尚未通过体积工具实测，不能把计算值记作实测或MCP验收结果。

开发者进入工具→参数，范围明确为零件WB_EXT_DIRTY；新增实数参数WB_DIRTY_CHECK，在数值编辑框最终填入42。参数值使用Home、Shift+End选择全文后替换，未将早先追加输入的中间值当作终值。离开该单元格的Tab操作返回failed to activate captured window；重新枚举仍有参数窗口，重新获取并激活一次后返回 `GetCursorPos failed: 拒绝访问。 (0x80070005)`，遂停止UI输入。尚未点击参数窗口确定，参数是否已提交不能确认；未测量最终体积，未执行保存、关闭或接管。保留现场待用户恢复可操作前台窗口。

中断后只读磁盘复核：wb_ext_dirty.prt.1仍86408字节、SHA256 `0c90ff2e18f39a9ca5cf87a40f67c34f928be28ef7690294093a71adef7b5a24`，与保存基线一致；时钟核对为2026-10-19 09:03:12 UTC（北京时间17:03:12）。已完成几何修改仍是来源会话的未保存变化，不能把磁盘不变当作副本复制语义通过。下一步先确认参数提交、实际测量体积、清理模态窗口并保持WB_EXT_DIRTY当前，再交由WorkBuddy重新枚举并独立执行dirty接管。

## 同日后续：dirty素材三项修改核对完成

用户确认已在参数窗口点击确定后，开发者重新激活WB_EXT_DIRTY，打开零件级参数对话框复核，并展开名称列：完整名称明确为 `WB_DIRTY_CHECK`、类型实数、值 **42.0**。退出参数对话框后恢复三维视图，实体方形通孔可见；通过分析→测量→体积实际读到 **6750.00 mm³**，与35×20×10减5×5×10相符。测量浮窗已关闭，来源WB_EXT_DIRTY仍为当前模型，无模态窗口；本轮没有执行模型保存、关闭或MCP接管。

本轮界面准备已具备三项明确变化：原草绘宽30→35 mm，新增零件参数WB_DIRTY_CHECK=42.0，新增草绘2及拉伸2形成X=8..13/Y=6..11/Z=0..10 mm方形通孔。外部磁盘基线仍为86408字节、最后写入时间北京时间16:40:55、SHA256 `0c90ff2e18f39a9ca5cf87a40f67c34f928be28ef7690294093a71adef7b5a24`，没有变化；只读核对后时钟2026-10-19 09:07:58 UTC（北京时间17:07:58）。此为开发者UI与磁盘证据，不是dirty接管通过结果。

交接WorkBuddy：先通过公开枚举确认当前WB_EXT_DIRTY、来源为上述外部prt.1、has_saved_origin=true、modified=true且没有受管关联，再执行已有文件inspect→apply；副本使用独立名称wb_ext_dirty_copy_01和新幂等键，只轮询已接受任务。确认副本保存重载verified、ready/revision1、体积6750±0.01，并通过公开详情逐项核对35×20×10、5×5通孔及参数42.0；接口无法暴露的原件/副本细项明确记未验证，不能仅凭特征数判定全部变化已复制。原件应保留来源路径与modified=true。尚未取得本次dirty的WorkBuddy任务/模型及终态，相关验收状态保持不变。

## 同日后续：dirty尺寸、参数和新特征接管通过

用户转贴WorkBuddy报告：WB_EXT_DIRTY为当前part，origin为 `E:\CreoAcceptance\2026-10-19\wb_ext_dirty.prt.1`、has_saved_origin=true、modified=true、无受管关联，session_model_id=524293；total=6、session_fingerprint=9090761655684717328。query_codes.modified=0为查询成功状态码，不能代替modified布尔值，亦不能由该码推断未修改。

- inspect完整输入 `{"mode":"inspect"}`，返回model `6343b3f7640746f4b2c1bfa209bd8a63`、adopt_pending/source_kind=file/available=true、600秒令牌；磁盘来源86408字节、SHA256 `0c90ff2e18f39a9ca5cf87a40f67c34f928be28ef7690294093a71adef7b5a24`。活体体积6749.999999999997 mm³、12特征/10面/24边/1实体，has_solid/healthy/millimeter_units/dependency_free均true。
- apply完整输入 `{"mode":"apply","model_id":"6343b3f7640746f4b2c1bfa209bd8a63","evidence_token":"871c74a2728745cf8fa68cd1ad56fb03","model_name":"wb_ext_dirty_copy_01","idempotency_key":"adopt-apply-dirty-20261019"}`，只轮询返回的job `e0e83eb085344eba81fc521853c974e2`。报告时刻部分created_at=09:13:12.464Z、finished_at=09:13:21.340Z；intent_persisted→connect→adoption_apply→adoption_committed，succeeded/revision=1/adopted=true。rollback_succeeded=false，未触发回滚。副本models下本model的output/wb_ext_dirty_copy_01.prt.1，SHA256 `e5a22ef6393040a1baf9542be82ddcbc9bf0d9b129d874ede68c1bdda853efa4`。
- 副本后续ready/revision=1、pending_job=null；saved_file_reloaded_and_verified=true、inspection_source=adoption_verified、snapshot.source=saved_verified，体积6749.999999999997 mm³，符合6750±0.01。

| 未保存修改 | 副本公开检查证据 | 判定 |
| --- | --- | --- |
| 原草绘宽度30→35 mm | sketch40 d1=35.0、protrusion48 d4=35.0、bbox x=0..35；另有sketch40 d0=20.0、protrusion48 d3=20.0，深度d2=10.0，bbox y=0..20/z=0..10 | 尺寸通过 |
| 新增5×5贯穿方孔 | cut84，d10=5.0、d11=6.0、d12=8.0、d9=10.0；草绘76只有一条边长5.0，另边由等长约束保证。10面均平面type=34，四孔壁分别位于x=8/13、y=6/11，z=0..10 | 方孔及贯穿几何通过；d10称边长，不称圆孔孔径 |
| 新增零件参数 | WB_DIRTY_CHECK，type=50、value=42.0 | 参数通过 |

特征/面/边为12/10/24，与来源inspect摘要一致；通过依据还包括上述尺寸、参数、平面位置和深度，未仅凭特征数量或体积相同推断复制正确。

原件WB_EXT_DIRTY仍在、非当前、origin不变、modified=true，adopted_copy_model_id指向上述model；副本WB_EXT_DIRTY_COPY_01成为当前、modified=false、model_id指向该登记，total=7、fingerprint未变。来源未保存修改被副本捕获、保存重载和原件关联有公开通过报告。末态modified=true证明检查时仍有未保存修改，单凭该标志不能独立证明中途从未保存。

WorkBuddy未通过公开接口独立重载源磁盘几何或再次读取源哈希，这两项继续未验证。开发者接管后另只读复核外部源文件仍86408字节、最后写入北京时间16:40:55、SHA256仍为 `0c90ff2e18f39a9ca5cf87a40f67c34f928be28ef7690294093a71adef7b5a24`，与修改前基线和inspect一致；核对时间晚于2026-10-19 09:15:38 UTC时钟读数。此为独立开发者文件证据，不并入WorkBuddy结论。没有为比较而关闭/重载仍dirty的原件。

来源矩阵的从未保存、外部clean、含未保存尺寸/参数/新特征的file来源及独立平板钣金均已有本机公开通过报告。关闭来源、拒绝类型/非毫米/外部依赖/不健康、快照改写拒绝、真实多页与实际并发等仍待补；FEAT-042/043继续验收中，prepare顶层adopted语义尚未修正。本轮继续只操作UI素材与文档，不修改运行源码、执行器或清除保护。

## 同日后续：装配与非毫米拒绝素材就绪

开发者通过Creo12.4 UI新建WB_REJECT_ASM，类型装配/设计，明确选择mmns_asm_design_abs模板；保留模板的三基准面与坐标系，不含组件。保存为外部文件 `E:\CreoAcceptance\2026-10-19\wb_reject_asm.asm.1`。此为空装配的类型拒绝素材，不用于证明装配纳管、装配几何或依赖处理能力。

另通过UI新建实体零件WB_REJECT_INCH，明确使用inlbs_part_solid_abs模板，FRONT草绘为边长1.00的等边矩形，实体拉伸深度1.00；体积工具实际读到 **1.00000 in³**。保存为 `E:\CreoAcceptance\2026-10-19\wb_reject_inch.prt.1`，收起测量浮窗。该素材有正常实体，后续公开预检仍须独立确认单位、健康及依赖，不能仅以模板名称代替拒绝结果。

保存后只读核验、时钟2026-10-19 09:40:03 UTC（北京时间17:40:03）：

| 文件 | 字节数 | SHA256 |
| --- | --- | --- |
| wb_reject_asm.asm.1 | 64737 | 20cbfe112c1cdf816fa55f59f25eb4387606ddc6442aeb07c62a6035526052f4 |
| wb_reject_inch.prt.1 | 92401 | 02dadb769a8caf248f1064d49d86fd44f988b6566405f569f6a91371b09504b4 |

开发者随后仅激活WB_REJECT_ASM窗口作为当前模型，未执行任何MCP接管或拒绝探测；两份素材均在同一会话，既有dirty来源和受管副本未关闭或改写。先交WorkBuddy通过公开接口枚举/inspect装配，预期明确拒绝、不返回可确认ID/令牌、不产生新受管登记或副本；回报后再切到WB_REJECT_INCH验证非毫米拒绝。真实多页枚举可在当前多模型会话独立补测，不能把session_model_id当成可操作目标或自动切窗能力。

本轮重新核对BUG-001-recovery-2026-10-17历史卡死记录，连接-11根因仍未由本次材料证明；既有用户确认可操作及后续正常UI/MCP结果不等同根因关闭。开发者未建立新的Toolkit连接或故意制造再生失败，外部依赖与不健康模型拒绝仍待合格素材及相应安全条件，不将装配/英寸素材准备视作第8步通过。

## 同日后续：装配拒绝与真实五页遍历通过

用户转贴WorkBuddy报告：WB_REJECT_ASM为当前assembly，来源 `E:\CreoAcceptance\2026-10-19\wb_reject_asm.asm.1`、has_saved_origin=true、modified=false、无model_id/adopted_copy_model_id，session_model_id=524288；会话total=9、session_fingerprint=9090761655684717328。WB_REJECT_INCH亦在同一会话。

受管列表基线调用 `creo_list_models({"detail":"compact","limit":50})`，因响应分页返回25条、complete=false、next_cursor非空；报告记录快照哈希前缀4989131a…，首项为wb_ext_dirty_copy_01（model前缀6343b3f7…、ready/revision1）。报告该登记created_at时间部分09:13:01，与前文apply任务created_at=09:13:12.464Z是不同对象时间，不强行视为冲突。未取得本次受管列表的后续页或完整哈希，不把首页25条作为登记总量。

接管inspect完整输入 `{"mode":"inspect"}`，工具级错误原文：

```text
Error executing tool creo_adopt_current_model: Adoption refused: only part or
sheetmetal models can be adopted; assemblies and drawings keep their own ownership
```

未返回model_id、evidence_token、available_modes或job；WorkBuddy未继续apply或其他写操作。拒绝后会话仍9个模型，当前仍WB_REJECT_ASM、来源及空受管关联未变、fingerprint一致；受管列表首项及报告中的快照哈希前缀亦未变。装配类型明确拒绝、未观察到新接管登记/副本或窗口切换，通过；这不等同已经执行装配apply、工程图拒绝或完整登记文件审计。

随后WorkBuddy以limit=2和每页返回的cursor遍历同次会话快照，报告如下：

| 页/offset | 模型（报告顺序） | snapshot_id | next_cursor |
| --- | --- | --- | --- |
| 1/0 | WB_UNSAVED_03、WB_EXT_SHEET | 1eb62765… | 有 |
| 2/2 | WB_EXT_CLEAN、WB_EXT_COPY_01 | 同上 | 有 |
| 3/4 | WB_EXT_SHEET_COPY_01、WB_EXT_DIRTY | 同上 | 有 |
| 4/6 | WB_EXT_DIRTY_COPY_01、WB_REJECT_INCH | 同上 | 有 |
| 5/8 | WB_REJECT_ASM | 同上 | null |

合计9条，与total=9及先前limit=20的完整名称顺序一致，无重复遗漏；5页snapshot_id相同、checked_at时间部分均09:46:03.035290，末页当前标记仍为WB_REJECT_ASM。真实同快照多页、末页终止及未切窗通过；snapshot_id仅有前缀，不补造完整值。该会话同时覆盖无盘、clean、dirty、sheetmetal、assembly和受管副本；未知值查询失败、其他类型及实际并发仍不由本段外推。

### 接口观察归类

1. 装配拒绝仅有工具级文本，无code/reason结构化字段：记录为[FEAT-008](../work-items/FEAT-008.md)错误契约改进线索，尚未设计或修改统一错误格式，不把明确拒绝本身判失败。
2. session_model_id=524288同时出现在part WB_UNSAVED_03与assembly WB_REJECT_ASM：说明该字段不是全局唯一身份；沿用FEAT-043的临时发现提示边界。后续操作只以当前窗口正式预检及返回的受管ID为准，不根据该整数选择或接管模型，也不承诺组合键为永久身份。
3. assembly的query_codes缺subtype，而part/sheetmetal有subtype=0：开发者静态核对native/generic.cpp，确实只在PRO_MDL_PART分支调用ProMdlSubtypeGet、添加该诊断。因此字段集不同符合当前查询行为；缺失项不推断为失败或0，0表示已执行查询成功。该说明与WorkBuddy观察分列，不伪装为黑盒读取源码，不新增缺陷ID。

开发者随后仅通过Creo UI激活已有WB_REJECT_INCH窗口；未保存、编辑、接管或执行单位拒绝探测。当前单位拒绝待WorkBuddy重新枚举/inspect，装配及多页通过结果已取得；FEAT-042/043维持剩余范围的验收中状态，实际并发和其他拒绝分支不因本段成功而关闭。

## 同日后续：非毫米拒绝通过，单位摘要另记BUG-072

用户转贴WorkBuddy报告：WB_REJECT_INCH为当前part，来源 `E:\CreoAcceptance\2026-10-19\wb_reject_inch.prt.1`、has_saved_origin=true、modified=false、model_id/adopted_copy_model_id均null，session_model_id=524295；total=9、session_fingerprint=9090761655684717328。枚举不暴露单位信息，不能以名称或枚举单独证明英寸单位。

受管列表基线调用 `creo_list_models({"detail":"compact","limit":3})`，报告快照哈希前缀4989131a…、首项6343b3f7…（wb_ext_dirty_copy_01）、complete=false、cursor offset=3。接管inspect完整输入 `{"mode":"inspect"}`，本次正常返回结构化JSON：available=false、reason="Adoption requires millimeter model units"、available_modes=[]、conflict=null、model_id=null、evidence_token=null、source_kind=file；current_model.millimeter_units=false、healthy=true、dependency_free=true、feature_count=8。没有接管ID/令牌，WorkBuddy未继续prepare/apply或转换单位。

该载荷同时提供current_model.volume_mm3=0.9999999999999999、inspection.units="mm"、inspection.volume_mm3=0.9999999999999999、volume_query_code=0、has_solid=true、8特征/6面/12边/1实体。源文件92401字节、SHA256 `02dadb769a8caf248f1064d49d86fd44f988b6566405f569f6a91371b09504b4`。这些量纲字段互相矛盾，不能把约1当成已核验的mm³值；拒绝保护通过与摘要缺陷分开判断。

拒绝后报告受管列表快照哈希与cursor完全相同、会话仍9个模型、fingerprint不变；WB_REJECT_INCH来源/空受管关联不变、modified=false、仍当前。非毫米明确拒绝、没有观察到新副本/登记或窗口切换，通过；受管列表只读首页不等于全量枚举。WorkBuddy公开接口没有第二个独立模型级单位读数，确为英寸的黑盒独立交叉验证仍未完成。此前开发者通过UI选inlbs模板并实测1.00000 in³是另列的独立开发者证据，不改写WorkBuddy验证边界。

开发者静态定位native/generic.cpp：inspection()固定units="mm"、将SDK mp.volume直接填入volume_mm3；adopt_current_native另行查询主长度单位生成millimeter_units。现有源码不能支持“inspection读取会话或全局单位”的猜测。非毫米单位/体积误标新登记[BUG-072](../work-items/BUG-072.md)（P2待开发），修正量纲、可靠换算或null，保留非毫米拒绝；尚未修改运行源码或重编。装配抛工具级错误、非毫米返回结构化不可用的差异继续归[FEAT-008](../work-items/FEAT-008.md)契约改进；不是两个保护分支都失败。

## 同日后续：关联外部来源的拒绝素材就绪

开发者通过Creo12.4 UI新建WB_REJECT_DEP，明确使用mmns_part_solid_abs；模型→获取数据→合并/继承，选择外部参考，打开外部WB_EXT_CLEAN为源模型，采用默认坐标放置（完全约束），保留合并/添加主体与选项中的自动更新。提交后模型树出现“外部添加主体 标识40”，实体可见；体积工具实际读到 **6000.00 mm³**。没有修改来源WB_EXT_CLEAN，也没有使用MCP创建或预检。

保存为 `E:\CreoAcceptance\2026-10-19\wb_reject_dep.prt.1`，关闭测量浮窗后保持WB_REJECT_DEP为当前。只读核对文件85207字节、SHA256 `c2eaa0ccf12d381499050878aef8ec9bef88cd49590343296243632ca4343888`；被引用clean源哈希仍 `8d4429d73fe721e5bf62df97a0efef15a9b4588310731d5eec9b19183cd18ba7`，核对时钟2026-10-19 10:07:29 UTC（北京时间18:07:29）。本段证明UI关联方式和素材状态，不代替公开接口dependency_free=false及拒绝行为的验收。

交接WorkBuddy重新枚举并做只读inspect，核对part/mm/healthy及dependency_free=false、明确外部依赖拒绝、无ID/令牌/登记/副本。若公开检查意外可接管则报告与UI关联矛盾，不执行apply或解除保护。外部依赖、不健康、实际并发仍待结果；原件关闭/快照改写及字段修正复验仍未完成，FEAT-042/043保持验收中。
