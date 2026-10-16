# 0.3.2 发布候选验收

日期：2026-10-16；条目：[DEV-025](../work-items/DEV-025.md)。发布候选验收通过。本文件记录合入前的实际检查；最终 main 提交、标签、公开 Release 及远端附件校验在 [PR #6](https://github.com/wudahua/MCP_CREO_MechDog/pull/6) 回填，不提前将发布准备当作公开交付。

集成 DEV-002 第二批、BUG-009、BUG-008 及已完成文档。历史 WorkBuddy 原件及开发者证据保留受测 0.3.1 和原日期，详见各条目，不外推为全部 0.3.2 黑盒验收。

## 本次执行与源码身份

独立发布分支 `codex/dev025-release032`，候选源码提交 `32d8b92`，工作区干净；源码预检 ZIP v2 包含 343 个白名单文件，SHA256 为 `5ceb9e7bdf5964009b43270c127adef56d8d783a27d337360f5b596081cd0aea`。之后只补充发布文档和证据，最终附件从实际 main 提交重新生成，候选包摘要不冒充最终附件摘要。

新目录解压位于原仓库忽略的 build 内，`dev_check.py` 正确记录 Git 身份为 null/null；原生旧测试助手直接调用 git，误读到父 E 目录的提交/dirty，该字段不作为解压源码身份。候选 ZIP 来源、23 枚实际 MCP 源码指纹和本次对照共同确认受测代码，见 [结构化记录](RELEASE-0.3.2.json)。日志保留在记录列出的忽略目录并附 SHA256。

环境：Windows x64 / Python 3.12.14 / Creo 12.4.0.0 / 匹配 Toolkit SDK，公开 release_numeric=44；使用本机 MSVC x64 配置。当前已有 Creo 会话保持打开，没有关闭或强杀。

| 验证 | 命令 / 结果 |
| --- | --- |
| 新目录独立安装 | 创建独立 .venv，`pip install -r requirements-dev.txt`，editable 包元数据 0.3.2 |
| 标准开发检查 | `python tools/dev_check.py --work-item DEV-025`，247 项单元通过，无新增语言诊断；40 条现存 lint、28 个未格式化文件仍按原债务保留，不宣称 strict 全库通过 |
| SDK 构建 | 新目录 `python bridge.py build` 成功；本机配置只用于验收，未进入源码包 |
| 真实 MCP 原生回归 | `python -m tools.test_toolkit_recovery --native --output build/release032/native-v2.json`；两客户端、8 个成功作业和 1 个预期失败作业通过 |
| 原生断开/刷盘与保护 | 发布工作区 `tools.test_toolkit_recovery --controlled --native`；5 种 C++ 交付路径、20 秒看门狗、9 秒探针预算、未知结果保护通过；该受控证据与真实 PRT 分开记录 |
| 公开接口和种子安装 | 等待公开 ready 后检查 82 个工具、9 个可用种子、实时 connected/code=0、source_changed=false；独立种子 ZIP 实际安装到隔离目录并注册/验证通过 |
| 分发及原件 | 源码 ZIP CRC/白名单、许可与配置模板检查通过；C++ 测试夹具在包内，无本机配置、执行器、SDK、许可数据、jobs/models；8 份相关原始报告字节/哈希不变 |

原生覆盖：600 mm³ 草图/实体、参数编辑、检查点回滚与 revision 保持、真实重叠 retry、120 mm³ 独立实体、600 mm³ plate、新建工程图及只读刷新。所有成功写作业的 `saved_file_reloaded_and_verified=true`、`delivery_complete=true`、`disconnect_code=0`，预期失败验证 `rollback_succeeded=true`，随后建模及连接继续可用。完整 job/model/revision 与保存文件摘要见 JSON。

历史 unknown 作业仍指向原 pending_job、revision=9，model.json SHA256 `03a4d13a90d4f34295525945790d72e53e8acd0fc2827004258efb15ad6536ae`，原 PRT SHA256 `324dd24ebd4d7b682fa9bbb41fbe02bc06b8158b5f43e75dec4b10f0f2323c6e`，均未改变。没有重放或解除保护。

## 首次失败与检查配置

首次解压目录将单元与实机并行，RegistryJobs 夹具遗漏 `bridge.ROOT` 隔离，模拟 worker 失败写入真实 build/toolkit_health.json。新建件成功后，下一次计划被启动保护拒绝、未排入作业。本次只修复测试夹具并新增保持真实健康记录不变的回归，再按 247 项单元、实机顺序通过；首次失败原始报告继续保留。另一次独立协议助手未等待启动准备即查询实时状态，修正助手等待公开 ready 后通过，没有据此修改产品行为。

两份不可改写的反馈 Markdown 代码块触发 formatter；pyproject 仅精确排除这两份档案的格式化，全部业务源码继续检查。风格基线只手工审核更新该配置指纹，诊断/格式债务条目完全不变。历史混合行尾独立提交归一，归一化内容一致；其中种子解析脚本字节改变，因此重建 ZIP 并同步安装摘要。

九个 PRT 摘要未变；确定性种子 ZIP SHA256 为 `e7b07e9a18f6101ec3fed145359831a7ffcf801be2e53a65f335d4c3cc9c2a16`，与 seeds.py 固定校验值一致。最终 main 的 ZIP 必须重新生成并核对该摘要。

## 范围与交付核对

本次未重做系统冷启动损坏注入、全部建模家族/参数分支、历史 transform/保存/-38 完整链、Creo 10/其他维护版或新一轮 WorkBuddy 全量验收。此前开发者真实冷态及 WorkBuddy 已有会话正例保留原身份；BUG-001/005/011 等未完成项不随本次发布关闭。

PR #6 将记录最终实际主干提交和 v0.3.2 指向；从该提交生成源码 ZIP、种子 ZIP 与各自 .sha256，发布非草稿 Pre-release，再下载公开附件逐项核对。本记录的候选源码摘要不能替代该远端核对。
