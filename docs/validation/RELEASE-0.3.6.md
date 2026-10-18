# 0.3.6 发布候选与主干交付核对

日期：2026-10-18（Asia/Shanghai）。条目：[DEV-041](../work-items/DEV-041.md)。阶段：候选检查通过；实际 main / v0.3.6 / Release / 附件核验在交付 PR 回填，不另加未发布主干提交。

用户 2026-10-18 确认 DEV-040 收尾后发布 0.3.6。分支 `codex/dev-040-offline-recovery`，自远端 main `8ce644f` 起包含五笔：`64a7485`（0.3.5 四份反馈补录）、`2907e34`（DEV-038/039 台账重构）、`f879673`（DEV-040 建卡）、`2c9409e`（DEV-040 实施：BUG-059 修复与诊断脚本）、`a6c1334`（钣金/曲面反馈补录）。

## 本轮范围与既有证据边界

| 条目 | 实际受测身份与范围 |
| --- | --- |
| BUG-059 / DEV-040 | `2c9409e`，隔离黑盒三场景（原生前拒绝 `failed/before_native` 释放自身占位；合成原生后 `unknown_outcome/native_worker_started` 保留保护；省略字段成功 abandoned）+ 开发者复核 12/12，见[收尾复核](DEV-040-closeout-review-2026-10-18.md)。真实会话切换、原生恢复、几何与并发未测，DEV-040 按该范围归档 |
| BUG-057 | 本机 10 轮未复现；`tools/reproduce_toolkit_lock.py` 隔离诊断脚本随版提供，外部复核待原环境执行 |
| BUG-058 | 仅静态核对，未改协调器 |
| BUG-054/055 | 外部 Creo 9 与 Creo 10 实机/文件层证据补录进完成卡，历史身份保留 |
| 反馈补录 | 六份 0.3.5 外部反馈原件归档，新登记 BUG-057～062、FEAT-038～041，台账重构（DEV-038/039） |

无 C++ 改动、无新增 MCP 工具（84 不变，`server.py` 仅更新 `creo_reconcile_model` 描述）；不执行原生建模回归，历史实机证据不改标。

## 本次发布检查

- 命令：`.\.venv\Scripts\python.exe tools\dev_check.py` → `success: true`、`unit_tests: passed`（356/356，与 DEV-040 收尾复核受测源码集合 SHA256 `92002a70…` 一致口径）；存量基线 35 条 lint / 25 个未格式化文件保持，无新增语言问题；`native_validation: not_run`（无 C++ 改动，符合联调约束）。
- 版本元数据：`version.py` → 0.3.6；[RELEASE_NOTES_0.3.6.md](../RELEASE_NOTES_0.3.6.md)；本记录。
- 候选提交为包含版本元数据的工作区提交（见 PR）；dirty 状态在本记录生成时仅剩版本/发布文档本身。

## 附件与发布（PR 回填）

最终源码包与种子包必须从合并后 main 的 Git 快照运行 `tools/package.py` 与 `tools/package_seeds.py` 生成，禁止复用旧 ZIP；独立解压检查、分发白名单、第三方许可、9 枚种子 SHA256 核对后，`v0.3.6` 标签指向该 main 提交，发布非草稿 Pre-release 并附版本说明、验收摘要、环境、未测范围及两包 SHA256。发布后下载核对校验和，PR 回填远端提交、标签、Release 链接与附件核对结果。

- 合并 main 提交：`ca105b9`（PR #11 merge）+ `1f38069`（种子清单版本与 seeds.py 指纹同步；tag 指向后者）
- v0.3.6 标签指向：`1f38069`
- Release 链接：https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.3.6（Pre-release 非草稿）
- 源码包 SHA256：`6cf1d925901dc5d4fa08cd5b00261720c0a2741a8555027a6bf4f6e59ac4ad88`（588 文件，远端下载核对一致）
- 种子包 SHA256：`829474ed2995d1ab62b757133a4d9dd795e1634ef079197ab8ba7086da609741`（24 文件 / 9 种子，与 seeds.py expected_digest 一致，远端下载核对一致）
- 交付核对：[PR #11 回填评论](https://github.com/wudahua/MCP_CREO_MechDog/pull/11#issuecomment-6245231613)。本回填不新增发布后主干提交。
