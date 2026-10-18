# FEAT-042 受管副本接管实机验证（2026-10-18）

来源：[0.3.7 / Creo 13 反馈](FEEDBACK-0.3.7-CREO13-2026-10-18.md)问题 2；[任务卡](../work-items/FEAT-042.md)。

## 环境

- Windows x64；Creo Parametric 12.4.0.0（release_numeric=44）、匹配 Toolkit SDK 与许可；Toolkit 会话由既有后台协调器管理（本机 dev 联调约定）。
- 分支 `codex/bug-067-creo13-feedback`，基底提交 `1def478`（BUG-068/BUG-050 交付）+ 本次未提交改动（native/generic.cpp、src/creo_mechdog/adoption.py、bridge.py、server.py、capabilities.py、tests/unit/test_adoption.py、tools/test_adoption.py、三个工具数断言测试、文档）。
- 开发统一检查 `tools/dev_check.py` 通过（checked_source_sha256=70114af0d88998e2b731f5530fc0fa5eae2ce467e0fce56f6347ba4891de5a8d，为中途快照；提交号见交付记录）。

## 契约（用户 2026-10-18 确认）

受管副本：接管对象为 Creo 当前窗口模型（`ProMdlCurrentGet`）；apply 以 `ProMdlnameCopy` 复制当前会话状态为受管对象，保存到新 `models/<id>/output/`，erase/load/regenerate 后 `verify_recovery` 全量比对；用户磁盘原件与会话中原模型不修改、不擦除、不改名。首批独立 part + sheetmetal；mm 主单位、无外部依赖（`ProMdlDependenciesDataList` 为空）、无不健康特征；assembly/drawing/非 mm/带依赖明确拒绝。身份 = origin 路径 + 磁盘文件 sha256 + live inspection 全量结构 + 会话指纹；显示名乱码（[BUG-070](work-items/BUG-070.md) 形态，本次实机 current_model 为 `▩FEAT042_SEED_PART0001`）不影响身份判定。

## 工具协议

`creo_adopt_current_model`（85 个工具之一，capabilities family `model_adoption`）：

- `mode="inspect"`：只读探针，返回 `{available, reason, conflict, current_model{origin/model_type/healthy/feature_count/volume/摘要}, file{path,size,sha256}, model_id(adopt_pending), default_model_name, evidence_token}`；失败探针不残留半登记。
- `mode="apply"`：需 `model_id+evidence_token+idempotency_key`（可选 `model_name`），复核会话指纹/origin/磁盘哈希/live 全量快照后提交 kind=adoption job；成功模型 ready、revision=1；worker 已启动的失败按 unknown_outcome 保留 pending_job 保护，经 `creo_reconcile_model abandon_new` 收尾；同源重复接管 inspect/apply 双层拒绝并指向已有 model_id。

## 实机执行记录（tools/test_adoption.py --current）

准备：`creo_execute_plan` 建 Ø24×10 圆柱种子（job `b1ab3318624640adb1ff0326d1c70621`，保存后成为当前窗口模型）；移除其 model.json 登记（保留 output 文件与窗口）构成"已存在但登记不持有"的目标场景——与用户手动打开 001.prt 的所有权处境一致。第一轮对种子接管（受管名 feat042_adopted_current），第二轮对第一轮接管副本再接管（受管名 feat042_adopted_run2），验证记录以第二轮为主：

| 步骤 | 命令/断言 | 结果 |
| --- | --- | --- |
| inspect | origin=`…\output\feat042_adopted_current.prt.1`、type=part、features=8、volume=4523.893421169301、sha256 与磁盘一致 | 通过（job 内只读探针） |
| apply | job `62702c4e17f04c40ababb653b9804af1`，stage=adoption_committed，saved_file_reloaded_and_verified=true，revision=1 | 通过 |
| 会话状态复制 | 受管副本 counts.features=8 与 inspect feature_count=8 相等，体积逐位一致 | 通过 |
| 原件保护 | 原件 sha256 接管前后不变（脚本断言） | 通过 |
| 接管后编辑 | execute_plan 凸台（job `f00237c5f31f47709d813383eb52918a`）成功，revision=2，保存重载 verified | 通过 |
| 重复接管 | 同源再 inspect：available=false，conflict.reason=already_adopted 指向受管 model_id | 通过 |
| 第一轮对照 | 种子→feat042_adopted_current（job `0ed3d3e6d0774e71985febc3ebdaf48a`）同样 adoption_committed | 通过 |

第一轮 apply（job 0ed3d3e6）与第二轮（job 62702c4e）走同一 native 路径，互为重复性证据。

## 单测与回归

- `tests/unit/test_adoption.py` 9 用例（stdio MCP 协议 5：发布/两阶段/幂等重放/缺参拒绝/失败保护+abandon 可用；业务规则 4：过期证据/源文件变化/adopt_pending 下 submit 拒绝/不支持类型）全过。
- 全量单测 375 过；三处工具数断言 84→85 同步（test_callback_admission/test_reference_contract/test_update_check）。
- `tools/dev_check.py` 通过（无新增语言问题；native/generic.cpp clang-format 干净）。
- 原生回归 `tools/test_general.py`：GENERAL_CORE_SUCCESS=1（含 plate 保存重载验证用例）；`tools/test_sketch_stability.py`：PUBLIC_COORDINATES_PASS（8 用例含 BUG-068/BUG-050 回归）。本次 native 改动仅新增 adopt_native 分支与 dependency_free 参数化，未触碰既有操作路径，回归确认无破坏。

## 未测范围

- **未保存修改的复制语义**：实机两轮接管对象均为已保存状态；`ProMdlnameCopy` 是否携带未保存修改未实证（需人工在 Creo 修改不保存后接管）。契约表述为"复制当前会话状态"，若实证仅复制磁盘态，需按结果修订文档描述。
- **sheetmetal 实机接管**：类型判定（model_type=sheetmetal）与拒绝路径由单测覆盖；实机未打开未登记钣金模型执行接管。
- **Creo 13.4.1.0 外部环境**：反馈源环境未测；本机 12.4 通过不能外推。
- **用户目录原件场景**：实机接管的 origin 位于本仓 models 树下（登记已移除）；外部磁盘路径（如 D:\PTC 场景）的路径解析/哈希逻辑相同但未实测。尝试以 shell 关联自动打开外部副本时会拉起第二个 Creo 实例（本次误启后已清理，未影响既有会话），交互式运行 `tools/test_adoption.py`（不带 --current）时该步骤仍需人工在既有会话内打开。
- WorkBuddy 黑盒验收未执行（MCP 公开接口流程与上述一致，另行留证）。

## 交付

提交于 `codex/bug-067-creo13-feedback`（提交号见 git log，标题 FEAT-042：creo_adopt_current_model 受管副本接管当前会话模型）；未合 main、未发版。
