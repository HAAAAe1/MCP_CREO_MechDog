# 开发入口

本项目按可交付的 Creo MCP 工具维护，采用功能条目驱动、短分支和分批整理。日常开发从 [统一台账](BACKLOG.md) 选择条目；新增工作先登记，复杂条目复制 [模板](templates/WORK_ITEM.md)。开发准入对小修复同样适用，内容可精简为几行。

当前后续批次见[DEV-030分期任务卡](work-items/DEV-030.md)：[BUG-001 G0复现](validation/BUG-001-repro-2026-10-16.md)已确认当时0.3.3模型协调阻断，2026-10-17按[联合执行卡](work-items/BUG-001-FEAT-018-RECOVERY.md)完成恢复实现，284项单元及四动作部分实机通过；随后Creo卡死未定位，停止新的Toolkit调用，完整实机/WorkBuddy仍未完成，见[恢复验证记录](validation/BUG-001-recovery-2026-10-17.md)。用户随后要求先集成FEAT-029，现已纳入E盘开发分支，297项单元、SDK编译、载荷ABI及84工具离线检查通过，见[集成记录](validation/FEAT-029-integration-2026-10-17.md)。来源见[履带映射](validation/TRACK-FEEDBACK-2026-10-16.md)和[0.3.3构建/回调反馈](validation/FEEDBACK-0.3.3-BUILD.md)，历史分支与原件核对见[分支记录](validation/DEV-030-branch-sync-2026-10-17.md)。当前本机MCP只启用MCP_CREO_MechDog_dev指向E盘，未合入main或发布；单项状态以统一台账为准。

最新[BUG-001离线卡死核对](validation/BUG-001-hang-offline-2026-10-17.md)已确认Creo IPC初始化通信失败及同一12.4进程无响应关闭，底层诱因仍待定位。当前无Creo会话可验证，确认可操作前继续停止Toolkit连接/注入；此核对不替代实机/WorkBuddy验收。

## 每次开发的顺序

