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
