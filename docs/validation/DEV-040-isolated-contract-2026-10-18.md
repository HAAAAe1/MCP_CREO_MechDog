# DEV-040 隔离夹具契约补测记录（2026-10-18）

## 0. 范围与边界

- 通道：仅 `MCP_CREO_MechDog_test` 已连接的 4 个公开工具（`creo_capabilities`、`creo_reconcile_model`、`creo_get_job`、`creo_list_jobs`）。
- 未查看源码、Git、本机配置、日志或生成文件；未运行 Python、单元测试、开发脚本或源码探针；未调用 Creo 会话/环境/建模工具；未连接、结束或重启 Creo；未操作历史模型；未删除或清理任何保护。
- 夹具标记 `actual_creo_verified=false`，模型与原生结果均为合成。**本记录只支持“隔离 MCP/Python 契约”结论**，不构成真实原生执行、真实会话变更、真实几何、保存重载或回滚证据。

## 1. 夹具身份与源码对应关系

| 检查项 | 实际返回 | 判定 |
| --- | --- | --- |
| `name` / `version` | `MCP_CREO_MechDog` / `0.3.5` | 记录 |
| `fixture_mode` | `dev040_isolated_mcp_contract_v1` | 符合 |
| `actual_creo_verified` | `false` | 符合 |
| `synthetic_boundaries` | 5 条：合成模型/作业记录与无 CAD 文件；部署绑定用夹具/Python 源码摘要而非原生构建身份；runner 构建前置替换为不存在、不可执行的标记；A 仅 session selection 不同而真实 Python 拒绝路径执行；B/C 替换 `reconciliation._native`、`worker_started` 为合成且无 worker | 符合 |
| `runtime.data_root` | `...\build\dev040-blackbox\run-1792290959119795300-7f9a8ae8` | 符合（本轮专用目录） |
| `runtime.lock_root` | 同上目录 | 符合 |
| `runtime.job_root` / `model_root` | 该目录下 `jobs` / `models` | 符合 |
| `scheduling.native_channels` | `0` | 符合 |
| `scheduling.fixture_lock_channels` | `1` | 符合 |
| `scheduling.scope` | `Isolated fixture OS lock; real Toolkit channel not tested` | 记录 |
| `fixture_source_changed` / `source_changed_since_startup` | `false` / `false` | 符合 |
| `fixture_deployment` / `_at_prepare` | `e084eaffccd415af3cc931bb608b8f18c8c5be5ab5d63e4177533dfac47c9a9d`（两者相同） | 符合 |
| `production_server_entry` | `E:\Projects\MCP_CREO_MechDog\server.py` | 符合 |
| `tool_count` / `allowed_tools` | 4 / 恰为四项 | 符合 |
| `fixtures` | A/B/C 三场景，各含 `model_id`、`original_job_id`、`action=abandon_new` | 符合 |

源码摘要逐项核对（与发起者映射相同口径）：

| 公开源码键 | 夹具值 | 预期值 | 判定 |
| --- | --- | --- | --- |
| `server.py` | `e4872eca80f2ecd29451afa732a75f287a6d0c94018fc953e019c5bd55874f07` | 同 | 一致 |
| `bridge.py` | `1db90acadebf227a5ecee83218dc8ae8ca64dffd583af6ebd7f03d013fb7916d` | 同 | 一致 |
| `src/creo_mechdog/reconciliation.py` | `e5c98867dd6f37587d104fe8c57e28c9711141c03ea61c10a5c653380f5eafb4` | 同 | 一致 |

该映射仅对应 DEV-040 当前工作区源码，不代表原生构建身份或生产运行环境。

## 2. 场景 A：`before_native_refusal`

模型 `2fecee0e101147cbb73ce5e46f017386`，`original_job_id=6262f11bbbe54ba18fe92ee58822ed65`。

### 2.1 前置 inspect（token 1）

`2026-10-18T02:46:56.856055+00:00`，`evidence_token=4c5942f29eba465f8a68d3b75960eaeb`，有效 600 s。

- `status=failed`、`revision=0`、`pending_job=null`、`recovery_pending=null`、`resolution=null`。
- `owners[0].stopped=true`（runner 与 worker 均 `alive=false`，`windows_error=87`）。
- 仅 `abandon_new.available=true`；其余三个动作因缺少 baseline/candidate/live 证据不可用。

### 2.2 可选输入形态检查

| 形态 | 传入 | 结果 |
| --- | --- | --- |
| 空串 | `expected_pending_job_id=""`，key `dev040-a-empty-pending-01` | 工具错误：`expected_pending_job_id must be the pending job id returned by inspect, or null when inspect returned pending_job=null; received ''`；**未创建 job** |
| 字面字符串 | `expected_pending_job_id="null"`，key `dev040-a-literal-null-01` | **被接受**，创建 `job_id=287bacd464ec468892d73ab0e2fc7faf`（`created_at=02:47:05.309421Z`，`stage=intent_persisted`） |
| 显式 JSON null | `expected_pending_job_id: null`，key `dev040-a-main-null-01` | 工具错误，内容同上，`received ''`；**未创建 job** |

