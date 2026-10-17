# 0.3.5 发布候选与主干交付核对

日期：2026-10-17（Asia/Shanghai）。条目：[DEV-035](../work-items/DEV-035.md)。阶段：发布准备，适用检查完成后回填；实际 main / v0.3.5 / Release / 附件核验在本次交付 PR 回填，避免另加未发布主干提交。

用户指定提交全部相关内容、将未合分支统一合入 main，版本 0.3.5。E 盘起点 `7951266`、远端 main `7662f7e`；待交付五个提交为 `65ea3db`、`f3c434f`、`26a3edd`、`eca844c`、`7951266`。原始分支和验收历史保留，不重复采摘已合祖先。

## 已有功能证据与本轮边界

| 条目 | 实际受测身份与范围 |
| --- | --- |
| BUG-054 / DEV-033 | `65ea3db` 的本机 Creo 12.4 T01～T08；[WorkBuddy 五场景](BUG-054-WorkBuddy-acceptance-2026-10-17.md)及开发者只读核对 11 作业通过，revolve 正反例包含在内。后续版本元数据改变不把该记录改标新测试 |
| BUG-055 / DEV-034 | `26a3edd`，真实 stdio 6 项、既有协调回归、307 项单元及本机 MCP 显式 null 正例；[WorkBuddy 核心契约](BUG-055-WorkBuddy-acceptance-2026-10-17.md)通过，客户端显式 null 降级为空串已记录，省略字段完成 M1。M2 与稳定通道下对照未取得 |
| BUG-056 | 新 P1 待核实；约 40 秒通道静默失效和后续无会话观测保持来源，未实现修复 |

当前不新增 Toolkit 探测、启动、模型写入、故障注入或 WorkBuddy 操作，不处置 M2 recovery_pending。FEAT-018/029 及其他版本/分支未测范围不因发布关闭。

## 本次发布检查

实际命令、源码 commit/dirty/指纹、Windows/Python/SDK 环境、独立安装与构建、分发原件/种子摘要及附件信息在[结构化记录](RELEASE-0.3.5.json)汇总。仅报告真实完成的检查；候选提交与最终合并提交分别标识。

最终四份附件必须从实际合并后 main 的 Git 快照运行 tools/package.py 与 tools/package_seeds.py 生成，禁止复用旧源码 ZIP。核对无本机配置、SDK、constants.inc、二进制或运行数据；9 个原生种子 PRT 身份保持。发布为非草稿 Pre-release 后回下载核对 SHA256，PR 回填远端提交、标签、Release 及附件校验。