1. 明确条目 ID、问题或目标、包含与排除的范围、验收命令、预期结果、目标环境。报告中的问题先复现，区分现象与推测根因。
2. 检查工作区和现有条目；从可交付的 `main` 建立短分支，如 `codex/bug-002-registry-write`。一个分支围绕一个条目或一组明确相关的条目。
3. 实现最小完整改动。格式清理、路径迁移、行为修改分开提交；每次目录迁移同时核对安装、后台入口、资源和运行数据的位置、源码打包。
4. 执行下述检查。校验或保护逻辑补回归用例；原生建模变更还需对应 Creo 实机测试。
5. 更新条目状态、验证证据和能力边界；提交说明注明 ID、具体行为及验证。PR 使用仓库模板；合入 `main` 前确定未发布的目标版本，同步版本元数据及版本说明，完成适用检查与发布准备。
6. 每次合入或直接提交到 `main`，均须在同一次交付流程按 [发布规则](development/RELEASING.md#合入-main-必须同步发布) 发布对应版本的 GitHub Release（包括文档和工程配置变更）。核对主干提交、版本标签、附件及 SHA256，并回填 Release 链接；Release 未发布或附件未齐则交付未完成。开发分支上的普通提交不要求发布。

## 配置开发环境

Windows x64、Python 3.12+。已有源码安装环境可直接安装开发依赖；只运行单元与语言检查时无需安装 Creo、SDK 或许可。正式建模安装可使用 Creo 9、10 或 12 及匹配 SDK；Creo 9 的编译与运行时状态见 [兼容矩阵](COMPATIBILITY.md) 与 [BUG-033](work-items/BUG-033.md)。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe tools\dev_check.py
```

`requirements-dev.txt` 引用锁定的运行依赖、固定 Ruff 和 clang-format 版本，并通过 `-e .` 安装本地源码包。`pyproject.toml` 的构建后端版本也已锁定。正式建模安装继续使用 `setup.ps1`，详见 [安装说明](INSTALL.md)。检查入口以脚本位置定位仓库，工具在仓库目录执行。

`.gitattributes` 固定 Python/C++ 和新开发文档换行为 LF，避免 Windows 检出设置导致格式检查差异；已有历史文档沿用原换行，第三方与原生 PRT/ASM 等二进制禁止文本转换。

## 检查与现有问题基线

默认命令执行 Ruff 检查、Python/C++ 格式检查、历史基线比较和全部 Python 单元测试。输出 `build/development_check.json` 与 `build/unit_test_report.json`，失败返回非零退出码。Windows CI 执行同一入口，保存报告，不连接 Creo。

现有压缩代码暂记在 [风格基线](development/style-baseline.json)。它是未完成的整理工作，不是语言规范已全部通过的证明：

- Ruff 问题按文件、规则、消息、源代码行及次数匹配，行号移动不会误报；新增问题或同类问题次数增加会失败。
- 未格式化文件以规范化换行后的内容 SHA256 匹配；内容变化后必须通过格式检查。处理旧模块时先单独做格式整理，再改行为。
- 已清理问题可以消失，基线不会因此阻塞检查；随后在独立提交中删去对应基线项，防止旧问题被再次容许。
- 工具版本或配置改变、工具缺失、语法或配置错误、单测失败都会使检查失败。不能用自动更新基线规避检查。
- 基线变更必须关联工作条目并单独审查，审查新增容许项的具体原因；CI 从不生成或更新基线。

```powershell
# 仅检查语言，不构成单元或原生验收
.\.venv\Scripts\python.exe tools\dev_check.py --skip-unit
# 忽略历史容许项；当前会明确暴露全部存量问题
.\.venv\Scripts\python.exe tools\dev_check.py --strict --skip-unit
# 仅在审查工具升级、配置修改或初始欠账后显式执行
.\.venv\Scripts\python.exe tools\dev_check.py --write-baseline --reason 'DEV-xxx: 已审查的具体原因'
```

语言细则见 [编码规范](development/CODING_STANDARD.md)，迁移路线见 [架构计划](development/ARCHITECTURE.md)。

## 验收级别

| 改动 | 本次必须取得的证据 |
| --- | --- |
| 文档、开发配置 | 文档引用与台账一致性、适用工具配置可加载；涉及检查或打包时运行其回归用例 |
| Python 校验、调度、登记、保护逻辑 | 统一检查、对应回归；外部进程/会话行为需要额外实机验证 |
| C++ 或建模行为 | 上述检查、匹配 SDK 构建、对应 `tools/test_*.py`、原生几何及尺寸断言、保存擦除重载验证；失败路径涉及回滚时验证回滚 |
| 路径或布局迁移 | 单元检查、安装和客户端入口、后台任务、资源/数据根目录、源码包重新解压验证；涉及原生部分补实机验收 |
| 发布 | 发布回归清单、环境与源码标识、版本一致性、附件与校验和；明确本轮未测项 |

原生修改验收必须检查任务成功、原生特征有效、几何断言通过、`saved_file_reloaded_and_verified == true`。超时、`unknown_outcome`、拒绝非法输入以及仅能编译均不能计为建模成功。历史证据保留原日期和环境，只能在明确证明实现一致且说明复用范围时引用，不能改名冒充本次测试。

每份新证据记录条目 ID、版本、提交号、工作区是否有修改、实际受测源码指纹、测试时间、Windows/Python/Creo/SDK/编译器环境、命令、结果和未测范围。工作区有修改时，提交号不能单独代表受测内容。

## 功能与支持声明

2026-10-15 按用户要求，当前开发与发布按本机 Windows x64 / Creo 12.4.0.0 / 匹配 Toolkit SDK 的实际改动范围验收。Creo 10 独立复测、双版本验收及正式基线不再作为完成、合入或发布门槛；朋友反馈具体问题后，再登记或沿用 ID 跟进。2026-10-16 起把 Creo 9 与匹配 Toolkit 9 纳入支持/要求范围，[BUG-033](work-items/BUG-033.md) 编译探测修复已实现；本机无 Creo 9 SDK，实机编译和建模运行时均未验收，不据此把 Creo 9 写成已通过。历史报告中的 Creo 10 测试、失败来源和未测事实保留，旧复测安排不再约束当前任务，不把取消要求写成其他环境已通过。具体已测功能和未测范围按 [兼容矩阵](COMPATIBILITY.md) 记录。运行接口范围以 `capabilities.py` 为基础，能力变更同时更新工具描述、README 和有关文档。台账管理未来工作，历史版本说明保存已经发布的范围，两者职责不同。

## WorkBuddy 测试约定

2026-10-13 用户明确要求：本项目所有“WorkBuddy 测试”均指直接使用已连接的 MCP 工具，对最终用户可见行为做黑盒验收，不查看源码。该约定已写入 [根级代理规范](../AGENTS.md)，后续任务和测试提示词均遵循，适用范围不限于 BUG-002。

WorkBuddy 测试提示词只包含 MCP 操作场景、输入、预期结果和报告要求，不要求阅读仓库、检查 Git、查看本机配置、修改源码或执行本地测试命令。环境、会话、可见工具与服务版本通过 MCP 公开接口确认；接口未提供的信息记为“无法确认”。版本号本身不足以证明具体修复已部署，部署身份可由测试发起者提供，不能据此要求 WorkBuddy 检查源码。

最终结果记录实际工具调用与输入、任务/模型 ID、终态、几何和参数、保存重载、revision、回滚及原始错误。并发场景须实际并行调用；不能并行时记为“并发未验证”。文件占用注入、重试预算/次数和临时文件清理等内部机制，若无法通过 MCP 观察，则不纳入 WorkBuddy 的通过结论。

开发者仍按前述要求执行源码单元、开发检查、压力和实机脚本。开发证据与 WorkBuddy 最终 MCP 验收分别记录；本约定不表示已经执行 WorkBuddy 测试。用户明确调整当次范围时遵循当次要求。

## 2026-10-17 FEAT-029集成

已按用户指令把879aebe集成到E盘恢复开发基线，当前84工具、297项单元、SDK编译及12项载荷ABI通过，见[集成验证](validation/FEAT-029-integration-2026-10-17.md)。本机仅用MCP_CREO_MechDog_dev。Creo卡死限制保留，未做新的实机或WorkBuddy调用，未合入main/发布。
