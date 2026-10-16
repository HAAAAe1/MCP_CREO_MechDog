# 0.3.3 集成与发布验收

日期：2026-10-16（Asia/Shanghai）。条目：[DEV-029](../work-items/DEV-029.md)。结论：合入前发布候选验收通过；本记录不提前宣称已经公开发布，正式交付信息在本次合并 PR 回填。

以已发布的 main / 0.3.2 为基础集成 DEV-028 和 WorkBuddy 补录，保留原实现提交及 main 的 DEV-025 测试与分发修复。Creo 9 真实 SDK/运行时未验收，WorkBuddy 底板快捷入口未覆盖，FEAT-029 独立实现不在本次范围。版本与变更见 [发布说明](../RELEASE_NOTES_0.3.3.md)。

## 源码与环境

候选提交 `e9c134b77e5807cc45c3f81c1446f2a3e6eede49`，dirty=false；开发检查源码 SHA256 `bde27688aa73fc52cb5bf1cc41b30881a3b2bdbd44dd54cb24d790918bf5069c`。之后只补文档证据，最终 main 的运行源码须与此逐项一致，附件从实际 main 提交重新生成。源码包独立目录 Git 身份为 null/null，按候选 ZIP 摘要及同一源码指纹确认，不读取父仓库提交冒充解压来源。逐作业/源码身份和摘要见 [结构化证据](RELEASE-0.3.3.json)。

环境：Windows 11 x64 10.0.26100 / Python 3.12.14 / Creo 12.4.0.0 / 匹配 Toolkit SDK（release_numeric=44）/ MSVC 19.44.35213。实机通过现有 Explorer 桌面启动隐藏测试进程，不关闭或重启 Creo，不把原开发宿主连接 -4 的限制改写为已修复。

## 最终导出发现与修正

第一次 main 导出预检发现 seed_manifest.json 的 CRLF/LF 差异使种子 ZIP 摘要变化。当时尚未建立 v0.3.3 标签或发布 Release，不能沿用工作区候选的摘要。随后在同一次未完成发布流程中增加 seed_distribution：库内 Markdown/JSON/Python/LICENSE 文本按 LF 入包，原生 PRT 字节保持原样；安装许可比较只容许 CRLF/LF 差异，内容篡改仍拒绝。新增两项完整回归，并从修复提交重做下面全部候选检查。此前 261 项检查及旧候选摘要保留在原 PR #7 阶段记录中，不作为最终发布证据。

## 本次检查

| 范围 | 命令或操作 | 结果 |
| --- | --- | --- |
| 标准检查 | 两目录各运行 `python tools/dev_check.py --work-item DEV-029` | 各 263 项通过，0 failure / 0 error，无新增语言问题；现存风格欠账继续按原基线，不宣称 strict 全库通过 |
| 种子换行一致性 | 工作区与 Git 导出分别构建整个种子 ZIP；LF/CRLF 夹具回归及许可篡改拒绝回归 | 两个 ZIP 字节完全相同；九个 PRT 摘要未变，许可只容许换行差异 |
| 原生构建 | 两目录各 `python bridge.py build` | 匹配本机 SDK 构建通过，两个孔探针均生成，未复制其他机器的 constants.inc |
| 通用/底板孔回归 | 两目录各 `python tools/test_general.py` | 各 7 个写作业成功并保存重载；圆盘尺寸编辑、L 形支架 10600 mm³、旋转件通孔/盲孔/槽 6324.026011676252 mm³、底板孔 7030.353996706152 mm³ |
| 参数与失败回滚等发布回归 | 发布目录 `python -m tools.test_toolkit_recovery --native` | 8 成功（7 写作业、1 只读刷新）与 1 个预期失败；参数编辑、检查点回滚/revision、原文件保持、实际重叠 retry、后续实体/底板/工程图和连接通过 |
| 独立安装 | 候选源码 ZIP 解压，独立 venv、锁定依赖及 extracted-root editable 安装，真实 `setup.ps1 -CheckOnly` | 包元数据/接口 0.3.3，资源和包根指向解压目录；SDK/Python 前置检查通过；不是受限新机器的完整 setup 实测 |
| 公开接口与种子 | 两目录真实 MCP 能力、会话与种子查询；独立 ZIP 安装与注册 | 82 工具、9 种子、connected=true、source_changed=false，所有运行源码指纹一致；种子 ZIP 实际安装可用数 9 |
| 分发 | CRC、白名单、原件字节与排除项检查 | 候选 373 文件，包含原件 TXT 和 C++ 交付测试夹具，无本机配置/SDK/许可/二进制/生成常量表/jobs/models/venv；本记录补齐后从最终 main 重新打包 |

累计 22 个成功作业，其中 21 个成功写作业的 saved_file_reloaded_and_verified=true，另 1 个只读刷新不要求保存；1 个预期失败的 rollback_succeeded=true。没有重交未知任务。旧测试助手固定查询历史 unknown ID，隔离目录仅提供其字节一致的只读 manifest 镜像；原 manifest 摘要保持不变，这不算新增未知结果恢复验收。

种子包摘要 `7e1332dd87ec0a90dd20600594e88580721df50eaff66f4e588a7ad771e79e70`，两份清单及 seeds.py 安装校验一致，九个原 PRT 摘要未变。候选源码 ZIP 摘要 `dff7517bcf81bae3858ec51e57fbfcf761516587db968f30143bfc298c82ac54` 只代表受测候选，不能当作最终 main 附件摘要。

保留 0.3.2 已有测试夹具隔离和精确档案格式排除；没有重建或增加风格基线债务项。历史反馈原件的行尾空格按原样保存，差异空白检查排除原始档案，原件以字节和 SHA256 校验；当前说明与代码正常检查。

## 未测与远端交付

本机无 Creo 9 SDK，未做其真实编译/运行时建模；未做 Creo 10 或其他维护版本独立测试，也未重测全部建模家族/参数分支、系统冷启动损坏注入、历史完整 transform/保存/-38 因果链、受限机器完整安装或真实商店交互。WorkBuddy 的通用孔正例保留原 0.3.1 身份，底板专用入口的客户端参数问题仍待 FEAT-008 核实；未执行新一轮 WorkBuddy 全量验收。独立 FEAT-029 功能不在本次发布范围。

通过保留历史的 PR 合入 main，完成 Windows CI；以实际 main 提交生成源码/种子 ZIP 与各自 SHA256，建立 v0.3.3 并发布非草稿 Pre-release，再下载四份附件核对摘要。最终 main 提交、标签指向、Release 链接及附件验证回填 PR，避免为回填另造未发布的 main 提交。公开交付失败时继续补齐，不能只报告已合并。
