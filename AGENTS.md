# Repository Guidelines

## 项目结构与模块划分

- 根目录的 Python 模块负责 stdio MCP 服务（`server.py`）、任务与构建桥接（`bridge.py`、`generic_bridge.py`）、输入校验（`schema.py`、`profile_checks.py`）及建模辅助逻辑。
- `native/` 保存 C++17 Creo Toolkit 执行器和各类特征实现；`native/third_party/` 保存第三方 JSON 代码及许可证。
- `tests/` 保存 Python 单元测试；`tools/` 保存实机 Creo 集成测试、打包脚本及验证证据汇总工具。
- `examples/` 保存 JSON 建模方案；`seed_library/` 保存原生 PRT 种子模板及清单；`docs/` 保存安装说明、功能边界和验证记录。
- `.venv/`、`build/`、`jobs/`、`models/` 是本机运行生成的目录。

当前布局与迁移目标分别记录在 `docs/development/ARCHITECTURE.md`。首批只建立规范；Python 包化、C++ 上下文提取及独立编译由 DEV-002～DEV-004 分批推进，每批同时核对入口、路径、安装和打包。

## 开发准入与台账

- 以 `docs/DEVELOPMENT.md` 为开发入口、`docs/BACKLOG.md` 为唯一工作台账；每项功能、缺陷或工程整理在实现前登记固定 ID、目标、范围、验收方式和环境。小修复可精简，复杂条目使用 `docs/templates/WORK_ITEM.md`。
- 先复现已报告缺陷，分别记录现象与推测根因。优先处理 P1 稳定性问题，再扩展建模能力。
- 条目验收后同步状态、能力边界和本次证据。旧版本说明、测试日志和待办快照保留其历史日期，不作为当前台账。

## 构建、测试与开发命令

在仓库根目录使用 PowerShell 执行以下命令。安装需要 Windows x64、Python 3.12+、Creo 10 或 Creo 12、匹配的 Toolkit SDK、可用许可及 MSVC x64 构建工具。

- `.\setup.ps1 -CreoRoot 'C:\Program Files\PTC\Creo 10.0.0.0'`：创建虚拟环境、安装锁定版本的依赖、生成配置和常量表，并编译执行器。请替换为实际安装路径。
- `.\.venv\Scripts\python.exe bridge.py build`：编译变更后的原生源码，或复用已有执行器。
- `.\.venv\Scripts\python.exe server.py`：启动本地 stdio MCP 服务。
- `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`：运行单元测试。
- `.\.venv\Scripts\python.exe tools\test_unit.py`：运行单元测试并生成 `build/unit_test_report.json`。
- `.\.venv\Scripts\python.exe tools\test_general.py`：连接已打开的 Creo 会话，执行原生建模集成测试。
- `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`：安装锁定的运行与开发依赖；纯单元/语言检查无需 Creo SDK。
- `.\.venv\Scripts\python.exe tools\dev_check.py`：检查新增语言问题并运行全部 Windows 单元测试，生成 `build/development_check.json`。
- `.\.venv\Scripts\python.exe tools\dev_check.py --strict --skip-unit`：暴露全部存量语言问题；不是原生建模验收。

## 代码风格与命名约定

Python 使用四个空格缩进，函数和模块采用 `snake_case`，类采用 `PascalCase`；Ruff 配置位于 `pyproject.toml`。C++ 保持 C++17 和 Toolkit 命名，格式配置位于 `.clang-format`，保留 include 顺序。具体错误处理、类型标注、资源管理规范见 `docs/development/CODING_STANDARD.md`。格式清理按模块独立提交，排除第三方、SDK 和生成文件。

历史问题记录在 `docs/development/style-baseline.json`，默认检查拒绝新增诊断和变更后仍未格式化的文件。工具/配置错误与单测失败不能加入基线；基线新增容许项必须关联条目、说明原因并单独审查，禁止在正常开发或 CI 中自动重建。

长度使用毫米，角度使用度。特征标签以小写字母开头，仅包含小写字母、数字和下划线，最多 28 个字符。服务标准输出仅用于 MCP 协议消息。

## 测试要求

### WorkBuddy 测试约定（项目全局）

- 用户提到“WorkBuddy 测试”“用 WorkBuddy 测试”或要求给 WorkBuddy 测试提示词时，均指通过 WorkBuddy 直接调用已连接的 MCP 工具，对最终用户可见行为做黑盒验收。此约定适用于整个项目，不限于 BUG-002。
- WorkBuddy 不查看、分析或修改源码，不执行本地 Python 测试脚本、单元测试、开发检查或源码压力探针；测试提示词只提供 MCP 操作场景、输入、预期结果和报告要求。
- 环境、会话、可见工具与服务版本通过 MCP 公开接口确认。接口未提供的构建身份或实现细节记为“无法确认”，不要求读取仓库、Git 状态或本机配置来补齐。
- 验收以工具实际返回及 Creo 中的实际结果为准，记录工具调用、输入、job_id/model_id、终态、几何/参数、保存重载、revision、回滚和原始错误；只有真实实施了并发调用，才能报告并发测试通过。
- 只能靠源码或本地脚本验证的内部机制（例如文件占用注入、重试次数/预算、临时文件清理）不纳入 WorkBuddy 结论。无法由 MCP 观察的项目明确记为“未验证”，不得推测通过。
- 下面的开发者测试要求继续用于实现与回归阶段；本地测试证据和 WorkBuddy 最终 MCP 验收分别记录，不互相替代。用户明确要求改变 WorkBuddy 范围时，以当次要求为准。

单元测试使用 `unittest`，文件命名为 `tests/test_*.py`，测试方法命名为 `test_*`。修改输入校验或保护逻辑时补充回归用例。项目未设置数值化覆盖率门槛。修改原生建模代码后，运行对应的 `tools/test_*.py`，检查任务成功、几何断言通过，以及 `saved_file_reloaded_and_verified` 为 `true`。明确记录本次验证范围，不能用历史证据代替当前验证。

Windows CI 仅承担语言与单元检查；原生构建及建模由具备匹配 SDK、许可的环境验收。Creo 10 是正式验收基线，Creo 12 已验证可用，已记录的实机版本为 12.4.0.0，范围见 `docs/COMPATIBILITY.md`；不同版本的发布回归分别记录，不互相替代。新证据记录条目、源码提交与 dirty 状态、受测源码指纹、命令、环境和未测范围。

## 提交与合并请求要求

历史提交保留原样。新提交标题简短指出条目 ID 和具体变更。`main` 保持可交付，开发使用 `codex/<条目>-<主题>` 短分支。合并请求使用 `.github/pull_request_template.md`，说明影响范围、关联条目、列出验证命令及结果、注明 Creo 环境，并提供适用的建模证据。支持能力发生变化时，同步更新能力说明文档。

`version.py` 是服务/源码版本入口。一次开发会话不等于一次发布；验收发布时依 `docs/development/RELEASING.md` 统一三段版本、候选版、标签及附件。已发布标签和同名附件不得覆盖；本批 DEV-001 保持服务版本 0.2.5。

## 配置与许可

本机路径写入已被 Git 忽略的 `config.json` 和 `client-config.json`。不要提交生成的常量表、二进制文件、日志或测试模型。保留第三方许可声明，不要提交 PTC SDK 文件或许可数据。
