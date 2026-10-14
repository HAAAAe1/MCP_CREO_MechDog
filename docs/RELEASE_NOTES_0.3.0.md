# MCP_CREO_MechDog 0.3.0

发布日期：2026-10-14。MIT 源码预发布版本，标签 v0.3.0。

本版保留原提交历史，将 FEAT-020、DEV-002 已完成的第一批及 BUG-006 合入 main；DEV-012 兼容性文档已在 main。新增功能按版本规则递增 MINOR。

## 变更

- FEAT-020：新增只读 `creo_check_update(force=false)`，查询 GitHub 公开版本，包括预发布；能力与启动状态提供共用异步缓存快照。成功缓存 24 小时，失败冷却 15 分钟，跨分页网络预算 5 秒。失败只影响更新检查，升级由用户手动执行。可用工具由 81 个增至 82 个。
- DEV-002 第一批：更新模块迁入 `src/creo_mechdog/`，对应测试迁入 `tests/unit/`；建立显式路径入口和 editable 包安装。`setup.ps1` 自动安装本地包，根 `server.py`、桥接入口及运行数据位置保留。整体迁移继续开发。
- BUG-006：`axis_pattern.axis` 兼容 `datum_feature` 轴标签并规范化为 `datum_axis_feature`；保留几何轴 ID 与显式轴标签。`capabilities.references.by_tool` 和工具 schema 明确裸引用、圆角/倒角集合及草图支撑包装。其他参数中的 `datum_feature` 仍表示基准平面。
- DEV-013：同步服务版本、九种子清单及独立种子 ZIP 摘要，完成源码与种子分发检查。

## 验证与限制

用户于 2026-10-14 确认 WorkBuddy N1(P1) 通过，BUG-006 已完成；详细新报告、任务/模型 ID 与几何/保存重载原始返回未提供，不能补造。开发者的 158 项单元/语言守卫、真实 stdio 接口和全新源码安装记录见 [发布验收](validation/RELEASE-0.3.0.md)。现有风格欠账仍保留，不宣称全库严格检查通过。

FEAT-020 的 [WorkBuddy 原报告](validation/FEAT-020-WorkBuddy-report.md) 在 Creo 12.4 / 0.2.6 开发服务验证更新字段、缓存一致性、实际并发、预发布识别，以及联网条件下 400 mm³ 板件保存重载。公开高版本提醒、真实断网/超时/限流和断网期间建模等未验证，FEAT-020 保持验收中。报告日期、版本及路径保留原样，不冒充迁移后 0.3.0 全量原生回归。

本版没有 C++ 改动；Creo 10 本轮由其他机器协助者验证，当前未补录。本机 Creo 12 的历史成功记录按原日期与范围保留；BUG-005 的 Codex 启动连接差异未修复，其他工具家族及全部参数分支未做本版全量原生回归，故保持 Pre-release。详见 [兼容矩阵](COMPATIBILITY.md)。

## 升级

等待任务完成，停止目标客户端 MCP 服务，保留 `config.json`、`client-config.json`、`models/` 和 `jobs/`，更新完整源码及内附种子库，使用匹配 SDK 重跑 `setup.ps1`，然后重启 MCP。开发环境更新后执行 `python -m pip install --no-deps -e .`；本地包安装步骤不可省略。核对版本 0.3.0、82 个工具、九个种子及实际 runtime 路径。0.2.6 必须先手动升级一次，之后才能通过此功能发现后续更新。

独立种子 ZIP 与新版清单配套；原 PRT 文件和指纹未变，外置库需同步新版清单再注册验证。源码 ZIP 已内附九种子。

## 附件

- `MCP_CREO_MechDog-0.3.0-source.zip` 与 `.zip.sha256`
- `MCP_CREO_MechDog-0.3.0-seed-library.zip` 与 `.zip.sha256`

旧标签及旧附件保留原样。
