# DEV-028：WorkBuddy 报告复核与覆盖边界

日期：2026-10-16（Asia/Shanghai）。受测服务版本 0.3.1，报告运行入口为本仓库 E 盘 dev 服务、Creo 12.4.0.0、release_numeric=44。开发交付提交 `e41f9280a2e1f1582157dbba3abc84336fb54bfc`；本次只归档和复核反馈，不改源码、不重跑建模、不清理测试模型。按用户后续要求，将验收补录单独提交，保留原实现提交；不推送、不发布、不升版。

来源：[用户附件原文](DEV-028-WorkBuddy-report-20261016.txt)，包含执行叙述和报告；用户随后重贴同轮正式报告，作业和结果一致。原件逐字节保存，SHA256 与独立登记核对见 [结构化复核](DEV-028-WorkBuddy-review-20261016.json)。报告中的建议不自动成为本轮实施指令。

提交校验：原件第 19 行自带一处行尾空格，按逐字节归档要求保留，不为通过格式检查改写原文；其完整性以 SHA256 核对。`git diff --cached --check` 仅排除该原件后通过，其余补录文档无空白错误，链接/锚点、表格与台账 ID 校验通过。

## 采纳结论

| 范围 | 报告及本次只读核对 | 结论 |
| --- | --- | --- |
| 部署与就绪 | 报告称 bridge、build_support、geometry 三指纹与发起者预期一致，source_changed_since_startup=false，ready/connected=true；接口未提供 Git/build 分支 | 采纳本轮公开接口的部署/准入报告；分支和完整编译身份仍无法从该报告确认 |
| 通用计划单通孔 | job `0c9d1335da704329ad368e7c2103ee6e` / model `814e1d7ed0364d878bdc3d181096aff3`，revision=1，体积 7030.353996706152 mm³，一拉伸一孔 | WorkBuddy 通用计划通过；现存登记、PRT 和保存重载独立核对一致 |
| 通用计划通孔+盲孔 | job `9c15196efb59499eaf104ccbd8382b2c` / model `517eb3aa8a95493192c44aa554b23227`，revision=1，体积 7020.929218745383 mm³；Ø6 通孔、Ø2 深3盲孔，x=10/y=0 | WorkBuddy 通过；孔原生尺寸、轴端点、去料体积、登记和 PRT 独立核对一致 |
| 底板快捷入口 creo_create_plate | 报告称 holes 被作为字符串，三次出现 `/holes: must be array`；未交付三次完整原始请求/错误响应 | 该场景在参数阶段受阻，没有完成 WorkBuddy 原生验收；通用计划替代结果不覆盖底板专用路径 |

两个成功计划均 succeeded、saved_file_reloaded_and_verified=true、delivery_complete=true、disconnect_code=0；当前模型 pending_job=null，PRT 存在且文件 SHA256 与成功结果相符。本次是开发者对现存登记的只读核对，不是新增 WorkBuddy 工具调用或新建模验收。报告提供的是输入摘要，完整成功输入由本次现存任务 request.json 另行复核，不能改称报告已交付逐调用原始 JSON。

## 需要保留的边界

- **序列化根因待核实。** 当前源码的 holes 参数为可空列表，与报告的 anyOf 观察相符；但尚无客户端真正发出的完整 JSON、三次原始错误及独立客户端对照，不能仅据输入类型错误断言客户端自动序列化机制，更不能承诺把 schema 改成 array 就能解决。线索补入 FEAT-008 的工具包装/契约范围，本轮不改公共参数或 null 兼容。
- **不采纳“替代接口即快捷入口通过”。** 开发者先前已在底板专用路径取得本机成功证据；该证据保留为开发者层，WorkBuddy 该入口仍未覆盖。DEV-028 按原开发验收范围已完成，不把此次部分黑盒覆盖改写为全量黑盒通过。
- **探测失败不等于没有登记。** `cb07b70ae7c84d688f223ed5ae61a31b` 确实 failed / Unknown feature label: s1，但已经登记 model `e42c1cc428c24c51b10b3b68658bd785`，revision=0、status=failed、pending_job=null、part_file=null。没有成功交付 PRT，不能据此断言 Creo 内无残留。空计划 `02bf0f7c030c400fb346fb8d9151107d` 已登记 model `2424973e8bac41e68fafcb35157e087c`、revision=1 并保存空件，二者均不纳入目标场景成功数，也未清理。
- **执行方式声明分开采纳。** 附件叙述提到尝试用文件工具/PowerShell/Bash 读取 MCP 工具结果缓存，以及写入每日记忆；因此不能照录“全程仅调用 MCP”。这些叙述不证明读取过源码、Git 或本机配置，也不证明执行了源码测试；建模结果仍按实际任务采纳，缓存读取和记忆写入不纳入验收通过依据。

Creo 9 实机编译/运行时、常量生成器内部机制、失败日志读取/摘要上限、setup 参数回写与 WindowsApps 提示、未启用的显式编译环境分支继续未验证。并发、失败回滚、独立孔工具及保存后另一次客户端重开也没有新增黑盒证据。内部机制仍以原开发证据为准，两层不互相替代。
