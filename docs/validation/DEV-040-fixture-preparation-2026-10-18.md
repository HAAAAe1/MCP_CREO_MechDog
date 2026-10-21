# DEV-040：专用模型与隔离验收夹具准备

日期：2026-10-18，Asia/Shanghai。按用户“构造模型让测试继续、推进关闭 DEV-040”的要求执行。服务版本仍为 0.3.5，开发基线 `f8796737a8da34622f7bfe3a3b44c41de3019f29`，工作区 dirty；没有合入 main 或发布。

## 真实块体方案与实际门槛结果

当前恢复逻辑没有要求模型必须 unknown：新建正常 `ready` part，只要保存基线摘要已验证、inspection 非空且历史 runner/worker 可证明停止，`restore_baseline` 即可用。最小块体为 20 × 10 × 5 mm、体积 1000 mm³；输入已保存为 [examples/dev040_recovery_baseline.json](../../examples/dev040_recovery_baseline.json)，通过生产 schema 校验。此模型可做正常恢复、幂等、compact/full 与保存重载，不能单凭几何稳定触发 admission 后、原生派发前的拒绝。

准备过程没有产生真实模型或建模作业：

| 阶段 | 观察 | 实际动作 |
| --- | --- | --- |
| Codex 已连接 dev 的公开能力核对 | E 盘服务，但 `source_changed_since_startup=true`；启动时 server/bridge/reconciliation 摘要仍为修改前版本 | 未从该旧实例提交建模 |
| 当前 E 盘源码的一次性 stdio 开发者连接 | 核对三个源码摘要与本轮一致；内存配置 `auto_start_creo=false`，未改客户端或磁盘配置 | 只检查已有会话；构建/验证执行器后探测超时 |
| 10:32:21（02:32:21Z） | `connected=false`、`connection_state=probe_timeout`、预算 9 秒；匹配的 Creo 12.4 parametric/xtop 进程仍在 | 未执行 execute_plan，停止后续建模 |
| 用户确认 | 用户确认“界面正常，可操作” | 再做一次有界核验；该连接还禁用了后台 startup/update 协调，只调用显式会话状态 |
| 10:35:06（02:35:06Z） | 再次 `probe_timeout`，9 秒，同一 Creo 进程身份 | 未执行 execute_plan，停止后续真实 Toolkit 调用；未 retry、结束/重启 Creo 或清保护 |

两次公开响应均说明仅停止本次探测 helper，不关闭 Creo。界面可操作与 Toolkit 通道可用是两个观察，当前不能把正常界面写成建模通过；本轮不据此认定超时根因或更改 BUG-056 的历史结论。

开发者完整输入与响应保存在 `build/dev040-model-preparation/evidence.json`、`build/dev040-model-preparation/attempt2/evidence.json`，对应执行输出 `execution.log`、`attempt2-execution.log`。两次均无 creation_job_id/model_id；没有借用或更改旧 abandoned/unknown 模型。上述客户端为开发者 Python stdio，不能标作 WorkBuddy 执行。

## 已构造的离线模型记录

为避免依赖真实会话，在 [tools/dev040_blackbox_fixture.py](../../tools/dev040_blackbox_fixture.py) 提供独立、持久的 MCP 契约夹具。它使用实际生产工具的 schema、调用适配、恢复准入、执行前校验、文件登记、轮询和幂等逻辑，只在下述边界替代前置条件：

- 模型与原作业登记为合成数据，owner 使用本机已证明不存在的 PID；没有 PRT 或真实几何。
- 构建前置替换为不存在、不可执行的 marker；部署绑定使用明确的夹具/Python 摘要，不冒充原生构建身份。
- A 仅改变恢复 runner 内的夹具会话选择，实际进入生产 `_check_execution` 并拒绝；原生边界设硬守卫，进入即失败。
- B/C 仅替代 `_native`，明确返回 `synthetic_native_result=true`、`actual_native_worker_started=false`。B 的 worker_started 是合成标记，不是真实进程证据。

新准备根为：

```text
E:\Projects\MCP_CREO_MechDog\build\dev040-blackbox\run-1792290959119795300-7f9a8ae8
```

配置和清单：

- [client-config.json](../../build/dev040-blackbox/run-1792290959119795300-7f9a8ae8/client-config.json)：仍只有 `MCP_CREO_MechDog_dev`，E 盘 Python、`python -m tools.dev040_blackbox_fixture --serve` 与明确 cwd/data root。
- [fixtures.json](../../build/dev040-blackbox/run-1792290959119795300-7f9a8ae8/fixtures.json)：公开场景/模型清单。该生成目录是本机测试数据，不进入源码包或附件。

