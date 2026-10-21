# 2026-10-18_CREO_0.3.5_通道11失效实测复现与种子筋第六轮依旧

**测试日期**：2026-10-18（08:43 – 09:00，GMT+8）
**MCP 版本**：0.3.5（GitHub 最新，Pre-release；84 工具）
**Creo 版本**：Creo Parametric 9.0.0.0（release_numeric=41）
**平台**：Windows 10，stdio；本机已由用户升级至 0.3.5（执行器 2026-10-17 21:31 重建，源码指纹核对一致）
**对照基线**：2026-10-15（0.3.0）、10-16（0.3.2）、10-17（0.3.3）、10-17（0.3.4）四轮报告

---

## 一、本轮结论

| 项 | 结果 |
|---|---|
| **BUG-055 恢复参数契约**（上轮 P0） | ✅ **MCP 路径闭环验收通过**（省略字段成功；null→"" 与无效值均准确拒绝并回显） |
| `restore_baseline` 动作（上轮未验） | ✅ 通过（基线 sha256 校验、rev 保持、历史保留） |
| **BUG-054 切除材料守卫**（本版新增） | ✅ 有效 cut 返回 `material_removed_mm3`；零去料 cut 失败+回滚+revision 保持 |
| **BUG-056 通道失效**（本版已知问题） | ❌ **本机实测复现**（-11，约 33 秒窗口），自动 retry 无法自愈 |
| 叶片种子 / 筋 | ❌ 第六轮依旧（Creo 9） |
| loft 回调 / component_constraints | ❌ 行为未变（第 4/5 轮） |
| 孔、参数、关系、工程图 PDF、翼型、UDF、种子列表 | ✅ 全部通过，数值精确 |

## 二、BUG-055 验收：上轮 P0 已闭环 ✅

上轮我报告的阻塞性缺陷（`expected_pending_job_id: null` 经 MCP 变成 `""` 导致 apply 必然失败）在本版得到完整修复。三条路径全部实测：

| 调用 | 期望 | 实际 |
|---|---|---|
| **省略 `expected_pending_job_id`** | 成功 | ✅ 入队 → `succeeded` → 模型 `abandoned`，`recovery_pending: null`，原 job 历史保留 |
| 显式 `null`（客户端转 `""`） | 准确拒绝 | ✅ `expected_pending_job_id must be the pending job id returned by inspect, or null when inspect returned pending_job=null; **received ''**` |
| 无效非空值 `not-a-real-job-id` | 准确拒绝 | ✅ `... **received 'not-a-real-job-id'**` |

**评价**：错误信息回显实际收到值这一点做得很好——它直接把"客户端把 null 转成空串"这个事实暴露给调用方，用户一眼就能判断该改用省略字段。作者在发布说明中"WorkBuddy 客户端把显式 null 转为空串的限制已观察到"的表述，本机实测完全一致。

**`restore_baseline` 也验通了**（0.3.4 时只能验 `abandon_new`）：有基线的 failed 模型 → inspect 正确识别 `baseline.verified: true`（sha256 匹配）且只开放 `restore_baseline`（`abandon_new` 正确置为不可用）→ apply 后 `succeeded` / `reconciliation_committed` / 模型 `ready` / **revision 保持 1**（符合"restore_baseline keeps revision"契约）。

## 三、BUG-056 通道失效：本机实测复现 ❌（本轮最重要的新发现）

### 现象与时间线

```
00:45:44  creo_new_part(wb_acc35_cut)            → succeeded
00:46:17  creo_execute_plan(底座拉伸)             → failed
          Toolkit call connect_creo(&process) failed with code -11 during connect
00:47:20  creo_session_status: connection_failed / toolkit_code -11 / worker_exit_code 20 / stale: true / retry_allowed: true
00:47:2x  creo_startup_status(retry=true)         → checking
00:48:12  state: waiting_for_connection（coordinator_running: true，剩余预算 258 秒）
00:50:54  state: timeout（自动重连失败，coordinator_running: false）
```

**失效窗口**：new_part 成功 → 33 秒后下一个请求 -11。与作者观测的"验证后约 37～41 秒失效"高度吻合，说明该缺陷在 **Creo 9 环境同样存在**，非 Creo 12 特有。

### 关键发现：当前 retry 机制无法自愈，但存在明确的人工恢复路径

