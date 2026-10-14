# 0.3.0 发布验收

日期：2026-10-14。条目：DEV-013、FEAT-020、DEV-002 第一批、BUG-006。环境：Windows x64 / Python 3.12.14，本机 Creo 12.4；本版没有 C++ 改动。

发布候选的开发检查和独立解压安装均通过，结构化结果见 [JSON](RELEASE-0.3.0.json)。BUG-006 的 WorkBuddy N1(P1) 按本次会话用户确认通过，详细新报告未提供，不能填写未经提供的 job_id/model_id 或原始几何数据。

FEAT-020 的 [WorkBuddy 原始报告](FEAT-020-WorkBuddy-report.md) 保留原版本 0.2.6、原时间 2026-10-14 03:27–03:30 UTC 和 Creo 12.4 环境。更新字段、缓存、预发布与实际并发通过；联网板件 job_id=563ee955f3e7454eae708824dc8aed0b，400 mm³，保存重载成功。网络故障、公开高版本、提醒等未测，不能宣称完整验收。

Creo 10 本轮未补录，按用户安排由其他机器验证。BUG-005 未修复；本次未运行全量原生、全部参数、真实多客户端启动、退出重连或完整 SDK 安装后建模。开发单元、MCP 协议和包安装检查与原生验收分别记录，旧版本证据保留原日期。保持 Pre-release。

源码 ZIP 包含本证据，源码 ZIP 的最终摘要在 GitHub Release 正文及独立 `.sha256` 附件记录，避免嵌入自身摘要的循环依赖。

## 本轮开发与分发检查

受测源码基点 5ff1684aec76da80ada5056a5162681393b8e051，dirty=true；实际检查文件的规范化源码指纹为 `44bf55b78ae7ddd6fc7e0e69663e39ef56e9276f75adadc8fbacc3d8bc9d25c4`。文档和证据归档随后补录，没有新增行为改动；不能仅用基点提交代表受测代码。

| 检查 | 命令与结果 |
| --- | --- |
| Windows 回归 | `.venv/Scripts/python.exe tools/dev_check.py --work-item DEV-013`：158 项通过，无新增诊断，保留 67 条 Ruff / 36 个 Python / 14 个 C++ 格式欠账。最初 seeds.py/version.py 换行格式检查失败，已按格式器修正，再运行全部检查通过，未修改基线 |
| MCP 引用契约 | `tools/test_reference_contract.py --output build/release-0.3.0/mcp-reference.json`：版本 0.3.0，82 工具，schema/capabilities/引用校验通过；未请求原生建模 |
| MCP 更新接口 | `tools/test_update_check.py --output build/release-0.3.0/mcp-update-before-release.json`：真实 GitHub 接口返回本地 0.3.0 高于公开 0.2.6，up_to_date、不建议降级、预发布与两个入口正确 |
| 独立源码安装 | `tools/package.py --output build/release-0.3.0/candidate-source.zip` 后全新解压，独立 venv 中 `pip install -r requirements-dev.txt`（包含本地 editable），随后 `tools/dev_check.py --work-item DEV-013`：158 项通过；源码指纹与工作区相同 |
| 分发核对 | 忽略目录内 check_distribution.py 校验公开白名单、包路径、当前文档链接、配置模板、第三方许可、九个 PRT 指纹，并将新版种子 ZIP 实际安装到空目录，available_count=9 |

九种子 ZIP SHA256：`d97bf7e4283c88c63fb835225cdb614435a8d99d4d75cc3aded39a15f54dd778`。原 PRT 未变；新版两份清单和 seeds.py 匹配此 ZIP。标签、最终附件与提交关系将在 GitHub 发布时回读确认；公开地址为 https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.3.0。
