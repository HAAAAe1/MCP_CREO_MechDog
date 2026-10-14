# FEAT-020 开发与 MCP 验收记录

日期：2026-10-14。状态：实现完成，验收中；尚未发布。用户明确分工：本机只验证 Creo 12，Creo 10 由协助者在其他机器验证，不要求本机具备 Creo 10。外部证据独立补录。

服务源码暂为 0.2.6，新增功能的目标发布版本按规则为 0.3.0。已发布 0.2.6 的标签和附件保持原样，旧发布仍为 81 个工具，不包含本功能；当前源码为 82 个工具。源码身份必须核对新工具与 runtime 指纹，不能只看版本号。

## 实现与受测环境

`update_check.py` 实现公开 GitHub Release 分页查询、SemVer、异步共享请求、内存缓存、超时与失败冷却。`server.py` 注册只读联网工具 `creo_check_update`，在能力和启动状态中返回相同 update 快照，instructions 引导首次检查、提醒和客户端会话去重。`tools/package.py` 白名单包含新模块；`requirements.txt` 显式声明锁定的现有 HTTP 依赖。新增开发者回归及 MCP 测试入口，完整契约见 [功能说明](../UPDATE_CHECK.md)。未修改原生 C++、模型登记、revision 或就绪保护。

受测基点提交 `b7f4dfe1bf4c2787e50a5df5b08012a463b2d24b`，dirty=true；实际代码通过逐文件与统一检查指纹标识，详见 [结构化证据](FEAT-020.json)。最终语言/单元检查源码 SHA256：`068e51c0bfc0a77005e0d8551deecbf842c99e43d118f71c2ebba71307e649c3`。环境：Windows 11 x64 10.0.26100、Python 3.12.14、已配置 Creo 12.4 SDK / VS 2022 x64。窗口实际显示 Creo Parametric 12.4.0.0；没有阻挡启动的对话框，GUI 可用不代表 Toolkit 连接成功。

## 本轮开发结果

命令均在仓库根目录通过 `.venv/Scripts/python.exe` 执行；完整机器日志保留在忽略的 `build/`，公开摘要和原始报告 SHA256 见结构化证据。

| 命令 / 场景 | 实际结果 |
| --- | --- |
| `-m unittest tests.test_update_check -v` | 21 项新回归通过；新版本、相等/开发版、预发布和网络失败四类核心分支均通过受控响应验证 |
| `tools/dev_check.py --work-item FEAT-020` | 142 项 Windows 单元全部通过；无新增语言问题。70 条存量 Ruff、52 个存量未格式化文件仍在基线中，不宣称全库严格通过；未扩大基线 |
| 版本排序与无效数据 | rc.2/rc.10/正式版、数值 MINOR、v 前缀、构建元数据、历史非法标签、空列表、草稿、未发布/未来日期、无效发布时间通过 |
| 网络与分页 | 更高版本在后页可发现；短页 next 分页、超页/超体积、错误 JSON/列表、HTTP 403/429/500、重定向、连接错误与超时均不会虚报最新版；只请求官方固定 API |
| 缓存与非阻塞 | 24 小时成功缓存、主动刷新、15 分钟失败/unknown 冷却、过期标记、保留旧成功目标且 stale=true、并发共享、调用取消/服务退出通过；挂起网络时能力、启动状态和建模入队路径均在单元受控环境中及时返回 |
| `tools/test_update_check.py --output build/feat020-mcp-live-final.json` | 真实 stdio MCP / auto 模式通过：82 个工具、外部访问注解、instructions、同源接口契约、版本和运行源码身份通过；GitHub 最高有效发布为 0.2.6，is_prerelease=true，官方源码 ZIP 链接正确 |
| `tools/test_update_check.py --classic --output build/feat020-mcp-classic.json` | 真实 stdio MCP / legacy 模式相同更新接口通过；此轮在最后发布时间校验回归前执行，逐轮实际指纹保留，不冒充最终源码的全量原生验收 |
| `tools/package.py --output build/FEAT-020-development-source.zip` / `tools/package_seeds.py --output build/FEAT-020-development-seeds.zip` | 开发包白名单与许可核对通过，包含 update_check.py；九种子包校验通过且与原 0.2.6 包一致。开发 ZIP 不是新 Release 附件 |
| 全新目录解压后运行 `tools/dev_check.py --work-item FEAT-020` | 开发包实际解压验证；代码/配置指纹与对应源码一致，无本机配置、任务、二进制或 SDK 文件混入。最终包复核结果另见结构化证据 |

并发共享是开发者实际运行多个异步请求的确定性回归，不等于 WorkBuddy 多客户端并发验收。OS 真实断网、GitHub 实际限流没有实施；HTTP 响应模拟和进程内故障注入分别标识，不能换名为真实断网。

## 本机 Creo 12 集成结果

以下使用新的 E 盘开发源码进程、真实 stdio MCP 和已有匹配 SDK。`--network-failure` 在新服务进程内注入更新请求失败，未修改操作系统网络、安装配置或模型。

1. `tools/test_update_check.py --network-failure --create --retry-startup --output build/feat020-mcp-failure-creo12.json`：更新接口返回 failed、无目标、原始受控错误；三个接口缓存一致且持续可调用。显式启动重试后 Toolkit 返回 -4，未在本轮窗口内就绪，建模 unverified。
2. `tools/test_update_check.py --network-failure --create --output build/feat020-mcp-failure-creo12-recheck.json`：保留已有 Creo 会话重查，终态 timeout；更新失败数据保持独立，不宣称更新成功。
3. 查看并恢复最小化 Creo 窗口，主界面显示 12.4.0.0，无需处理的对话框；`tools/test_update_check.py --network-failure --create --retry-startup --output build/feat020-mcp-failure-creo12-visible.json` 仍为 timeout，未取得 Toolkit 就绪。

三个尝试均未提交任何建模任务，因此没有 job_id/model_id、几何、revision 或保存重载成功数据。保留已有 Creo，不关闭或重复提交未知任务。现象与已登记 [BUG-005](../work-items/BUG-005.md) 一致，未确认根因；本项不将其归因于版本、许可或更新功能，也未修复启动代码。真实联网和受控失败两种更新条件下均存在连接失败，不能由此宣称“失败更新下原生建模通过”。

当前聊天挂载的 MCP 仍为 C 盘旧安装 0.2.6 / 81 个工具，未用于冒充新功能验收；本轮通过新的 E 盘 stdio 服务验证了更新接口。WorkBuddy 验收前须由测试发起者部署本项源码并重启目标 MCP，提示词见 [交接材料](FEAT-020-WorkBuddy-test.md)。

## 尚待完成

本机 Creo 12 在真实 Toolkit 就绪环境下完成网络失败期间的小零件、400 mm³ 几何和保存重载验收；外部 Creo 10 证据由协助者补录。WorkBuddy 最终 MCP 报告、客户端实际提醒展示与会话去重、真实网络故障/公开高版本场景、0.3.0 发布及发布后的更高版本发现尚未验证。

本次未升级服务版本、创建 GitHub Release 或覆盖任何旧附件。发布需在验收结论明确后同步版本、清单、说明和打包；旧安装必须先手动升级一次，后续才可收到版本提醒。条目保持验收中，开发测试与外部最终验收不互相替代。
