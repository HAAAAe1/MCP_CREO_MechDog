# DEV-040 WorkBuddy 黑盒验收记录（2026-10-18）

- 执行方式：仅通过已连接的 MCP 公开工具（`MCP_CREO_MechDog_dev`）做黑盒调用；未读取源码、Git 状态、本机配置或日志文件，未运行 Python 或开发测试脚本，未结束/重启 Creo，未删除任务或模型保护。
- 授权测试模型：`1984b7f4bd9240e6a0c3c7ccbba127c7`（`wb_dev036_t07n_b2c9`，发起者指定，唯一）。
- 执行窗口：2026-10-18T02:06Z ~ 2026-10-18T02:20Z。

## 1. 环境与服务身份（公开接口）

| 项目 | 值 | 来源 |
| --- | --- | --- |
| 服务名称 | `MCP_CREO_MechDog` | `creo_capabilities.name` |
| 服务版本 | `0.3.5` | `creo_capabilities.version` |
| 工具数 | `tool_count=84`，`enabled_tool_count=84`，`unavailable_tools=[]` | `creo_capabilities` |
| 更新状态 | `up_to_date`，latest `0.3.5`，`is_prerelease=true` | `creo_capabilities.update` |
| 运行根 | `E:\Projects\MCP_CREO_MechDog`，`server_entry=E:\Projects\MCP_CREO_MechDog\server.py` | `creo_capabilities.runtime` |
| 启动时源码指纹 | `server.py=e4872eca80f2ecd29451afa732a75f287a6d0c94018fc953e019c5bd55874f07`，`source_changed_since_startup=false` | `creo_capabilities.runtime` |
| Creo 环境 | `C:\Program Files\PTC\Creo 12.4.0.0`，`release_numeric=44`，`ready_to_build=true` | `creo_check_environment` |
| 会话 | `connected=true`，`toolkit_code=0`，`current_model=""`，`launch_state=ready`，`verified_at=2026-10-18T02:06:54.251012+00:00` | `creo_session_status` |
| Creo 进程 | `parametric.exe` pid 22448（created 00:52:31Z）、`xtop.exe` pid 20264，`matches=true`，`uncertain=false` | `creo_session_status.creo_process_snapshot` |
| 对账能力 | `families.model_reconciliation.enabled=true`，四动作齐备，`inspect_requires_creo=false`，`original_plan_replay=false` | `creo_capabilities.families` |
| 通道契约 | `native_channels=1`，`admission=reject_busy_without_creating_a_job`，`queue_guarantees=No public FIFO…` | `creo_capabilities.scheduling` |

**构建身份：无法确认。** 公开接口只提供版本号与启动时源码指纹，不提供"本次部署即 DEV-040 提交"的映射证据。不将版本 0.3.5 视为已部署 DEV-040。发起者亦未提供本次部署身份与可操作会话确认（会话可用性由本次 `creo_session_status` 自行确认）。

## 2. 授权模型基线

`creo_reconcile_model(model_id=1984b7f4bd9240e6a0c3c7ccbba127c7, mode=inspect)`
`evidence_at=2026-10-18T02:08:36.324332+00:00`，`expires_in_seconds=600`，`evidence_token=facb0322fdbc4983aa4c8de65a676972`

- `status=abandoned`，`revision=0`，`pending_job=null`，`recovery_pending=null`
- `original_job_id=0610afdbd4b8495280e476686200d806`，`baseline=null`，`candidate=null`
- `automatic_replay_allowed=false`
- 历史 resolution：`recovery_id=27a5147301e84751b062dbce9c87effe`，`action=abandon_new`，`resolved_at=2026-10-17T14:53:00.944344+00:00`
- **四个动作均不可用**：`restore_baseline` / `accept_saved` / `accept_live` / `abandon_new` 全部 `available=false`，理由统一为 `Model is already abandoned`

该基线直接决定：本模型无法产生"已接受"的恢复作业，因此场景 2、3 以及场景 4 中"已接受作业的幂等重复"在本模型上不具备可执行条件。

## 3. 场景 1：准入前过期凭证 —— **通过**

| 步骤 | 输入 | 原始返回 |
| --- | --- | --- |
| inspect #1 | `mode=inspect`（无 live） | token `facb0322…`，`evidence_at 02:08:36.324Z`，`expires_in_seconds=600` |
| apply（等待 608 s 后） | `model_id=1984b7f4…`，`mode=apply`，`action=restore_baseline`，`expected_revision=0`，`expected_pending_job_id` 省略（inspect 返回 null），`evidence_token=facb0322…`，`idempotency_key=dev040-expiry-20261018-01`，调用时刻约 `2026-10-18T02:18:45Z` | `Error: Evidence token is missing or expired; inspect again` |

- 未创建任何恢复作业：apply 前后 `creo_list_jobs` 顶部仍为 `27a5147301e84751b062dbce9c87effe`（created `2026-10-17T14:52:54Z`），无新增 job_id。
- 模型未变化：inspect #2（`02:19:04.407Z`）与最终 inspect（`02:19:27.059Z`）均为 `status=abandoned`、`revision=0`、`pending_job=null`、`recovery_pending=null`。
- 未自动执行旧动作：返回提示为 `inspect again`，无任何隐式重放。
- 后续若需继续，按规则重新 inspect 并使用新幂等键与新凭证；本次未执行任何有效动作。

