# 0.3.1主干合入准备记录

条目：[DEV-015](../work-items/DEV-015.md)。日期：2026-10-15。服务/源码0.3.1；本任务范围为版本同步、检查及通过PR合入main，GitHub Release、标签和附件上传独立记录。

## 范围与来源

从`codex/p1-modeling-repair`的`559f52d377d06a12f11af423d53b3fd543a3bb86`建立干净托管工作区及`codex/release-031`，保留主工作区未提交文档。原工作区未登记的DEV-014、其他条目文档、运行数据不混入本次版本提交。

用户明确确认0.3.1最小补丁版本及[改动说明](../RELEASE_NOTES_0.3.1.md)，包括默认摘要的调用迁移。本次不修改原生建模实现；原生源码指纹与此前专项证据核对，保持原受测0.3.0、日期、commit/dirty身份，不将其改标为本轮全量原生发布回归。

## 检查

详细命令、实际源码指纹、commit/dirty、环境和结果见[结构化记录](RELEASE-0.3.1.json)。检查在559f52d、dirty=true下实施，不能用之后提交号替代实际指纹；新目录解压来源不继承父目录Git身份。

- Windows/Python3.12.14独立虚拟环境与锁定依赖：`tools/dev_check.py --work-item DEV-015`，191项通过。现存Ruff诊断55、未格式化文件38仍按基线保留，无新增问题、未重建基线。
- 源码预检ZIP的252个文件白名单、CRC、版本入口检查通过，未带本机配置、运行模型/作业、虚拟环境、SDK或执行器二进制。预检ZIP在验证记录补齐前生成，SHA仅代表当次预检包，不冒充后续文档提交的完整归档。
- 新目录解压后创建独立虚拟环境、按requirements-dev安装editable包，再执行191项开发/单元检查通过。
- 新目录真实stdio调用capabilities、list_seeds和list_models通过；版本0.3.1、代码根指向解压目录、source_changed_since_startup=false、九种子可用。该目录未配置Creo；启动状态为配置未就绪，不把元数据/协议检查称作Toolkit连接或建模通过。
- 两份种子清单完全一致且兼容版本0.3.1；九个原PRT指纹逐项验证。独立ZIP真实安装到隔离测试目录并注册验证通过，配套清单和MIT许可同时保留。
- 新种子ZIP SHA256=`7d0e722e2fac144b4df6e8bdf7479f693c9e8eed575b3dd59fb5a45ada9bc10b`，已同步seeds.py校验值。旧版本ZIP及标签未覆盖。
- 相对559f52d所有native文件无变更；generic.cpp归一化SHA256=`72bb9c87518edd8f6a05851d69ce322a47133578609998c4b4fe90b132fcfe97`，与BUG-022已验收实现一致。原生43作业与WorkBuddy补测继续按受测0.3.0/原日期引用，没有重新运行0.3.1完整原生发布套件。

准备检查已完成，主干合入通过PR实施，是否已合入以PR实际状态及远端main为准。本记录不提前宣称已生成v0.3.1标签或GitHub Release。

## 原生与最终黑盒边界

BUG-007核心、P1联合开发及BUG-022追加证据分别保留。[BUG-022 WorkBuddy最终补测](BUG-022-WorkBuddy-retest-20261015.md)由用户确认四场景通过。Creo10原始问题、BUG-028计划入口部分引用黑盒分支、32KiB精确字节数/单条超预算、并发及未知结果恢复未因此关闭。
