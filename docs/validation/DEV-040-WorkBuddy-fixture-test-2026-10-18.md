# DEV-040：WorkBuddy 隔离 MCP 契约补测交接

日期：2026-10-18。状态：交接草案，尚无本文件对应的 WorkBuddy 执行结果。

本轮真实会话前置探测返回 `probe_timeout`，未创建新的真实模型。停止新增 Toolkit 连接、结束/重启 Creo、处理历史 unknown 保护的限制继续有效。本交接使用独立数据根目录中的合成模型，补测 DEV-040 的 MCP/Python 恢复契约；不将合成原生结果记作真实 Creo 验收。

## 发起者准备

本节由开发者/发起者执行，不交给 WorkBuddy 运行。WorkBuddy 不读取仓库、配置或生成文件，也不运行下述命令。

```powershell
.\.venv\Scripts\python.exe -m tools.dev040_blackbox_fixture --prepare
```

准备器在 `build/dev040-blackbox/` 下创建新的独立运行目录，并生成 `fixtures.json` 与 `client-config.json`。每次补测使用新目录；不覆盖旧目录，不把生产 `jobs/`、`models/` 或锁文件复制进去。发起者用生成的配置将专用测试客户端的注册键 `MCP_CREO_MechDog_dev` 指向夹具服务；同一客户端不同时启用另一个同名生产连接。配置中的 `--serve --data-root` 由客户端启动服务，无需手动运行第二个服务。

发起者向 WorkBuddy 提供本文件下方提示词、预期的隔离数据根目录及本轮生产 Python 源码摘要映射。模型 ID 从公开 `creo_capabilities.fixtures` 获取，不硬编码历史模型 ID。

夹具仅保留四个公开工具：`creo_capabilities`、`creo_reconcile_model`、`creo_get_job`、`creo_list_jobs`。它绕开构建前置，禁止真实原生/会话调用；A 在恢复 runner 中改变夹具会话选择，进入实际 Python 执行前校验；B/C 替代原生边界并明确返回合成结果。夹具部署摘要与生产原生构建身份是两个不同证据。

## 交给 WorkBuddy 的提示词

---

只使用已连接的 `MCP_CREO_MechDog_dev` 公开 MCP 工具，执行 DEV-040 的隔离契约补测。不要查看源码、Git、本机配置、日志或生成文件，不运行 Python、单元测试、开发脚本或源码探针。不调用 Creo 会话/环境/建模工具，不连接、结束或重启 Creo；不操作历史模型，不删除或清理任何保护。

本次使用合成模型及合成原生结果，只能给出“隔离 MCP/Python 契约”结论。不要把 `worker_started=true`、消息中的 session changed、合成成功或合成文件证据写成真实原生执行、真实会话变更、真实几何、保存重载或回滚通过。

### 1. 先确认夹具身份

先调用 `creo_capabilities`，并保存完整返回。只有下列检查均符合才继续 apply：