自动 retry（`creo_startup_status(retry=true)`）尝试后仍是 `timeout`。检查进程状态发现：

```
xtop.exe        pid 4036  启动 2026-10-18 00:00:30  运行 530 分钟  MainWindowHandle=0（无主窗口）  Responding=True
parametric.exe  pid 2652  同上                                        MainWindowHandle=0
```

即：**Creo 进程存活、响应正常，但无任何主窗口，Toolkit 无法在其上建立连接**（-11）。MCP 的 `launch_attempt` 已累计到 5 次仍失败。

**实际有效的恢复步骤（本机验证）**：
1. 结束无主窗口的 `xtop.exe` / `parametric.exe` / `creoagent.exe` 残留进程；
2. 调用 `creo_startup_status(retry=true)`；
3. MCP 自动拉起新 Creo 会话（`launch_attempt: 6`），约 40 秒后 `connected: true` / `state: ready`，通道完全恢复。

**建议**：
1. `creo_startup_status` 在 `waiting_for_connection` 且检测到"Creo 进程存在但无可见主窗口/无 Toolkit 连接"时，直接给出**"结束残留 Creo 进程后 retry"的具体指引**（当前只提示"Check startup dialogs"，对无窗口进程不适用）；
2. 评估让自动重连在"进程存在但连不上"时主动清理自己启动的（且记录为本次 launch 拉起的）进程后重试——需严格限定只处理自身 launch 的进程，避免误杀用户会话；
3. 该问题在 Creo 9 复现，建议纳入 BUG-056 的复现矩阵。

## 四、BUG-054 切除材料守卫：全部通过 ✅

| 场景 | 结果 |
|---|---|
| **有效切除**（Ø10 圆，z=20 顶面向内切深 10） | ✅ `succeeded`，`material_removed_mm3 = 785.3981633974618`（= π×5²×10 精确），体积 120000 → 119214.60183660254 |
| **零去料切除**（圆在 (200,200) 实体外） | ✅ `failed`，提示 `Extrude cut removes no material; check the sketch position, direction and depth against existing geometry`；`rollback_succeeded: true`；`failed_operation_index: 1`；**模型 `ready`、revision 保持 3、体积保持 119214.60** |

两个场景都符合发布说明承诺（零去料返回可识别错误并回滚、有效切除返回 `material_removed_mm3`、revision 与保存基线保持）。**这是本版做得最扎实的一项。**

## 五、本轮发现的其他问题（新）

### P1 `creo_reconcile_model`：明确"拒绝"的作业被标为 `unknown_outcome`，并悬挂 `recovery_pending`

**复现**：升级后首次 apply（省略字段，参数合法）→ 作业返回 `unknown_outcome` / `stage: reconciliation_unconfirmed` / 消息 `Recovery refused: Creo session changed since recorded evidence`。

**问题**：
1. **语义矛盾**：作业已被明确拒绝（"refused"），却标成 `unknown_outcome`（不确定是否执行）。这会让调用方与 `reconcile_model` 自身都把它当作"结果未知"，而实际上"未执行"是确定的。
2. **`recovery_pending` 悬挂**：该作业已是终态（有 `finished_at`），但模型 `recovery_pending` 仍保留其 id。虽然下一次成功恢复会覆盖它（本机第二次 apply 成功），但在此期间 inspect 会把这个已终态作业列为 owner，增加混淆。

**建议**：会话变更/证据过期这类**执行前拒绝**应记为确定性的失败（如 `refused` / `failed` 附带 `reason`），并立即清除 `recovery_pending`；`unknown_outcome` 仅保留给"原生进程可能已开工"的情形。

### P2 `creo_callback_status` 在通道故障时的降级（做得好，附带一条建议）

通道 -11 时返回 `reason: "connection_failed"` + `instruction: "Registration and loaded state cannot be inferred from this failed probe"`——**没有把通道故障误报为"未注册"**，这个设计正确且重要（值得保留）。

建议：在 `connection_failed` 时额外返回 `last_known_readiness`（上次成功探针的值 + 时间），便于调用方判断"之前是否已注册"。

## 六、历史问题状态（第六轮）