观察：本次调用路径下，显式 JSON null 到达校验时表现为空串被拒，而字面 `"null"` 被归一化为 null 接受。无法依据错误文本判定归一化发生在客户端适配层还是服务端，故不推断层级。被拒调用未消耗 token（同一 token 后续仍可用于字面 null 形态）。

### 2.3 A 实际取证作业（字面 null 形态）

`job_id=287bacd464ec468892d73ab0e2fc7faf`，`idempotency_key=dev040-a-literal-null-01`。

- 终态 compact：`status=failed`、`stage=reconciliation_refused`、`reason=session_selection_changed`、`failure_phase=before_native`、`revision=0`、`recovery_pending_released=true`、`recovery_required=true`、`finished_at=2026-10-18T02:47:05.930462+00:00`、`message="Creo session selection changed after recovery admission"`。
- 无 `recovery_pending_cleanup_error` 字段（未出现清理错误）。
- `recovery.native_result_present=false`、`recovery.automatic_replay_allowed=false`、`recovery.resolution=null`。
- full 与 compact 的 `job_id`/`status`/`stage`/`reason`/`failure_phase`/`recovery_pending_released`/`finished_at`/`message` 完全一致；该作业无 `result` 块（原生结果不存在），不出现合成标记。
- 说明：按夹具边界，A 的拒绝由真实 Python 恢复代码执行，仅 session selection 为 runner 侧构造；该字段不证明真实 Creo 会话变更。

### 2.4 幂等与状态复核

- 用原 token `4c5942f2…`、原 revision 0、原 pending 形态、原 key `dev040-a-literal-null-01` 复放：返回同一 `job_id=287bacd4…`，`created_at`/`finished_at` 与首次完全相同，状态为既有终态，**未接受第二个恢复作业**。
- 中间 re-inspect（`02:47:12.850614Z`，token `c3efd4a9cd7e4fc5a65eb2fa67ce7098`）与终态后 inspect（`02:47:47.163208Z`，token `a68a9f1bc4cb4e7eb6ab4105883cd243`）结果均为：`status=failed`、`revision=0`、`pending_job=null`、`recovery_pending=null`、`resolution=null`、`abandon_new` 仍可用。模型**未被改为 abandoned**，与 apply 前一致。
- `creo_list_jobs` 复查：本轮仅存在 1 个 A 相关 reconciliation 作业，无第二个作业或占位。

## 3. 场景 B：`synthetic_native_unknown`

模型 `e9d6aff25a2c4c818f4cbe3d1e042f3d`，`original_job_id=09719957fb6e455c918809bd3ed14fd6`。

### 3.1 前置 inspect

`02:47:50.688182Z`，token `8e57224dcb1c430dac5a0cac922e8954`：`status=unknown_outcome`、`revision=0`、`pending_job=09719957…`（等于 original_job_id）、`recovery_pending=null`、owners `stopped=true`、`abandon_new.available=true`。

### 3.2 apply（原样传入非空 pending_job）

`job_id=45bf13315dfb4fea92e97361cdb00ee8`，key `dev040-b-apply-01`，`created_at=02:47:54.630784Z`。

- compact 终态：`status=unknown_outcome`、`stage=reconciliation_unconfirmed`、`reason=native_outcome_unconfirmed`、`failure_phase=native_worker_started`、`recovery_pending_released=false`、`recovery_required=true`、`finished_at=02:47:55.448555Z`。
- `result.failed_stage=recovery_abandon_new`，`result.success=false`，保留原始消息 `Recovery refused: Creo session changed since recorded evidence`。
- full 追加：`worker_started=true`、`result.fixture_mode=dev040_isolated_mcp_contract_v1`、`result.synthetic_native_result=true`、`result.actual_native_worker_started=false`。**`worker_started` 为夹具置位，不是实际原生执行证据。**
- compact 与 full 的 `job_id`/`status`/`stage`/`reason`/`failure_phase`/`recovery_pending_released`/`result.failed_stage` 一致。

### 3.3 保护与幂等

- 终态后 inspect（`02:48:04.931296Z`，token `8ddeea36af6c4075a2d62f8662fe4d47`）：`status=unknown_outcome`、`revision=0`、`pending_job=09719957…` 均保持不变；`recovery_pending=45bf1331…`（本次恢复作业，非 null）。
- 同次 inspect 中四个动作全部不可用，理由为 `Previous runner/worker is active or cannot be proven stopped`；新恢复作业的 worker 报 `Native owner identity is unavailable`，即未知保护已生效并阻断后续动作。
- 用原 token `8e57224d…`、原 revision、原 pending、原 key 复放：返回同一 `job_id=45bf1331…` 与既有状态，`created_at`/`finished_at` 不变。
- 未使用新 key 发起其他动作，未选择其他恢复动作，未清理 B 的 `recovery_pending`；保留为未知结果保护证据。