- `fixture_mode="dev040_isolated_mcp_contract_v1"`。
- `actual_creo_verified=false`；`synthetic_boundaries` 明确列出合成模型、替代构建前置及 B/C 的原生替代边界。
- `runtime.data_root`、`runtime.lock_root` 均为发起者提供的本轮专用目录，位于 `E:\Projects\MCP_CREO_MechDog\build\dev040-blackbox\` 下。
- `runtime.job_root`、`runtime.model_root` 分别位于该专用目录的 `jobs`、`models` 下；`scheduling.native_channels=0`、`scheduling.fixture_lock_channels=1`。
- `runtime.fixture_source_changed=false`，`runtime.source_changed_since_startup=false`；保存 `runtime.fixture_deployment` 和 `runtime.fixture_deployment_at_prepare`，二者应相同。
- `runtime.production_server_entry` 指向本项目 `server.py`。将 `runtime.source_fingerprints_at_startup` 中的 `server.py`、`bridge.py`、`src/creo_mechdog/reconciliation.py` 与发起者提供的本轮生产 Python 摘要逐项核对。未提供映射或字段缺失时，报告“源码对应关系无法确认”，不根据相同版本号推定一致。
- 可见工具和 `allowed_tools` 为上述四项；`fixtures` 应包含 A/B/C 三种 `scenario`、各自的 `model_id`、`original_job_id` 和 `action="abandon_new"`。

本次受测生产 Python 入口/恢复逻辑的摘要映射如下（按公开接口相同口径将 CRLF 规范为 LF 后计算 SHA256）。它对应 DEV-040 当前工作区，不能单凭该映射证明原生构建或生产运行环境；夹具文件自身变化另由 fixture deployment 摘要约束。

| 公开源码键 | 预期 SHA256 |
| --- | --- |
| `server.py` | `e4872eca80f2ecd29451afa732a75f287a6d0c94018fc953e019c5bd55874f07` |
| `bridge.py` | `1db90acadebf227a5ecee83218dc8ae8ca64dffd583af6ebd7f03d013fb7916d` |
| `src/creo_mechdog/reconciliation.py` | `e5c98867dd6f37587d104fe8c57e28c9711141c03ea61c10a5c653380f5eafb4` |

身份不符、目录不符、源码已变化或夹具标记缺失时停止 apply，报告实际返回并交回发起者。不要调用其他工具试探是否误连生产服务。

### 2. 每个场景的取证规则

从 `creo_capabilities.fixtures` 选择相应场景，调用 `creo_reconcile_model(model_id=该场景ID, mode="inspect", live=false)`。保存 `status`、`revision`、`pending_job`、`recovery_pending`、`original_job_id`、`owners`、`actions`、`evidence_token`、`evidence_at`、有效期。各场景只使用其自己的凭证。

执行 apply 前必须看到 `actions.abandon_new.available=true`、`recovery_pending=null`，并且 owners 均可证明停止。动作不可用或前置与下表不符时，该场景记“未验证”；不修改文件或制造故障。

| 场景 | `scenario` | inspect 的初始预期 | 授权动作 |
| --- | --- | --- | --- |
| A | `before_native_refusal` | `status="failed"`，revision 0，pending_job null | `abandon_new`，进入实际 Python 执行前拒绝 |
| B | `synthetic_native_unknown` | `status="unknown_outcome"`，revision 0，pending_job 等于该场景 original_job_id | `abandon_new`，仅观察合成原生后未知保护 |
| C | `synthetic_success` | `status="failed"`，revision 0，pending_job null | `abandon_new`，仅观察合成成功与幂等；可选 |

apply 的 `expected_revision` 与 `expected_pending_job_id` 必须来自本次 inspect，不写死 revision 或 pending。A 的主用例请实际发送 JSON null；B 原样传递非空 pending_job；C 可省略该字段，以观测 pending 为 null 时的省略契约。`evidence_token` 使用本次 inspect 返回值，`idempotency_key` 使用本轮唯一的 8～80 字符字母/数字/下划线/连字符键。

每次 apply 一旦返回 job_id，只用 `creo_get_job(job_id=该ID, detail="compact")` 轮询该作业；不重新提交动作来催促执行。到终态后获取同一 job_id 的 full，并再次 inspect 对应模型。终态为 failed/unknown_outcome 时也保留原始返回，不手动清理。

### 3. 场景 A：已接受、原生前确定性拒绝

对 A 按上述规则 apply。记录确实接受了新恢复 job_id，随后只轮询它。预期终态与前后状态为：

- `status="failed"`、`stage="reconciliation_refused"`。
- `reason="session_selection_changed"`、`failure_phase="before_native"`，具备原始 `message` 与 `finished_at`。
- `recovery_pending_released=true`，无 `recovery_pending_cleanup_error`。若实际出现清理错误，报告失败/异常，不据此清保护。
- 后续 inspect 的 `status`、revision、pending_job 与 apply 前相同，`recovery_pending=null`，没有把 A 变成 abandoned。
- compact/full 的 job_id、status、stage、reason、failure_phase、释放字段、清理错误字段（有则比较）和 finished_at 一致。

用**完全相同的 apply 参数**与同一 idempotency_key 再调用一次，包含原来的 token、revision、pending 与 action；预期返回同一 job_id 和既有终态，不接受第二个恢复作业。重复查询不是一次新的恢复，不要为这次幂等查询更换 token。可用 `creo_list_jobs` 和前后 inspect 辅助记录没有第二个作业/占位。

需要再发起另一项恢复时，必须重新 inspect，使用新 token 与新 key；本提示词没有要求反复重交 A。

### 4. 场景 B：合成原生后未知保护

对 B 按上述规则 apply，准确传入其非空 pending_job。预期终态为：

- `status="unknown_outcome"`、`stage="reconciliation_unconfirmed"`。
- `reason="native_outcome_unconfirmed"`、`failure_phase="native_worker_started"`、`recovery_pending_released=false`。
- full 的 `result.synthetic_native_result=true`、`result.actual_native_worker_started=false`；`result.failed_stage="recovery_abandon_new"`，保留原始错误消息。这里的 native_worker_started 是夹具置位，不是实际原生执行证据。
- 后续 inspect 的原 status、revision、原 pending_job 保持不变；`recovery_pending` 等于本次恢复 job_id，不能为 null。
- compact/full 的关键终态、原因、阶段、保护字段和 `result.failed_stage` 一致；允许 full 独有合成标记等详细字段，不要求全部响应逐字相同。

用完全相同参数、原 token 与原 key 进行一次幂等查询，应返回同一 job_id 和既有状态。随后只记录保护，不再用新 key 发起动作，不选择其他恢复动作，不清理 B 的 recovery_pending。保留它作为未知结果保护证据。

### 5. 场景 C：合成成功、幂等与省略字段（可选）

对 C 按上述规则 apply；inspect 返回 pending_job 为 null 时，本次省略 `expected_pending_job_id`。预期恢复作业 `succeeded`、`stage="reconciliation_committed"`，模型变为 abandoned、revision 保持 0、pending_job 与 recovery_pending 均为 null；后续 inspect 的 `resolution.recovery_id` 指向本作业。

获取 compact/full，核对共同的 job_id、status、stage、revision、action 与幂等键。full 的 `result.synthetic_native_result=true`、`result.actual_native_worker_started=false` 应明确记录；本场景没有真实 PRT、几何或保存重载。

用完全相同参数、原 token 与原 key 重复 apply，应返回同一已成功 job_id。此时模型已 abandoned，正常新动作不可用；不要继续使用这个模型构造新恢复。

### 6. 可选输入与并发检查

可在 A 主 apply 之前，用有效 inspect 凭证分别检查 `expected_pending_job_id=""` 和字面字符串 `"null"`，各用独立 key，并完整记录工具实际收到的输入、返回和是否接受 job_id。空串预期直接拒绝；字面字符串的结果按本客户端实际调用记录，不根据错误文字推断 SDK/适配层或服务在哪一层归一化。若意外接受作业，立即按其 job_id 轮询并记录，后续 A 主用例重新 inspect。

显式 JSON null 以 A 的实际调用为证；省略形态以 C 的实际调用为证；未执行的形态不记通过。凭证过期用例如不重新执行，记为“本轮未重测”，不能用之前报告补成本轮记录。

busy 只有在确实发出两个重叠的 MCP 调用时才评价，并保留时间与原始响应；没有实际重叠就记“并发未验证”。夹具作业很快，顺序调用都成功/失败不证明 busy 契约。即使隔离夹具观察到 busy，也只支持本隔离锁/准入路径的结论，不替代生产 Toolkit 通道及 BUG-057 原环境锁竞争复现。不要通过占用/删除锁文件制造 busy。

### 7. 报告要求

为每个实际执行的场景记录：公开身份、fixture/data root、源码摘要对应关系、完整输入与原始响应、model_id、original_job_id、恢复 job_id、token 与 key 的复用关系、终态、compact/full 对照、前后 status/revision/pending_job/recovery_pending、幂等结果。

报告分清以下结论：

- A 的 MCP 接受、实际 Python 执行前拒绝、公开终态与占位释放字段。
- B/C 的 MCP/Python 契约观测与合成原生边界；不宣称实际原生行为。
- 未执行的并发、内部文件持久化/锁实现、真实会话变更/中断、几何、保存重载、回滚、其他 Creo 版本均“未验证”。

不要仅因这份夹具报告通过就写“DEV-040 整卡关闭”或“真实 Creo 验收通过”。发起者依据任务卡的范围、开发者证据和剩余实机事实分别裁定状态。

---

本文件不改写[上一轮 WorkBuddy 黑盒报告](DEV-040-workbuddy-blackbox-2026-10-18.md)。开发者准备/验证结果、本轮 WorkBuddy 实际执行结果与真实 Creo 结果应分别留证；任务状态见 [DEV-040](../work-items/DEV-040.md)。
