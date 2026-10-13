# 开发入口

本项目按可交付的 Creo MCP 工具维护，采用功能条目驱动、短分支和分批整理。日常开发从 [统一台账](BACKLOG.md) 选择条目；新增工作先登记，复杂条目复制 [模板](templates/WORK_ITEM.md)。开发准入对小修复同样适用，内容可精简为几行。

## 每次开发的顺序

1. 明确条目 ID、问题或目标、包含与排除的范围、验收命令、预期结果、目标环境。报告中的问题先复现，区分现象与推测根因。
2. 检查工作区和现有条目；从可交付的 `main` 建立短分支，如 `codex/bug-002-registry-write`。一个分支围绕一个条目或一组明确相关的条目。
3. 实现最小完整改动。格式清理、路径迁移、行为修改分开提交；每次目录迁移同时核对安装、后台入口、资源和运行数据的位置、源码打包。
4. 执行下述检查。校验或保护逻辑补回归用例；原生建模变更还需对应 Creo 实机测试。
5. 更新条目状态、验证证据和能力边界；提交说明注明 ID、具体行为及验证。PR 使用仓库模板，检查通过后合并。
6. 发布时按 [发布规则](development/RELEASING.md) 建立版本和标签。一次提交或 AI 会话不等于一次发布。

## 配置开发环境

Windows x64、Python 3.12+。已有源码安装环境可直接安装开发依赖；只运行单元与语言检查时无需安装 Creo、SDK 或许可。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe tools\dev_check.py
```

`requirements-dev.txt` 引用锁定的运行依赖，并固定 Ruff 和 clang-format 版本。正式建模安装继续使用 `setup.ps1`，详见 [安装说明](INSTALL.md)。检查入口以脚本位置定位仓库，工具在仓库目录执行。

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

正式验收基线为 Creo 10；Creo 12 为实验兼容，按 [兼容矩阵](COMPATIBILITY.md) 记录。运行接口范围以 `capabilities.py` 为基础，能力变更同时更新工具描述、README 和有关文档。台账管理未来工作，历史版本说明保存已经发布的范围，两者职责不同。