| 问题 | 首次反馈 | 0.3.4 | **0.3.5** |
|---|---|---|---|
| 叶片种子 Creo 9 无法加载 | 0.3.0 | ❌ | ❌ **仍 -16**（`ProMdlFiletypeLoad`） |
| 筋特征 Creo 9 失败 | 0.3.0 | ❌ | ❌ **仍失败**（"Rib regeneration failed on the requested material side"） |
| loft 需人工注册回调 | 0.3.2 | ⚠️ 行为未变 | ⚠️ **行为未变**（仍 `BLEND_CALLBACK_SETUP_REQUIRED`，信息完整） |
| component_constraints 位置不求解 | 0.3.2 | ❌ | ❌ **仍不求解**（transform 保持 (-30,20,0)+30°） |
| round 参数名 `radius`/`size` 不一致 | 0.3.3 | ❌ | ❌ 未修（`RoundOp.size`） |

发布说明已明确"外部 Creo 9 编译/部分建模正例与种子、筋、装配约束失败反馈分别保留，不等于本机或完整兼容验收"——说明作者已收到并记录这些反馈，但尚未修复。**这是第六轮确认**。

## 七、通过项与数值对账

| 项 | 对账 |
|---|---|
| 底座拉伸 100×60×20 | 120000.0 ✓ |
| 有效切除（BUG-054） | `material_removed_mm3` = 785.398 = π×5²×10 ✓ |
| 零去料切除（BUG-054） | 失败 + 回滚 + revision/体积保持 ✓ |
| 孔 Ø8×10 | 体积 119214.602 → 118711.947（Δ = -502.655 = π×4²×10）✓ |
| 参数（实数/布尔/字符串） | `A35`=9(type 52)、`A35_OK`=true(type 53)、`A35_S`="v035"(type 51) ✓ |
| 关系 | `A35_B` = 36 = 9×4 ✓ |
| 工程图 PDF | 16,321 字节，有效导出 ✓ |
| 翼型截面（chord 90 / 0.15） | 生成成功 ✓ |
| UDF inspect | T / DM / REF_CSYS ✓ |
| 种子库 | 9 个 available，哈希与清单一致 ✓ |
| 运行身份 | 源码指纹与实际文件一致，`source_changed_since_startup: false` ✓ |

## 八、给作者的建议（第 6 轮，按优先级）

1. **【P0 新增】BUG-056 的恢复指引**：`waiting_for_connection` + "进程存在但无主窗口"时，直接提示"结束该 Creo 进程后 retry"。本机实测这是唯一有效恢复路径，而现有提示（"Check startup dialogs"）无法覆盖无窗口场景。该问题在 Creo 9 复现，请纳入复现矩阵。
2. **【P1 新增】refused 作业不应标 `unknown_outcome`**：执行前拒绝（会话变更/证据过期）应确定性化，并立即释放 `recovery_pending`。
3. **种子库 Creo 9 适配（第六轮）**：至少在 `creo_list_seeds` 返回 `seed_build_version`，并在 `creo_new_airfoil_blade` 失败时明确"种子由 Creo 12.4 构建，当前 Creo 9 无法加载"——避免用户误以为是参数问题。
4. **筋的 Creo 9 兼容（第六轮）**：同样的错误文案建议区分"确定不支持当前 Creo 版本"与"轮廓/材料侧有问题"。
5. **component_constraints 触发重求解（第 4 轮）**。
6. 小项：统一 round 参数名；`creo_callback_status` 增加 `last_known_readiness`。

## 九、总体评价

0.3.5 的两个核心改动**都真实有效且验收通过**：BUG-055 完整闭环（我上轮报的 P0，作者不仅修了参数契约，还准确复现了我的诊断结论"客户端把 null 转成空串"）；BUG-054 的切除守卫逻辑严谨（体积核对 + 回滚 + revision 保持），是本轮质量最高的部分。

但本版发布说明中列为"尚未修复"的 **BUG-056，我在本机完整复现了**，并且发现它的恢复完全依赖人工清理残留进程——**这直接影响自动化的可靠性**，建议提到下一个版本的最高优先级。同时，种子/筋/装配约束三项跨版本问题进入第六轮，建议至少在文档与工具返回中明确"当前 Creo 版本不支持"，避免用户反复踩同一个坑。

---

*留痕：本轮作业 request.json / native.log / job.json 保留于 `F:\WorkBuddy CREO Space\MCP_CREO_MechDog\jobs\`；前四轮报告见工作区同名 md。*
