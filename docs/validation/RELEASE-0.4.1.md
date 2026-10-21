# 0.4.1 发布候选与主干交付核对

日期：2026-10-19（Asia/Shanghai）。版本类型：PATCH（用户 2026-10-19 明确指定，含新增公开工具，按约定本应为 MINOR，作为本次例外）。工具数 85 → **86**。条目：FEAT-042 第二阶段（无盘快照接管 prepare/apply、adopted 字段语义、续签/放弃）、FEAT-043（`creo_list_session_models`）、FEAT-022（重启指引，部分）、BUG-072（非毫米摘要诚实化）、BUG-073（extrude 系草图引用规范化）。工作区在发版准备提交后保持干净，受测源码即合入 main 的提交。

## 本轮变更清单

- 代码（详见 [RELEASE_NOTES_0.4.1.md](../RELEASE_NOTES_0.4.1.md)）：native（generic.cpp adopt 第二阶段/inspection_units.h 单位查询/feature_id 规范化与 alias_entry、worker.cpp）；Python（adoption.py、model_queries.py、session_models.py、schema.py SketchRef、bridge/generic_bridge 分发、server.py 86 工具）；测试（test_adoption、test_model_queries、test_session_models、test_sketch_references 5 例、test_inspection_units 8 例）。
- 文档：README 版本段与标题、RELEASE_NOTES_0.4.1、RELEASING/INSTALL/ADOPTION 版本行、WORKBUDDY_ADOPTION 提示词、BACKLOG、任务卡（FEAT-042、BUG-072、BUG-073）、验证记录（ADOPTION-WorkBuddy-2026-10-19 三轮）。
- 种子链：两份 seed_manifest `compatible_server_version` → 0.4.1（字节级同步）；种子包重建；seeds.py expected_digest 同步（9 枚种子身份不变，仅清单版本标记）。

## 检查与实机证据（Windows x64 / Python 3.12.14 / Creo 12.4.0.0 / 匹配 SDK）

- `tools/dev_check.py --work-item BUG-073` 与 `--work-item RELEASE-0.4.1`：success=true；全量单测 **411 项** 0 失败 0 错误（版本 0.4.1）。
- `tools/test_general.py`：**GENERAL_CORE_SUCCESS=1**；`tools/test_adoption.py --current`：**ADOPTION_INTEGRATION_SUCCESS**（adoption/edit/save-reload/conflict refusal 全过）。
- 开发者实机：无盘 prepare/apply 字段链（任务级 adopted=false→true、冻结哈希一致、副本续作 24000 mm³/revision2、原件无盘保留）；英寸拒绝载荷（units="in"、双层 volume_mm3=null）；BUG-073 四种 sketch 写法（自建+受管）与错误候选/回滚。
- WorkBuddy 黑盒（同日三轮转贴）：无盘续作主链/过期拒绝/续签/冻结副本/放弃保护、外部 clean/dirty/钣金接管、装配/非毫米/依赖/抑制特征拒绝、9 模型/5 页遍历；BUG-073 公开复验（部署身份、四写法、候选标签、重复标签保护、受管对照）全部通过。
- 打包：源码包 638 文件、种子包 24 文件；解压核验 README 标题/version.py 0.4.1/adoption.py/seeds digest/RELEASE_NOTES/manifest 版本一致。

## 附件与发布

- 合入 main 提交：`0cdc250`（fast-forward 自 `codex/feat-042-adoption-completion`，0ed68f4..0cdc250，远端已推送）。
- v0.4.1 标签指向：`0cdc250`（远端 `git ls-remote` 核对 main 与 tag 同指）。
- Release 链接：https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.4.1（Pre-release 非草稿，id 417461624）。
- 源码包 SHA256：`c1ef110462ec0e20818431dc8945411f39d12f9a8d2f66ce4052e65a7c528bcc`（638 文件；远端下载核对一致）。
- 种子包 SHA256：`68da44c3a3b089b922b7920b43de19943181b7e2cde990f1e19ad30cd7ad1148`（24 文件，9 枚种子身份不变；与 seeds.py expected_digest 一致，远端下载核对一致）。

## 未测范围

FEAT-042/043/022 保持验收中：关闭原件后确认、真实再生失败、真实并发、快照改写拒绝、钣金专有语义、外部 Creo 13 环境未验；BUG-072/FEAT-042 字段修正的 WorkBuddy 单独公开复验未执行（BUG-073 同轮已确认部署身份与修正行为）。BUG-073：实机 loft 数字串对照未测（单测覆盖无回归）。开发过程一次 Toolkit -11 通道事故（Creo 停模态叠加警告框循环）已记录恢复过程；BUG-001 卡死根因未定结论不变。Creo 9 实机未验收（无 SDK）；Creo 10 独立复测按用户决定不作为门槛。

本回填段随交付即时提交入 main，不改变标签所指源码与附件（仅文档回填，0.4.0 先例）。