## 4. 场景 2：已接受但尚未开始原生执行的拒绝 —— **未验证**

前置条件未提供：MCP 无控制原生执行暂停的接口，发起者未提供可在隔离环境观察 `stage="reconciliation_refused"` / `failure_phase="before_native"` 的测试条件。本模型四个动作 `available=false`，连"已接受"这一步都无法进入。未做人为制造，未手动清理。

## 5. 场景 3：原生会话指纹拒绝或原生中断 —— **未验证**

前置条件未提供（需发起者提供专用场景并明确准许）。本次未触发任何原生执行器启动，`native_worker_started` 与 `result.failed_stage` 均无本次观测值。

参考历史记录（非本次执行，仅作背景，不计入本次结论）：`creo_list_jobs` 中 `3b0d7a9442d34544bd71351378d3d5e4` 为 `unknown_outcome` / `reconciliation_unconfirmed`，`message="Recovery refused: Creo session changed since recorded evidence"`，`native_checkpoint.completion_stage="before_disconnect"`，`native_result_present=true`，属 2026-10-17 的既有记录，本次未复现。

## 6. 场景 4：幂等与可空字段 —— **部分通过**

使用 inspect #2 凭证 `240db6ba62e248bf950b0aa3777749aa`（`02:19:04.407Z`，有效期 600 s，基准 `revision=0`、`pending_job=null`）。

| 用例 | 输入要点 | 原始返回 | 判定 |
| --- | --- | --- | --- |
| 空串 pending | `expected_pending_job_id=""`，`idempotency_key=dev040-empty-pending-20261018-01` | `Error: expected_pending_job_id must be the pending job id returned by inspect, or null when inspect returned pending_job=null; received ''` | 准确拒绝，未转换、未建作业 |
| 字面字符串 `"null"` | `expected_pending_job_id="null"`，`idempotency_key=dev040-literal-null-20261018-01` | `Error: Model is already abandoned` | 未在 pending 校验处被拒，等价于被当作 null 接受后进入动作校验 |
| 省略字段 | 不传 `expected_pending_job_id`，`idempotency_key=dev040-omit-pending-20261018-01` | `Error: Model is already abandoned` | 与 `"null"` 表现一致 |
| revision 绑定 | `expected_revision=1`（模型实为 0） | `Error: Stale expected_revision: model revision is 0, expected 1; inspect again` | 正确拒绝 |

补充观测：

- 校验顺序可判定：凭证有效性 → `expected_pending_job_id` → 动作可用性。空串用例（凭证有效）停在 pending 校验；`"null"` 与省略用例越过 pending 校验，停在动作可用性。
- 上述拒绝均未消耗凭证：空串被拒后，同一 token 仍能通过凭证检查进入后续校验。
- **已接受作业的幂等重复：未验证。** 本模型无可用动作，无法获得"已接受"的恢复作业，故"相同参数 + 相同幂等键返回同一 job_id 与既有状态、不启动第二次恢复"未被实际观测。
- 紧接确定性拒绝后的再次 apply 均重新 inspect 并使用新幂等键，未复用旧凭证。

## 7. 场景 5：busy —— **未验证（并发未验证）**

无第二客户端可真实并行占用通道，发起者未准许专用并行操作。未通过故障注入、锁文件占用或重复提交制造 busy。锁文件占用、删除状态与系统错误码不能凭 MCP 黑盒判定，本场景不替代 BUG-057 的开发者复现。

## 8. 其他报告项

- **compact 与 full 一致性：未验证。** 本次所有 apply 均在准入前被拒，未产生恢复作业，无 job_id 可供 compact/full 对照。
- **几何/参数、保存重载、回滚证据：不适用/未验证。** 本模型 `inspection_available=false`、`part_file=null`，本次未发生任何几何变更。
- **内部文件机制**（锁占用、幂等键持久化、recovery 占位释放）：未验证，属不可由 MCP 观察项。
- **其他 Creo 版本**：未验证。本次仅 Creo 12.4.0.0（`release_numeric=44`）。
- **recovery_pending_released / recovery_pending_cleanup_error**：本次无被拒绝的恢复作业，两个字段均无观测值。

## 9. 结论

- 场景 1（过期凭证准入前拒绝、不接受新作业、保护与 revision 不变）**通过**。
- 场景 4 中可空字段与 revision 绑定校验**通过**；已接受作业的幂等重复**无法验证**。
- 场景 2、3、5 **未验证**，原因均为发起者未提供必要前置条件。
- 由于 apply 被接受后的全部路径（原生执行前拒绝、原生指纹拒绝/中断、幂等）均未取得黑盒观测，且构建身份无法确认，**DEV-040 不能判定为验收通过**，仅能判定"准入前校验与凭证过期路径符合预期"。

## 10. 后续需要发起者提供

1. 一个非 abandoned、且至少有可用动作的专用测试模型（用于场景 2/3/4 的已接受路径）。
2. 本次部署的构建身份（DEV-040 对应的提交/指纹映射），当前公开接口无此信息。
3. 场景 2/3 的隔离观察条件与明确准许；场景 5 的真实并行客户端与准许。