| 场景 | 新 model_id | 初态与用途 |
| --- | --- | --- |
| A：before_native_refusal | `2fecee0e101147cbb73ce5e46f017386` | failed/rev 0、无基线、pending null、非 abandoned；abandon_new 可用。预期接受后 failed / reconciliation_refused / before_native，释放自身 recovery_pending |
| B：synthetic_native_unknown | `e9d6aff25a2c4c818f4cbe3d1e042f3d` | unknown/rev 0、原 pending 非空；预期合成原生后 unknown，保留原 pending 与本次 recovery_pending |
| C：synthetic_success | `3d4bd6f746bf44eabe446e4ba6cc57eb` | failed/rev 0、pending null；预期合成成功后 abandoned，用于成功幂等与省略字段 |

准备时三个动作均未被消费，服务未常驻启动，用户客户端配置未修改。WorkBuddy 需从公开 capabilities 获取 ID、从本次 inspect 取新 token，不能复用旧模型或报告中的过期凭证。

## 隔离与防护

服务仅公开 capabilities、reconcile_model、get_job、list_jobs 四个工具，明确 `fixture_mode=dev040_isolated_mcp_contract_v1`、`actual_creo_verified=false`、`native_channels=0`、实际数据/锁根和替代边界。模型/作业/锁全部在新根内；生产 jobs/models/锁和本机配置不读取或改写。

启动器和更新器不启动；build、session、native environment、live 与原生调用封闭；subprocess 仅允许精确匹配、属于清单模型的自有 Python 恢复 runner，runner 内所有外部进程执行再封闭。超出四工具的调用不能进入生产建模。新增路径必须在 `build/dev040-blackbox/` 下且不含链接/联接；prepare 不覆盖已有运行根。

独立审阅未发现这四个公开工具可到达真实 Toolkit 或生产运行目录的阻断问题。新 stdio A 覆盖 pending=null；非空 pending 的确定性清理、清理失败、占位换主等仍由既有恢复单测覆盖，不把这些统称为新增夹具已经黑盒测过。

## 本轮验证

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_dev040_blackbox_fixture tests.unit.test_reconciliation_mcp -v
.\.venv\Scripts\python.exe tools\dev_check.py --work-item DEV-040
```

针对性 12/12（新增 4 项、既有真实 stdio 8 项）通过，Ruff check / format 通过。全量默认开发检查 **356/356** 通过，没有新增语言问题；既有风格基线未改，存量仍为 35 条诊断、25 个未格式化文件，不代表 strict 全绿。实际检查 113 个 Python、21 个 C++ 文件，没有原生运行验收。

全量检查起始时间 10:37:16（02:37:16Z），源码集合指纹 `92002a70bf4cfb4b39c557bc20a8773ae643035ff070a11828e440e7d4a26b2b`，commit 为上述基线且 dirty。完整输出 `build/dev040-fixture-development-check.log`，JSON 报告归档为 `build/dev040-fixture-development-check.json`、`build/dev040-fixture-unit-test-report.json`。

| 新增文件 | 原字节 SHA256 |
| --- | --- |
| tools/dev040_blackbox_fixture.py | `225b983aca28a2d0c857db86b162a27fe249534bacb141c0a1807bd5800f2376` |
| tests/unit/test_dev040_blackbox_fixture.py | `0b8761952be8a408dc0c91695a0681cbc44d138dcce34b31ff8b825ed8c02e17` |

准备清单的 fixture deployment 为 `e084eaffccd415af3cc931bb608b8f18c8c5be5ab5d63e4177533dfac47c9a9d`；它约束夹具及相关 Python 源码，不是 Git 提交或原生二进制身份。生产 server/bridge/reconciliation 摘要保持前轮对应关系。

## WorkBuddy 与关闭边界

[补测交接提示词](DEV-040-WorkBuddy-fixture-test-2026-10-18.md)已准备并提供具体配置；当前没有本夹具的 WorkBuddy 执行结果。开发者的 12/356 项测试不能代替这份报告，尚不关闭 DEV-040。

若 WorkBuddy 在身份/目录/源码均相符的四工具连接上完成 A/B/C、幂等和 compact/full 对照，可据此验收本轮 Python/MCP 终态及占位行为；真实 Creo 会话变化/中断、几何/保存重载、生产通道并发仍未验证。BUG-057 原环境的实际 open 失败根因仍未定，必须保留在独立 BUG-057 卡；本执行卡若按已交付阶段收尾，应明确“本机诊断交付与 BUG-059 Python 修复”范围，不宣称 BUG-057 已修复，也不自动关闭 FEAT-018 完整恢复验收。
