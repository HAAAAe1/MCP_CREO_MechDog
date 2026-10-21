# DEV-040：隔离补测复核与阶段收尾

日期：2026-10-18；复核时间：03:01 UTC（11:01 Asia/Shanghai）。本文件是开发者复核与状态裁定，与 WorkBuddy 原始报告分开保存。

## 来源与身份

- 用户提供的[隔离报告](DEV-040-isolated-contract-2026-10-18.md)，SHA256 `ce445774d21795ae14444af4e8d42db5e6dba3723d9faca8948d782f58053b7a`，原件未改。
- [首轮黑盒报告](DEV-040-workbuddy-blackbox-2026-10-18.md)，SHA256 `cc91a3d251f7e92fa05b0fe2b4307760256ba2db38792f5eecf49416584a9e4d`，原件未改。
- 当前分支 `codex/dev-040-offline-recovery`，基线提交 `f8796737a8da34622f7bfe3a3b44c41de3019f29`，工作区 dirty；提交号不能单独代表修复后的受测源码。版本仍为 0.3.5，未合入 main、未发布。
- 本机 Windows 11 / 26100、Python 3.12.14。此次没有 Creo/SDK/编译器运行验证；没有新建模作业，没有 Toolkit 调用。

报告中的数据根为 `build/dev040-blackbox/run-1792290959119795300-7f9a8ae8`，四工具、`actual_creo_verified=false`、部署未变化。部署摘要 `e084eaffccd415af3cc931bb608b8f18c8c5be5ab5d63e4177533dfac47c9a9d` 与本次开发者计算一致；server/bridge/reconciliation 三个公开源码摘要与[准备记录](DEV-040-fixture-preparation-2026-10-18.md)一致。它们支持隔离 Python 服务身份，不能证明原生构建或真实 Creo 行为。

## 报告裁定

| 场景 | 实际作业 | 裁定及边界 |
| --- | --- | --- |
| A：原生前拒绝 | `287bacd464ec468892d73ab0e2fc7faf` | 接受后 `failed/reconciliation_refused/session_selection_changed/before_native`，自身 recovery_pending 释放且模型状态/revision/原 pending 不变；实际 Python 拒绝路径成立，session selection 为夹具构造 |
| B：合成原生后未知 | `45bf13315dfb4fea92e97361cdb00ee8` | `unknown_outcome/reconciliation_unconfirmed/native_worker_started`，占位保留且阻断后续动作；result 明示无实际 native worker，只支持 Python 契约 |
| C：合成成功 | `112a3f3e26b9438d9c64c67366a71ff4` | 省略 expected_pending_job_id 后成功，模型 abandoned/revision 0，pending 与 recovery_pending 为 null，resolution 指向本作业；没有真实 CAD 文件或几何 |

三者 compact/full 关键字段一致，原参数与 key 的幂等重放返回同一作业和既有时间戳。清单只有三份原作业及三份恢复作业，支持未创建重复恢复作业。报告没有执行重叠调用，并发/busy 保持未验证；内部锁/持久化也不能由此证明。

报告没有附每次工具调用的完整原始 JSON，当前属于含输入、标识、字段和时间线的汇总证据，不是完整协议逐帧记录。可依据已列出的关键字段接受本次有限契约结论，不扩展到未列出的响应字段。

## null 形态与连接名偏差

报告的空串被精确拒绝；自述显式 JSON null 的调用也收到 `received ''`；字面字符串 `"null"` 被接受；C 的省略字段形态成功。错误只证明业务校验时收到空串，不能仅凭本报告定位它在客户端、适配层或 SDK 的具体转换位置。

该现象与 [BUG-055](../work-items/BUG-055.md) 已记录的调用路径差异一致。本次开发者通过标准真实 stdio 客户端复核：显式 JSON null 和省略都成功，空串/空白精确拒绝，字面 `"null"` 经当前 SDK 预解析兼容。当前没有服务端 null 退化的新缺陷证据，无需放宽空串校验。使用本客户端且 inspect.pending_job=null 时优先省略字段；pending 非空必须传精确原 ID，不能省略。字面字符串的兼容行为不作为推荐输入。

报告自述使用 `MCP_CREO_MechDog_test`，与项目本机只启用 `MCP_CREO_MechDog_dev` 的约定不同。源码/数据根/夹具标识支持此次隔离身份，但本次没有读取或修改 WorkBuddy 配置，不能确认具体注册过程或其他服务是否启用。本条是连接配置偏差，不作为服务代码缺陷；后续应按项目约定使用 `_dev`，恢复正常连接时核对公开工具与部署身份。

## 开发者复核

本次命令：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_reconciliation_mcp tests.unit.test_dev040_blackbox_fixture -v
```

12/12 通过，耗时 32.162 秒。使用各测试自己的新独立根，未消费、清理或重提交 WorkBuddy 已使用的夹具作业，未读取生产模型。测试属于开发者协议/夹具回归，不能替代 WorkBuddy 或实机证据。

本次重新计算 `tools.dev_check.collect_styles` 的源码集合 SHA256 为 `92002a70bf4cfb4b39c557bc20a8773ae643035ff070a11828e440e7d4a26b2b`，与先前 `build/dev040-fixture-development-check.json` 完整检查的受测源码一致。因此引用此前 356/356 及默认语言检查通过，不声称本次重跑了全套或 strict 检查。存量风格问题仍为 35 条 lint、25 个未格式化文件；基线未变。机器可读复核保存在本机生成物 `build/dev040-report-review.json`。

## 状态与剩余工作

按用户要求收尾 [DEV-040](../work-items/DEV-040.md)，将其作为“本机离线诊断交付与 BUG-059 Python/MCP 修复阶段”完成并归档；[BUG-059](../work-items/BUG-059.md) 按该已测修复范围转已修复。G6 核心契约缺口已由本轮补齐，不再因已 abandoned 的旧模型阻塞这个范围。

这不是原始所有目标均已实现：G2 未证明外部 Errno 13 的具体机制，G3 未改锁实现，[BUG-057](../work-items/BUG-057.md) 继续待原环境复现；[BUG-058](../work-items/BUG-058.md) 的实机 -11 原因未定。真实会话切换/中断、原生恢复、几何、保存重载、回滚、通道并发与其他版本均无本轮结果，[FEAT-018](../work-items/FEAT-018.md) 等原卡保留其范围。初轮 TTL 证据保留原轮次，本轮未重测。未结束/重启 Creo、未解除任何实际 unknown 保护。
