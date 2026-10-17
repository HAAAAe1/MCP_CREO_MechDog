# FEAT-029：E 盘开发分支集成验证

日期：2026-10-17（Asia/Shanghai）。工作目录：`E:\Projects\MCP_CREO_MechDog`。集成分支：`codex/feat-029-integration`。

本轮将原功能分支 `879aebe71391865639f21ffcdad025725c27970f` 合入恢复开发基线 `5628a33cbb8f442b4505c31c066b75fbc91017a3`。代码集成、SDK 编译及离线验证完成；**没有合入 main 或发布，没有执行新的 Creo 连接、注册、加载、重启、模型写入或故障注入。** 当前实例的实机/WorkBuddy 验收继续待测，不关闭 BUG-001。

## 合并与交叉保护

- 固定 `build/blend_callback_protk.dat` 注册入口、不可变引导/载荷、显式主机 API、protocol 3 / loader ABI 1，以及 `creo_callback_status` 已集成。查询与建模均不自动加载 DLL，不修改用户 config.pro 或安全策略。
- 保留当前 DEV-028/0.3.3 的 SDK 常量探测、编译失败摘要、显式编译环境、安装诊断和种子/许可分发修复，没有用旧分支版本覆盖。
- 保留 BUG-001 的会话/文件身份核验、无检查点普通写拒绝、恢复阶段预算、独立协调及持久化提交。回调预检只位于普通计划的模型变更之前；恢复请求仍走独立路径。
- 只有原生明确报告 `failed_stage=callback_preflight` 且 `model_unchanged=true` 时，已有保存基线模型保持 ready/revision；普通失败、未知结果和不可信的 unchanged 不获得例外。新增回归证明 unknown reservation 仍拒绝 loft，不启动执行器、不重放。
- 工具定义从 83 增为 **84**，同时保留 `creo_reconcile_model` 和新增的只读 `creo_callback_status`。能力登记、schema 检查、源码身份和源码包白名单已同步。恢复令牌还绑定新回调源码及产物选择，升级会使旧证据失效。
- 两个 add/add 的 DEV-026 文档/证据冲突保留当前 0.3.3 台账及原始 JSON，未覆盖既有证据；源分支不同版本仍由 `879aebe` 的 Git 对象追溯。旧分支的“功能已完成”关闭事实单独保留，不将本轮未测集成环境改标通过。

## 本轮验证

Windows 11 x64 / Python 3.12.14 / 本机 Creo 12.4 Toolkit SDK / MSVC x64。SDK 编译和 ABI 夹具使用 E 盘；没有与 Creo 会话建立连接。

| 检查 | 结果与边界 |
| --- | --- |
| `python tools/dev_check.py --work-item FEAT-029` | 增量语言检查、**297 项完整单元**通过；存量风格欠账仍保留，没有重建基线 |
| 针对性 callback/reconciliation 单元 | 41 项通过，覆盖回调拒绝、unknown 保护、恢复幂等/登记与两个公开工具共存 |
| `python bridge.py build` | 集成后的 worker、loader、payload 编译通过；只准备本机产物，不注册、不启动 Creo |
| `python -m tools.test_callback_payload --output build/feat029-integration-payload.json` | 实际编译载荷的 **12 项 ABI/状态检查**通过：nonce、初始化前拒绝、陈旧文件、活动请求、越界输入、双请求拒绝、选择/释放、终止状态。模型 API 为夹具，不是原生几何验收 |
| 真正 stdio MCP 离线检查 | 新进程定义84工具；真实通道锁被占用时，模型证据查询可读，回调状态为 unknown/channel_busy 且携带占用者，写恢复返回结构化 busy。服务后台启动已在此夹具关闭，未调用 Toolkit |
| 源码分发检查 | 从实际集成提交的 Git 快照制作、解压源码包；结果见[机器可读记录](FEAT-029-integration-2026-10-17.json)。运行数据、SDK、常量表和用户未跟踪计划不进入包 |

本轮源码、执行器/载荷/引导身份、命令与检查结果见[JSON](FEAT-029-integration-2026-10-17.json)。原始 `FEAT-029-WorkBuddy-report-2026-10-16.md` 与源分支逐字节相同，SHA256 仍为 `14f41ff0e6ec2c941c4ac3cee9791ae6613e374097fb39ab453eba8f6c744461`；G0 与 2026-10-17 恢复证据保留原件。

## 使用与剩余验收

本机继续仅用指向 E 盘的 `MCP_CREO_MechDog_dev`。已运行的 MCP 实例需要在恢复联调前重新连接，才能加载新增工具；本轮不通过重连触发 Creo 后台启动。源码 VERSION 仍为 0.3.3，集成改动尚未发布，不能按版本号推断客户端已有84工具。

旧 protocol 2 需要一次显式迁移到新固定入口；首次注册、必要的安全确认、将配置片段合入实际读取的 config.pro、手动启动和必要的正常 Creo 重启仍由使用者按[生命周期说明](../CALLBACK_LIFECYCLE.md)执行。固定文件名不等于已经完成 GUI 注册、加载或跨重启持久性。

原独立分支 2026-10-16 的开发者生命周期及 WorkBuddy 核心结果保留[原关闭记录](FEAT-029-closure-2026-10-16.md)；本次不重签。当前集成环境的两个直接放样入口、保存重载、升级/回退/并存、已加载模块保护及 WorkBuddy 未复跑。Creo9/10、真实 SDK/引导代际变化等旧未测范围继续保留。

用户已要求先集成 FEAT-029，本轮不以尚未关闭 BUG-001 阻止代码整合；Creo 卡死未定位仍阻止恢复实机测试。后续进入 main 时须选择未发布功能版本并完成实际 Release/附件校验，本轮不执行主干交付。