## 4. 场景 C：`synthetic_success`（省略字段形态）

模型 `3d4bd6f746bf44eabe446e4ba6cc57eb`，`original_job_id=5034422602194886ae0a0d68ce19232e`。

- 前置 inspect（`02:48:12.973068Z`，token `9dba7129a95c44d5ba52b3a6ce900478`）：`status=failed`、`revision=0`、`pending_job=null`、owners 停止、`abandon_new.available=true`。
- apply **省略** `expected_pending_job_id`：被接受，`job_id=112a3f3e26b9438d9c64c67366a71ff4`，key `dev040-c-apply-01`。
- compact 终态：`status=succeeded`、`stage=reconciliation_committed`、`revision=0`、`finished_at=02:48:17.921462Z`、`message="Explicit recovery committed; original job history preserved"`。
- full 追加：`worker_started=true`（夹具置位）、`result.fixture_mode=dev040_isolated_mcp_contract_v1`、`result.synthetic_native_result=true`、`result.actual_native_worker_started=false`、`result.message="Synthetic fixture result; no Toolkit or Creo call"`。compact/full 的 `job_id`/`status`/`stage`/`revision`/`action`/`idempotency_key` 一致。**本场景无真实 PRT、几何或保存重载。**
- 终态后 inspect（`02:48:27.476807Z`，token `7bb8654c0ab042cb82ed2a024028c58b`）：`status=abandoned`、`revision=0`、`pending_job=null`、`recovery_pending=null`；`resolution={recovery_id: 112a3f3e…, action: abandon_new, original_job_id: 503442…, original_plan_completion_confirmed: false, resolved_at: 02:48:17.921462Z}`；四个动作均因 `Model is already abandoned` 不可用。
- 幂等：原 token、原 revision、原 key、同样省略字段复放，返回同一 `job_id=112a3f3e…` 与 `succeeded` 既有状态，`created_at`/`finished_at` 不变；未继续用该模型构造新恢复。

## 5. 终态作业清单

`creo_list_jobs(limit=20)`：3 个本轮 reconciliation 作业（A `287bacd4…` failed、B `45bf1331…` unknown_outcome、C `112a3f3e…` succeeded）+ 3 个夹具原始 generic 作业（`6262f11b…` failed、`09719957…` unknown_outcome、`50344226…` failed）。无重复、无额外占位。

## 6. 结论分层

**通过的隔离契约观测**

1. A：MCP 接受恢复作业（字面 null 形态）；作业在 `before_native` 阶段被真实 Python 恢复代码拒绝；公开终态为 `failed/reconciliation_refused/session_selection_changed`；`recovery_pending_released=true` 且无清理错误；模型 `status`/`revision`/`pending_job` 前后不变、未被 abandoned；compact/full 一致；同 token+key 幂等返回同一作业且不新增作业。
2. B：MCP/Python 契约层面，`native_worker_started` 阶段进入 `unknown_outcome`，`recovery_pending_released=false`，`recovery_pending` 指向恢复作业，未知保护阻断全部后续动作，幂等返回同一作业。合成边界明确：`synthetic_native_result=true`、`actual_native_worker_started=false`。
3. C：省略 `expected_pending_job_id` 被接受；提交后模型变 `abandoned`、revision 保持 0、pending 与 recovery_pending 归零、`resolution.recovery_id` 指向本作业；幂等返回同一成功作业。合成边界同上。
4. 输入边界：空串被精确拒绝且不建作业；被拒调用不消耗 token。

**契约反常（需发起者裁定）**

- 本客户端路径下显式 JSON null 被当作空串拒绝（`received ''`），字面字符串 `"null"` 却被接受并建作业。三种形态行为不一致，导致 A 的“显式 null”主用例形态无法在本客户端完成，A 的接受→拒绝证据改由字面 null 形态取得；归一化层级无法从公开返回判定。

**未验证**

- 并发/busy 契约：本轮未发出重叠调用，记为并发未验证；即使观察到也不替代生产 Toolkit 通道及 BUG-057 原环境锁竞争。
- 内部文件持久化与锁实现、真实会话变更/中断、真实原生执行、几何、保存重载、回滚、其他 Creo 版本。
- 凭证过期用例本轮未重测，不引用历史记录补齐。

本记录不构成“DEV-040 整卡关闭”或“真实 Creo 验收通过”。状态裁定由发起者依据任务卡范围、开发者证据与剩余实机事实分别判定。
