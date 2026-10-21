# 0.4.1 版本说明

发布日期：2026-10-19。版本类型：PATCH（用户 2026-10-19 明确指定；包含新增公开工具与无盘接管能力，按约定本应为 MINOR，遵用户指定作为本次例外，见 [RELEASING](development/RELEASING.md) 版本约定）。工具数 85 → **86**（新增 `creo_list_session_models`）。

来源：0.4.0 后开发分支"现有模型纳管完善"批次（FEAT-042 第二阶段、FEAT-043、FEAT-022）与两项缺陷修复（BUG-072、BUG-073）；外部 WorkBuddy 黑盒反馈闭环。

## 变更内容

- **FEAT-042 第二阶段：无盘快照接管（`creo_adopt_current_model` 新增 prepare 模式）**：从未保存的当前模型显式 `prepare → apply` 冻结受管快照——prepare 以幂等键在一次原生事务中复制当前模型并保存/重载核验，返回独立 job/model、`adopt_pending`/revision=0 与 600 秒 evidence_token，任务顶层 `result.adopted=false`；apply 确认后 `ready`/revision=1、`adopted=true`，此后原模型后续编辑不进入快照。令牌过期经 `inspect(model_id=…)` 续签（不重复制）；放弃走 `creo_reconcile_model abandon_new`。已有文件模型仍用 `inspect → apply`。原件不保存、不改名、不擦除、不切窗。
- **FEAT-043 `creo_list_session_models`（新工具）**：只读会话模型枚举——名称/类型/origin/has_saved_origin/modified/当前窗口、固定分页（32 KiB 页/limit≤50/cursor）、未知字段显式 null、`adopted_copy_model_id` 受管关联；发现身份仅提示，不自动激活或接管。
- **FEAT-022（部分）**：工具描述、README/安装与接管入口补连接器重启与部署核对指引（`source_changed_since_startup`、启动指纹清单、`native/inspection_units.h` 纳入指纹）。
- **BUG-072**：非毫米来源摘要诚实化——原生长度单位查询（`inspection.units` 为实际单位名或 null、新增 `units_query_code` 诊断）；仅确认 mm 且数值有限时填写 `volume_mm3`，英寸/其他/未知单位为 null，不做未经验证换算；非毫米准入拒绝保持且无 ID/令牌。
- **BUG-073**：`creo_extrude`/`creo_revolve`/`set_sketch_dimensions`/`sheetmetal_wall`/`surface_fill`/`rib` 的 `sketch` 引用统一规范化——纯数字串按特征 ID 解析（与 `creo_loft` 契约一致，兼容客户端对 anyOf 整数分支加引号）；标签查找大小写不敏感回退（`inspect_model(features)` 返回的 Creo 大写特征名可直接引用）；查找失败错误信息列出可用标签候选；顺带修复大写引用在执行段对 null 别名调 `.value()` 的崩溃。

## 验收摘要

本机 Windows x64 / Creo 12.4.0.0 / 匹配 SDK 与许可。全量单测 **411 项**通过（新增 test_sketch_references 5 例、test_adoption/test_model_queries 扩充）、`tools/dev_check.py --work-item BUG-073` 通过、匹配 12.4 SDK 构建通过。实机：无盘 prepare/apply 字段链（`adopted=false`→`true`、快照冻结哈希一致、副本续作 24000 mm³/revision2、原件无盘保留）；英寸拒绝载荷（`units="in"`、双层 `volume_mm3=null`）；BUG-073 四种 sketch 写法（自建+受管模型）与错误候选、回滚。WorkBuddy 黑盒：无盘续作主链、过期拒绝/续签/冻结副本、放弃保护、外部 clean/dirty/钣金接管、装配/非毫米/依赖/抑制特征拒绝、9 模型/5 页遍历、prepare/apply 字段（本轮 BUG-073 复验含四写法/候选/重复标签/受管对照）。逐项证据见 [validation/ADOPTION-WorkBuddy-2026-10-19.md](validation/ADOPTION-WorkBuddy-2026-10-19.md) 与 [BUG-073](work-items/BUG-073.md)。

## 已知问题与未测范围

- FEAT-042/043/022 保持验收中：关闭原件后确认、真实再生失败、真实并发（仅有 busy 旁证）、快照改写拒绝、钣金专有语义（`sheets` 为工程图页）、外部 Creo 13 环境均未验证。
- BUG-072/FEAT-042 的英寸摘要与 prepare 字段已有开发者实机证据；WorkBuddy 对该两项的公开复验未单独执行（BUG-073 公开复验同轮已确认连接器部署身份与修正行为）。
- BUG-073：`creo_loft` 实机数字串对照未测（回调注册需人工前置；单测覆盖其规范化无回归）；`execute_plan` 内 extrude 数字串由 schema 层统一覆盖，未单独实机重跑。
- 开发过程一次 Toolkit 通道 -11（PRO_TK_COMM_ERROR）连接事故的定位与恢复已记录（Creo 停模态 Dashboard 叠加警告框循环；ESC 取消+关框+停重复实例恢复，未结束 Creo）；BUG-001 的 Creo 卡死根因未定结论不变。
- Creo 9 实机编译与建模运行时未验收（本机无 Creo 9 SDK）；Creo 10 独立复测按用户 2026-10-15 决定不作为门槛。

## 附件及 SHA256

见 [validation/RELEASE-0.4.1.md](validation/RELEASE-0.4.1.md) 与 Release 页面；附件由 `v0.4.1` 标签指向的 main 提交生成。
